"""OSV matcher (issue #77): findings, alias merge (U-ALIAS) and withdrawal (U-WITHDRAW)."""

from __future__ import annotations

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from osv_stub import OsvFixtureTransport
from vulntriage.db.models import (
    Advisory,
    Asset,
    Base,
    Dependency,
    Finding,
    FindingDependency,
    Vulnerability,
    VulnerabilityAlias,
)
from vulntriage.ingest.matcher import match_asset
from vulntriage.ingest.osv import OsvClient

pytestmark = pytest.mark.sqlite_integration


@pytest.fixture()
def factory(sqlite_engine) -> sessionmaker[Session]:  # type: ignore[no-untyped-def]
    Base.metadata.create_all(sqlite_engine)
    return sessionmaker(sqlite_engine, expire_on_commit=False)


def _asset_with_deps(factory: sessionmaker[Session], deps: list[tuple[str, str, str | None, str]]) -> int:
    with factory() as session:
        asset = Asset(name="a", owner_name=None, owner_email=None, criticality="low",
                      internet_facing=False, repository_url="https://github.com/o/r")
        session.add(asset)
        session.flush()
        for ecosystem, name, version, source in deps:
            session.add(Dependency(asset_id=asset.id, ecosystem=ecosystem, name=name,
                                   version=version, source_file=source, direct=True))
        session.commit()
        return asset.id


def _match(factory: sessionmaker[Session], asset_id: int) -> bool:
    client = OsvClient(OsvFixtureTransport().client())
    with factory() as session:
        created = match_asset(session, asset_id, client)
        session.commit()
        return created


def _findings(factory: sessionmaker[Session], asset_id: int) -> list[Finding]:
    with factory() as session:
        return list(session.scalars(
            select(Finding).where(Finding.asset_id == asset_id).order_by(Finding.package)
        ))


# -- a plain match ----------------------------------------------------------


def test_pyyaml_match_records_fixed_version_and_aliases(factory) -> None:  # type: ignore[no-untyped-def]
    aid = _asset_with_deps(factory, [("PyPI", "pyyaml", "5.1", "requirements.txt")])
    assert _match(factory, aid) is True
    findings = _findings(factory, aid)
    assert len(findings) == 1
    assert findings[0].package == "pyyaml"
    assert findings[0].fixed_version == "5.4"
    assert findings[0].status == "open"
    with factory() as session:
        vuln = session.get(Vulnerability, findings[0].vulnerability_id)
        aliases = set(session.scalars(
            select(VulnerabilityAlias.alias_id).where(
                VulnerabilityAlias.vulnerability_id == vuln.id)))
    assert vuln.cve_id == "CVE-2020-14343"
    assert vuln.identity_key == "CVE-2020-14343"
    assert {"GHSA-8q59-q68h-6hv4", "CVE-2020-14343"} <= aliases


def test_clean_dependency_has_no_finding(factory) -> None:  # type: ignore[no-untyped-def]
    aid = _asset_with_deps(factory, [("PyPI", "requests", "2.28.2", "requirements.txt")])
    assert _match(factory, aid) is False
    assert _findings(factory, aid) == []


def test_version_unknown_dependency_is_not_queried(factory) -> None:  # type: ignore[no-untyped-def]
    aid = _asset_with_deps(factory, [("PyPI", "pyyaml", None, "requirements.txt")])
    assert _match(factory, aid) is False
    assert _findings(factory, aid) == []


# -- U-ALIAS: two advisories for one CVE merge to one finding ---------------


def test_two_advisories_sharing_a_cve_make_one_finding(factory) -> None:  # type: ignore[no-untyped-def]
    aid = _asset_with_deps(factory, [("PyPI", "urllib3", "1.26.9", "requirements.txt")])
    assert _match(factory, aid) is True
    findings = _findings(factory, aid)
    assert len(findings) == 1  # not two
    assert findings[0].fixed_version == "1.26.17"
    with factory() as session:
        # Both advisory ids resolve to the one vulnerability.
        assert session.scalar(select(func.count()).select_from(Vulnerability)) == 1
        assert session.scalar(select(func.count()).select_from(Advisory)) == 2
        aliases = set(session.scalars(select(VulnerabilityAlias.alias_id)))
    assert {"GHSA-v845-jxx5-vc9f", "PYSEC-2023-212", "CVE-2023-43804"} <= aliases


# -- U-WITHDRAW: an already-withdrawn advisory creates no finding -----------


def test_already_withdrawn_advisory_creates_no_finding(factory) -> None:  # type: ignore[no-untyped-def]
    aid = _asset_with_deps(factory, [("PyPI", "django", "4.2", "requirements.txt")])
    assert _match(factory, aid) is False
    assert _findings(factory, aid) == []
    with factory() as session:
        # No vulnerability or advisory is recorded for the withdrawn-at-first-sight advisory.
        assert session.scalar(select(func.count()).select_from(Finding)) == 0
        assert session.scalar(select(func.count()).select_from(Vulnerability)) == 0


# -- A6: same package in two files is one finding linking both --------------


def test_same_package_in_two_files_is_one_finding_linking_both(factory) -> None:  # type: ignore[no-untyped-def]
    aid = _asset_with_deps(factory, [
        ("PyPI", "pyyaml", "5.1", "requirements.txt"),
        ("PyPI", "pyyaml", "5.1", "uv.lock"),
    ])
    assert _match(factory, aid) is True
    findings = _findings(factory, aid)
    assert len(findings) == 1
    with factory() as session:
        links = session.scalar(
            select(func.count()).select_from(FindingDependency).where(
                FindingDependency.finding_id == findings[0].id))
    assert links == 2


def test_matching_is_idempotent_on_a_repeated_run(factory) -> None:  # type: ignore[no-untyped-def]
    aid = _asset_with_deps(factory, [("PyPI", "pyyaml", "5.1", "requirements.txt")])
    assert _match(factory, aid) is True
    _match(factory, aid)  # a second run creates no duplicate finding or vulnerability
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(Finding)) == 1
        assert session.scalar(select(func.count()).select_from(Vulnerability)) == 1
        assert session.scalar(select(func.count()).select_from(Advisory)) == 1
