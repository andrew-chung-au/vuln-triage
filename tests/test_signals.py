"""KEV and EPSS enrichment (issue #78): U-KEV, U-EPSS and U-FEED."""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from osv_stub import OsvFixtureTransport
from signals_stub import EpssFixtureTransport, KevFixtureTransport
from vulntriage.db.enums import KevValue, kev_value
from vulntriage.db.models import Asset, Base, Dependency, Signal, Vulnerability
from vulntriage.ingest.matcher import match_asset
from vulntriage.ingest.osv import OsvClient
from vulntriage.ingest.signals import (
    EpssClient,
    KevClient,
    KevCatalogue,
    EpssScore,
    enrich_asset,
)

pytestmark = pytest.mark.sqlite_integration


@pytest.fixture()
def factory(sqlite_engine) -> sessionmaker[Session]:  # type: ignore[no-untyped-def]
    Base.metadata.create_all(sqlite_engine)
    return sessionmaker(sqlite_engine, expire_on_commit=False)


def _asset_with_findings(factory: sessionmaker[Session], deps: list[tuple[str, str, str]]) -> int:
    """Register an asset, store dependencies, and run OSV matching to create findings."""
    with factory() as session:
        asset = Asset(name="a", owner_name=None, owner_email=None, criticality="high",
                      internet_facing=True, repository_url="https://github.com/o/r")
        session.add(asset)
        session.flush()
        for ecosystem, name, version in deps:
            session.add(Dependency(asset_id=asset.id, ecosystem=ecosystem, name=name,
                                   version=version, source_file="requirements.txt", direct=True))
        asset_id = asset.id
        session.commit()
    with factory() as session:
        match_asset(session, asset_id, OsvClient(OsvFixtureTransport().client()))
        session.commit()
    return asset_id


def _enrich(factory, asset_id, kev=None, epss=None) -> None:  # type: ignore[no-untyped-def]
    with factory() as session:
        enrich_asset(session, asset_id, kev, epss)
        session.commit()


def _signals(factory) -> dict[str, Signal]:  # type: ignore[no-untyped-def]
    with factory() as session:
        return {s.cve_id: s for s in session.scalars(select(Signal))}


# -- U-KEV: KEV listed / not listed / n/a (no CVE) --------------------------


def test_kev_listed_and_not_listed(factory) -> None:  # type: ignore[no-untyped-def]
    aid = _asset_with_findings(factory, [
        ("PyPI", "urllib3", "1.26.9"),  # CVE-2023-43804: in the KEV fixture
        ("PyPI", "pyyaml", "5.1"),      # CVE-2020-14343: not in the KEV fixture
    ])
    _enrich(factory, aid, kev=KevClient(KevFixtureTransport().client()),
            epss=EpssClient(EpssFixtureTransport().client()))
    signals = _signals(factory)

    assert signals["CVE-2023-43804"].kev_listed is True
    assert signals["CVE-2023-43804"].kev_stale is False
    assert signals["CVE-2023-43804"].kev_date_added is not None
    assert kev_value("CVE-2023-43804", signals["CVE-2023-43804"].kev_listed) == KevValue.LISTED

    assert signals["CVE-2020-14343"].kev_listed is False
    assert kev_value("CVE-2020-14343", signals["CVE-2020-14343"].kev_listed) == KevValue.NOT_LISTED


def test_no_cve_vulnerability_gets_no_signal_and_derives_na(factory) -> None:  # type: ignore[no-untyped-def]
    # E11: a vulnerability with no CVE is recorded but keyed by its advisory id;
    # KEV derives to n/a (no CVE) from cve_id alone, and it has no Signal row.
    aid = _asset_with_findings(factory, [("PyPI", "pyyaml", "5.1")])
    # Force the one vulnerability to have no CVE, as an E11 vulnerability would.
    with factory() as session:
        vuln = session.scalar(select(Vulnerability))
        vuln.cve_id = None
        vuln.identity_key = "GHSA-8q59-q68h-6hv4"
        session.commit()
    _enrich(factory, aid, kev=KevClient(KevFixtureTransport().client()),
            epss=EpssClient(EpssFixtureTransport().client()))
    assert _signals(factory) == {}  # no Signal created for a CVE-less vulnerability
    assert kev_value(None, None) == KevValue.NOT_APPLICABLE


# -- U-EPSS: score or n/a ---------------------------------------------------


def test_epss_scores_are_recorded(factory) -> None:  # type: ignore[no-untyped-def]
    aid = _asset_with_findings(factory, [
        ("PyPI", "urllib3", "1.26.9"),
        ("PyPI", "pyyaml", "5.1"),
    ])
    _enrich(factory, aid, kev=KevClient(KevFixtureTransport().client()),
            epss=EpssClient(EpssFixtureTransport().client()))
    signals = _signals(factory)
    assert signals["CVE-2023-43804"].epss_score == pytest.approx(0.00456)
    assert signals["CVE-2023-43804"].epss_percentile == pytest.approx(0.73)
    assert signals["CVE-2023-43804"].epss_date is not None
    assert signals["CVE-2020-14343"].epss_score == pytest.approx(0.91234)
    assert signals["CVE-2020-14343"].epss_stale is False


def test_epss_batches_one_request_for_all_cves(factory) -> None:  # type: ignore[no-untyped-def]
    aid = _asset_with_findings(factory, [
        ("PyPI", "urllib3", "1.26.9"),
        ("PyPI", "pyyaml", "5.1"),
    ])
    epss_stub = EpssFixtureTransport()
    kev_stub = KevFixtureTransport()
    with factory() as session:
        enrich_asset(session, aid, KevClient(kev_stub.client()), EpssClient(epss_stub.client()))
        session.commit()
    assert len(epss_stub.requests) == 1  # both CVEs in one cve= batch
    assert len(kev_stub.requests) == 1   # one whole-catalogue fetch
    sent = epss_stub.requests[0].url.params.get("cve")
    assert "CVE-2023-43804" in sent and "CVE-2020-14343" in sent


# -- U-FEED: feed failure keeps last-known and marks stale ------------------


def test_kev_failure_marks_stale_and_does_not_raise(factory) -> None:  # type: ignore[no-untyped-def]
    aid = _asset_with_findings(factory, [("PyPI", "urllib3", "1.26.9")])
    # KEV fails; EPSS succeeds. No exception; KEV stale, EPSS fresh.
    _enrich(factory, aid, kev=KevClient(KevFixtureTransport(fail=True).client()),
            epss=EpssClient(EpssFixtureTransport().client()))
    signal = _signals(factory)["CVE-2023-43804"]
    assert signal.kev_stale is True
    assert signal.kev_listed is None  # never fetched -> null
    assert kev_value("CVE-2023-43804", signal.kev_listed) == KevValue.NOT_LISTED
    assert signal.epss_stale is False and signal.epss_score is not None


def test_epss_failure_marks_stale_and_keeps_last_known(factory) -> None:  # type: ignore[no-untyped-def]
    aid = _asset_with_findings(factory, [("PyPI", "urllib3", "1.26.9")])
    # First a successful run records a score.
    _enrich(factory, aid, kev=KevClient(KevFixtureTransport().client()),
            epss=EpssClient(EpssFixtureTransport().client()))
    assert _signals(factory)["CVE-2023-43804"].epss_score is not None
    # Then an EPSS outage: the last-known score is kept, the stale marker set.
    _enrich(factory, aid, kev=KevClient(KevFixtureTransport().client()),
            epss=EpssClient(EpssFixtureTransport(fail=True).client()))
    signal = _signals(factory)["CVE-2023-43804"]
    assert signal.epss_stale is True
    assert signal.epss_score is not None  # not zeroed or deleted


def test_enrich_with_no_clients_is_a_noop(factory) -> None:  # type: ignore[no-untyped-def]
    aid = _asset_with_findings(factory, [("PyPI", "urllib3", "1.26.9")])
    _enrich(factory, aid, kev=None, epss=None)
    assert _signals(factory) == {}


# -- client parsing (no DB) -------------------------------------------------


def test_kev_catalogue_membership() -> None:
    cat = KevClient(KevFixtureTransport().client()).fetch_catalogue()
    assert isinstance(cat, KevCatalogue)
    assert "CVE-2023-43804" in cat
    assert "CVE-2020-14343" not in cat


def test_epss_client_parses_scores() -> None:
    scores = EpssClient(EpssFixtureTransport().client()).fetch_scores(
        ["CVE-2023-43804", "CVE-0000-00000"])
    assert isinstance(scores["CVE-2023-43804"], EpssScore)
    assert scores["CVE-2023-43804"].score == pytest.approx(0.00456)
    assert "CVE-0000-00000" not in scores  # not returned by the feed
