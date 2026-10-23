"""Finding lifecycle and re-scan transitions (issue #80): U-WITHDRAW, I-RESCAN, audit.

These drive several scans against a programmable in-process OSV client so the
installed version, the advisory ranges and the ``withdrawn`` flag can change
between scans, exercising fixed/withdrawn/reopen/restore (US-10, E4, E7, E8) and
the audit trail (US-11).
"""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from vulntriage.db.enums import FindingStatus
from vulntriage.db.models import (
    AuditEntry,
    Asset,
    Base,
    Dependency,
    Finding,
    Lifecycle,
)
from vulntriage.ingest.matcher import match_asset
from vulntriage.ingest.osv import Query, VulnRef

pytestmark = pytest.mark.sqlite_integration


class ProgrammableOsv:
    """An OSV client whose answers the test sets directly (no HTTP)."""

    def __init__(self) -> None:
        # advisory id -> full advisory dict
        self.advisories: dict[str, dict[str, Any]] = {}

    def set_advisory(self, advisory: dict[str, Any]) -> None:
        self.advisories[advisory["id"]] = advisory

    def query_batch(self, queries: list[Query]) -> list[list[VulnRef]]:
        out: list[list[VulnRef]] = []
        for q in queries:
            refs: list[VulnRef] = []
            for adv in self.advisories.values():
                for entry in adv.get("affected", []):
                    pkg = entry.get("package", {})
                    if pkg.get("ecosystem") == q.ecosystem and pkg.get("name", "").lower() == q.name.lower():
                        refs.append(VulnRef(adv["id"], adv.get("modified")))
                        break
            out.append(refs)
        return out

    def get_vuln(self, osv_id: str) -> dict[str, Any]:
        return self.advisories[osv_id]


def _advisory(osv_id: str, name: str, fixed: str, *, aliases=None, withdrawn=None) -> dict[str, Any]:
    adv: dict[str, Any] = {
        "id": osv_id,
        "aliases": aliases or [],
        "modified": "2024-01-01T00:00:00Z",
        "summary": "s",
        "details": "d",
        "affected": [
            {"package": {"ecosystem": "PyPI", "name": name},
             "ranges": [{"type": "ECOSYSTEM", "events": [{"introduced": "0"}, {"fixed": fixed}]}]}
        ],
        "references": [],
    }
    if withdrawn:
        adv["withdrawn"] = withdrawn
    return adv


@pytest.fixture()
def factory(sqlite_engine) -> sessionmaker[Session]:  # type: ignore[no-untyped-def]
    Base.metadata.create_all(sqlite_engine)
    return sessionmaker(sqlite_engine, expire_on_commit=False)


def _make_asset(factory: sessionmaker[Session]) -> int:
    with factory() as session:
        asset = Asset(name="a", owner_name=None, owner_email=None, criticality="low",
                      internet_facing=False, repository_url="https://github.com/o/r")
        session.add(asset)
        session.commit()
        return asset.id


def _set_version(factory: sessionmaker[Session], asset_id: int, name: str, version: str) -> None:
    """Replace the asset's dependency set with one package at the given version."""
    with factory() as session:
        session.execute(Dependency.__table__.delete().where(Dependency.asset_id == asset_id))
        session.add(Dependency(asset_id=asset_id, ecosystem="PyPI", name=name,
                               version=version, source_file="requirements.txt", direct=True))
        session.commit()


def _scan(factory: sessionmaker[Session], asset_id: int, osv: ProgrammableOsv) -> None:
    with factory() as session:
        match_asset(session, asset_id, osv)
        session.commit()


def _finding(factory: sessionmaker[Session], asset_id: int) -> Finding:
    with factory() as session:
        return session.scalar(select(Finding).where(Finding.asset_id == asset_id))


def _audits(factory: sessionmaker[Session], finding_id: int) -> list[AuditEntry]:
    with factory() as session:
        return list(session.scalars(
            select(AuditEntry).where(AuditEntry.finding_id == finding_id).order_by(AuditEntry.id)))


# -- US-10: fix on upgrade out of range -------------------------------------


def test_upgrade_out_of_range_sets_fixed(factory) -> None:  # type: ignore[no-untyped-def]
    osv = ProgrammableOsv()
    osv.set_advisory(_advisory("GHSA-aaaa", "pkg", "2.0.1", aliases=["CVE-2024-1"]))
    aid = _make_asset(factory)

    _set_version(factory, aid, "pkg", "2.0.0")  # in range
    _scan(factory, aid, osv)
    finding = _finding(factory, aid)
    assert finding.status == "open" and finding.fixed_version == "2.0.1"

    _set_version(factory, aid, "pkg", "2.0.3")  # outside the range
    _scan(factory, aid, osv)
    finding = _finding(factory, aid)
    assert finding.status == "fixed" and finding.fixed_at is not None
    events = [(a.previous_value, a.new_value, a.actor, a.source) for a in _audits(factory, finding.id)]
    assert events[0] == (None, "open", "system", "OSV")  # creation
    assert events[-1] == ("open", "fixed", "re-scan", "OSV")


def test_still_in_range_after_upgrade_stays_open(factory) -> None:  # type: ignore[no-untyped-def]
    osv = ProgrammableOsv()
    osv.set_advisory(_advisory("GHSA-bbbb", "pkg", "3.0.0"))
    aid = _make_asset(factory)
    _set_version(factory, aid, "pkg", "1.0.0")
    _scan(factory, aid, osv)
    _set_version(factory, aid, "pkg", "2.5.0")  # upgraded but still < 3.0.0
    _scan(factory, aid, osv)
    assert _finding(factory, aid).status == "open"


# -- E4: withdrawal and restore ---------------------------------------------


def test_withdrawn_advisory_sets_withdrawn_not_fixed(factory) -> None:  # type: ignore[no-untyped-def]
    osv = ProgrammableOsv()
    osv.set_advisory(_advisory("GHSA-cccc", "pkg", "2.0.1"))
    aid = _make_asset(factory)
    _set_version(factory, aid, "pkg", "1.0.0")
    _scan(factory, aid, osv)
    assert _finding(factory, aid).status == "open"

    osv.set_advisory(_advisory("GHSA-cccc", "pkg", "2.0.1", withdrawn="2024-02-01T00:00:00Z"))
    _scan(factory, aid, osv)
    finding = _finding(factory, aid)
    assert finding.status == "withdrawn"
    assert finding.status_before_withdrawal == "open"
    assert _audits(factory, finding.id)[-1].new_value == "withdrawn"


def test_reinstated_advisory_in_range_restores_open(factory) -> None:  # type: ignore[no-untyped-def]
    osv = ProgrammableOsv()
    osv.set_advisory(_advisory("GHSA-dddd", "pkg", "2.0.1"))
    aid = _make_asset(factory)
    _set_version(factory, aid, "pkg", "1.0.0")
    _scan(factory, aid, osv)
    osv.set_advisory(_advisory("GHSA-dddd", "pkg", "2.0.1", withdrawn="2024-02-01T00:00:00Z"))
    _scan(factory, aid, osv)
    assert _finding(factory, aid).status == "withdrawn"
    # reinstated (withdrawn cleared), still in range -> back to open
    osv.set_advisory(_advisory("GHSA-dddd", "pkg", "2.0.1"))
    _scan(factory, aid, osv)
    finding = _finding(factory, aid)
    assert finding.status == "open" and finding.status_before_withdrawal is None
    assert _audits(factory, finding.id)[-1] .previous_value == "withdrawn"


def test_reinstated_advisory_out_of_range_sets_fixed(factory) -> None:  # type: ignore[no-untyped-def]
    osv = ProgrammableOsv()
    osv.set_advisory(_advisory("GHSA-eeee", "pkg", "2.0.1"))
    aid = _make_asset(factory)
    _set_version(factory, aid, "pkg", "1.0.0")
    _scan(factory, aid, osv)
    osv.set_advisory(_advisory("GHSA-eeee", "pkg", "2.0.1", withdrawn="2024-02-01T00:00:00Z"))
    _scan(factory, aid, osv)
    # reinstated but the version was upgraded out of range -> fixed
    osv.set_advisory(_advisory("GHSA-eeee", "pkg", "2.0.1"))
    _set_version(factory, aid, "pkg", "2.5.0")
    _scan(factory, aid, osv)
    assert _finding(factory, aid).status == "fixed"


# -- E7: a fixed finding's vulnerable version returns -----------------------


def test_fixed_finding_reopens_with_new_lifecycle(factory) -> None:  # type: ignore[no-untyped-def]
    osv = ProgrammableOsv()
    osv.set_advisory(_advisory("GHSA-ffff", "pkg", "2.0.1"))
    aid = _make_asset(factory)
    _set_version(factory, aid, "pkg", "1.0.0")
    _scan(factory, aid, osv)
    _set_version(factory, aid, "pkg", "2.5.0")  # fixed
    _scan(factory, aid, osv)
    assert _finding(factory, aid).status == "fixed"
    _set_version(factory, aid, "pkg", "1.0.0")  # vulnerable version returns (E7)
    _scan(factory, aid, osv)
    finding = _finding(factory, aid)
    assert finding.status == "open" and finding.fixed_at is None
    with factory() as session:
        lifecycles = list(session.scalars(
            select(Lifecycle).where(Lifecycle.finding_id == finding.id).order_by(Lifecycle.number)))
    assert [lc.number for lc in lifecycles] == [1, 2]  # a new lifecycle started
    assert finding.current_lifecycle_id == lifecycles[-1].id


# -- E4/E8: risk-accepted finding transitions -------------------------------


def test_risk_accepted_finding_is_fixed_on_upgrade_with_ra_as_previous(factory) -> None:  # type: ignore[no-untyped-def]
    osv = ProgrammableOsv()
    osv.set_advisory(_advisory("GHSA-gggg", "pkg", "2.0.1"))
    aid = _make_asset(factory)
    _set_version(factory, aid, "pkg", "1.0.0")
    _scan(factory, aid, osv)
    finding = _finding(factory, aid)
    # a human accepts the risk (done directly here; the API is task 9b)
    with factory() as session:
        f = session.get(Finding, finding.id)
        f.status = "risk accepted"
        session.add(AuditEntry(finding_id=f.id, asset_id=None, field="status",
                               previous_value="open", new_value="risk accepted",
                               actor="42", source="dashboard", reason="accepted for the pilot"))
        session.commit()
    _set_version(factory, aid, "pkg", "2.5.0")  # upgrade out of range
    _scan(factory, aid, osv)
    finding = _finding(factory, aid)
    assert finding.status == "fixed"
    last = _audits(factory, finding.id)[-1]
    assert (last.previous_value, last.new_value, last.actor) == ("risk accepted", "fixed", "re-scan")


def test_withdrawn_from_risk_accepted_restores_acceptance(factory) -> None:  # type: ignore[no-untyped-def]
    osv = ProgrammableOsv()
    osv.set_advisory(_advisory("GHSA-hhhh", "pkg", "2.0.1"))
    aid = _make_asset(factory)
    _set_version(factory, aid, "pkg", "1.0.0")
    _scan(factory, aid, osv)
    finding = _finding(factory, aid)
    with factory() as session:
        f = session.get(Finding, finding.id)
        f.status = "risk accepted"
        session.add(AuditEntry(finding_id=f.id, asset_id=None, field="status",
                               previous_value="open", new_value="risk accepted",
                               actor="42", source="dashboard", reason="accepted"))
        session.commit()
    acceptance_id = _audits(factory, finding.id)[-1].id
    # withdraw -> withdrawn, saving risk accepted
    osv.set_advisory(_advisory("GHSA-hhhh", "pkg", "2.0.1", withdrawn="2024-02-01T00:00:00Z"))
    _scan(factory, aid, osv)
    finding = _finding(factory, aid)
    assert finding.status == "withdrawn" and finding.status_before_withdrawal == "risk accepted"
    # reinstate in range -> restores risk accepted, naming the earlier entry
    osv.set_advisory(_advisory("GHSA-hhhh", "pkg", "2.0.1"))
    _scan(factory, aid, osv)
    finding = _finding(factory, aid)
    assert finding.status == "risk accepted"
    restore = _audits(factory, finding.id)[-1]
    assert restore.new_value == "risk accepted" and restore.restores_entry_id == acceptance_id


def test_scan_only_creates_open_findings(factory) -> None:  # type: ignore[no-untyped-def]
    # An advisory withdrawn at first sight creates no finding at all (E4).
    osv = ProgrammableOsv()
    osv.set_advisory(_advisory("GHSA-iiii", "pkg", "2.0.1", withdrawn="2024-02-01T00:00:00Z"))
    aid = _make_asset(factory)
    _set_version(factory, aid, "pkg", "1.0.0")
    _scan(factory, aid, osv)
    assert _finding(factory, aid) is None
