"""Deterministic ranking (issue #79): U-TIER, U-TIE and the I-RANK worked example."""

from __future__ import annotations

import datetime as dt

import pytest

from vulntriage.db.enums import Tier
from vulntriage.ingest.ranking import (
    RankInputs,
    RankedFinding,
    order_findings,
    sort_key,
    tier_for,
)

pytestmark = pytest.mark.unit

LISTED = "KEV: listed"
NOT_LISTED = "KEV: not listed"
NA = "KEV: n/a (no CVE)"


def _inputs(kev=NOT_LISTED, epss=None, fix=True, facing=False, crit="low") -> RankInputs:
    return RankInputs(kev=kev, epss=epss, fix_available=fix, internet_facing=facing, criticality=crit)


# -- U-TIER: the four rules, first match wins -------------------------------


def test_p1_kev_listed_and_exposed() -> None:
    assert tier_for(_inputs(kev=LISTED, facing=True))[0] is Tier.P1
    # exposed via criticality critical, not internet-facing
    assert tier_for(_inputs(kev=LISTED, facing=False, crit="critical"))[0] is Tier.P1


def test_p2_kev_listed_not_exposed() -> None:
    assert tier_for(_inputs(kev=LISTED, facing=False, crit="high"))[0] is Tier.P2


def test_p2_epss_high_on_exposed_asset() -> None:
    assert tier_for(_inputs(epss=0.55, facing=True))[0] is Tier.P2
    # EPSS high but not exposed -> not P2 (falls to P3 via fix)
    assert tier_for(_inputs(epss=0.55, facing=False))[0] is Tier.P3


def test_threshold_is_0_10_inclusive() -> None:
    assert tier_for(_inputs(epss=0.10, facing=True))[0] is Tier.P2  # >= T
    assert tier_for(_inputs(epss=0.0999, facing=True))[0] is Tier.P3  # < T


def test_p3_fix_available_no_exploitation() -> None:
    assert tier_for(_inputs(fix=True))[0] is Tier.P3


def test_p4_no_fix_no_exploitation() -> None:
    assert tier_for(_inputs(fix=False))[0] is Tier.P4
    # no fix but KEV listed + exposed is still P1 (P1 rule wins first)
    assert tier_for(_inputs(kev=LISTED, facing=True, fix=False))[0] is Tier.P1


def test_only_critical_counts_as_critical_for_exposure() -> None:
    # high criticality, not internet-facing, KEV listed -> not exposed -> P2
    assert tier_for(_inputs(kev=LISTED, crit="high", facing=False))[0] is Tier.P2


def test_no_cve_cannot_reach_p1_or_p2() -> None:
    # E11: KEV n/a and EPSS n/a -> P3 (fix) or P4
    assert tier_for(_inputs(kev=NA, epss=None, fix=True, facing=True, crit="critical"))[0] is Tier.P3
    assert tier_for(_inputs(kev=NA, epss=None, fix=False, facing=True))[0] is Tier.P4


def test_rank_reason_names_the_rule_and_signals() -> None:
    _, reason = tier_for(_inputs(kev=LISTED, facing=False, crit="high", epss=0.42))
    assert reason.startswith("P2: KEV listed, asset not exposed")
    assert "EPSS 0.42" in reason and "criticality high" in reason


# -- U-TIE: the total order within a tier -----------------------------------


def _key(epss, crit="low", detected=None, fid=1):  # type: ignore[no-untyped-def]
    detected = detected or dt.datetime(2026, 1, 1, tzinfo=dt.UTC)
    return sort_key(_inputs(epss=epss, crit=crit), detected, fid)


def test_higher_epss_sorts_first() -> None:
    assert _key(0.55) < _key(0.05)


def test_na_epss_sorts_after_every_scored_finding() -> None:
    assert _key(0.0001) < _key(None)
    assert _key(0.9) < _key(None)


def test_criticality_order_breaks_a_tie() -> None:
    same = dict(epss=0.05)
    assert _key(crit="critical", **same) < _key(crit="high", **same)
    assert _key(crit="high", **same) < _key(crit="medium", **same)
    assert _key(crit="medium", **same) < _key(crit="low", **same)


def test_older_detection_then_id_breaks_the_tie() -> None:
    older = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)
    newer = dt.datetime(2026, 6, 1, tzinfo=dt.UTC)
    assert _key(0.05, detected=older, fid=9) < _key(0.05, detected=newer, fid=1)
    # same everything but id: lower id first
    assert _key(0.05, detected=older, fid=1) < _key(0.05, detected=older, fid=2)


# -- I-RANK: the architecture worked example --------------------------------


def test_worked_example_order() -> None:
    same_scan = dt.datetime(2026, 10, 23, 12, 0, tzinfo=dt.UTC)
    items = [
        # fnd-0001: A(yes, high), KEV listed, EPSS 0.30, fix -> P1
        RankedFinding(1, _inputs(kev=LISTED, epss=0.30, fix=True, facing=True, crit="high"), same_scan),
        # fnd-0002: B(no, medium), not listed, EPSS 0.55, fix -> P3
        RankedFinding(2, _inputs(kev=NOT_LISTED, epss=0.55, fix=True, facing=False, crit="medium"), same_scan),
        # fnd-0003: C(yes, critical), KEV n/a, EPSS n/a, fix -> P3
        RankedFinding(3, _inputs(kev=NA, epss=None, fix=True, facing=True, crit="critical"), same_scan),
        # fnd-0004: A(yes, high), not listed, EPSS 0.05, fix -> P3
        RankedFinding(4, _inputs(kev=NOT_LISTED, epss=0.05, fix=True, facing=True, crit="high"), same_scan),
        # fnd-0005: D(no, high), not listed, EPSS 0.05, fix -> P3
        RankedFinding(5, _inputs(kev=NOT_LISTED, epss=0.05, fix=True, facing=False, crit="high"), same_scan),
        # fnd-0006: B(no, medium), not listed, EPSS 0.02, no fix -> P4
        RankedFinding(6, _inputs(kev=NOT_LISTED, epss=0.02, fix=False, facing=False, crit="medium"), same_scan),
    ]
    assert order_findings(items) == [1, 2, 4, 5, 3, 6]


def test_order_is_deterministic_regardless_of_input_order() -> None:
    same_scan = dt.datetime(2026, 10, 23, 12, 0, tzinfo=dt.UTC)
    base = [
        RankedFinding(1, _inputs(kev=LISTED, epss=0.30, fix=True, facing=True, crit="high"), same_scan),
        RankedFinding(2, _inputs(kev=NOT_LISTED, epss=0.55, fix=True, facing=False, crit="medium"), same_scan),
        RankedFinding(3, _inputs(kev=NA, epss=None, fix=True, facing=True, crit="critical"), same_scan),
        RankedFinding(4, _inputs(kev=NOT_LISTED, epss=0.05, fix=True, facing=True, crit="high"), same_scan),
        RankedFinding(5, _inputs(kev=NOT_LISTED, epss=0.05, fix=True, facing=False, crit="high"), same_scan),
        RankedFinding(6, _inputs(kev=NOT_LISTED, epss=0.02, fix=False, facing=False, crit="medium"), same_scan),
    ]
    assert order_findings(list(reversed(base))) == [1, 2, 4, 5, 3, 6]


# -- rank_asset writes tiers and reasons to the findings --------------------


@pytest.fixture()
def factory(sqlite_engine):  # type: ignore[no-untyped-def]
    from sqlalchemy.orm import sessionmaker

    from vulntriage.db.models import Base

    Base.metadata.create_all(sqlite_engine)
    return sessionmaker(sqlite_engine, expire_on_commit=False)


@pytest.mark.sqlite_integration
def test_rank_asset_writes_tier_and_reason_from_signals(factory) -> None:  # type: ignore[no-untyped-def]
    from sqlalchemy import select

    from osv_stub import OsvFixtureTransport
    from signals_stub import EpssFixtureTransport, KevFixtureTransport
    from vulntriage.db.models import Asset, Dependency, Finding
    from vulntriage.ingest.matcher import match_asset
    from vulntriage.ingest.osv import OsvClient
    from vulntriage.ingest.ranking import rank_asset
    from vulntriage.ingest.signals import EpssClient, KevClient, enrich_asset

    # An exposed asset with urllib3 1.26.9 (KEV-listed CVE) -> P1.
    with factory() as session:
        asset = Asset(name="a", owner_name=None, owner_email=None, criticality="high",
                      internet_facing=True, repository_url="https://github.com/o/r")
        session.add(asset)
        session.flush()
        session.add(Dependency(asset_id=asset.id, ecosystem="PyPI", name="urllib3",
                               version="1.26.9", source_file="requirements.txt", direct=True))
        aid = asset.id
        session.commit()
    with factory() as session:
        match_asset(session, aid, OsvClient(OsvFixtureTransport().client()))
        enrich_asset(session, aid, KevClient(KevFixtureTransport().client()),
                     EpssClient(EpssFixtureTransport().client()))
        rank_asset(session, aid)
        session.commit()
    with factory() as session:
        finding = session.scalar(select(Finding).where(Finding.package == "urllib3"))
        assert finding.tier == "P1"
        assert finding.rank_reason.startswith("P1: KEV listed and exposed")
        assert finding.rank_inputs["kev"] == "KEV: listed"
        assert finding.rank_inputs["exposed"] is True


@pytest.mark.sqlite_integration
def test_e8_risk_accepted_finding_flagged_signals_changed_when_tier_rises(factory) -> None:  # type: ignore[no-untyped-def]
    # E8: a risk-accepted finding keeps its status but is flagged when its signals
    # escalate (here KEV becomes listed, raising the tier). No status change.
    from sqlalchemy import select

    from vulntriage.db.models import Asset, Finding, Signal, Vulnerability
    from vulntriage.ingest.ranking import rank_asset

    with factory() as session:
        asset = Asset(name="a", owner_name=None, owner_email=None, criticality="high",
                      internet_facing=True, repository_url="https://github.com/o/r")
        session.add(asset)
        session.flush()
        vuln = Vulnerability(identity_key="CVE-2024-9", cve_id="CVE-2024-9")
        session.add(vuln)
        session.flush()
        # risk-accepted finding, not yet KEV-listed -> P3 initially.
        finding = Finding(asset_id=asset.id, vulnerability_id=vuln.id, ecosystem="PyPI",
                          package="pkg", fixed_version="2.0.1", status="risk accepted",
                          tier="P4", rank_inputs={}, rank_reason="",
                          first_detected_at=dt.datetime(2026, 1, 1, tzinfo=dt.UTC))
        session.add(finding)
        session.add(Signal(cve_id="CVE-2024-9", kev_listed=False, epss_score=0.01))
        aid, fid = asset.id, None
        session.commit()
        aid = asset.id
    with factory() as session:
        rank_asset(session, aid)  # first ranking: P3, not escalated
        session.commit()
    with factory() as session:
        f = session.scalar(select(Finding))
        assert f.tier == "P3" and f.signals_changed is False
        # KEV becomes listed -> next ranking escalates the tier to P1.
        session.get(Signal, "CVE-2024-9").kev_listed = True
        session.commit()
    with factory() as session:
        rank_asset(session, aid)
        session.commit()
    with factory() as session:
        f = session.scalar(select(Finding))
        assert f.status == "risk accepted"  # unchanged
        assert f.tier == "P1" and f.signals_changed is True
