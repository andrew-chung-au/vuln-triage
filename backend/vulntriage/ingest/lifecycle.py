"""Finding lifecycle transitions and the audit trail (issue #80, task 8).

A scan (registration or re-scan) drives every finding through its status machine
(``_docs/specs.md`` § Finding statuses, E4/E7/E8/US-10/US-11):

- A new vulnerable dependency creates an ``open`` finding and its first
  ``Lifecycle``.
- A re-scan whose installed version left every affected range sets ``fixed``
  (US-10), including from ``risk accepted`` (E8).
- A re-scan where OSV has withdrawn every merged advisory sets ``withdrawn``
  (E4), saving the prior status in ``status_before_withdrawal``; it is never
  ``fixed`` and the finding is not deleted.
- A reinstated advisory (E4 restore): if the installed version is still in range,
  the finding returns to the status it had before withdrawal (``open`` or
  ``risk accepted``, the latter naming the earlier acceptance entry); if it is
  outside every range it becomes ``fixed``.
- A ``fixed`` finding whose vulnerable version returns (E7) becomes ``open`` and
  starts a new ``Lifecycle``.

Every status change writes an append-only ``AuditEntry`` with the previous
value, actor ``re-scan`` and source ``OSV`` (creation records actor/timestamp
only). No automated component ever sets ``risk accepted`` (US-11): the re-scan
only *restores* an acceptance a human previously recorded, naming that entry.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from vulntriage.db.enums import FindingStatus, Tier
from vulntriage.db.models import AuditEntry, Dependency, Finding, FindingDependency, Lifecycle

ACTOR_RESCAN = "re-scan"
ACTOR_SYSTEM = "system"
SOURCE_OSV = "OSV"


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


@dataclass(frozen=True)
class MatchState:
    """What the current scan found for one (asset, package, vulnerability).

    ``in_range`` is whether the installed version falls in any *live*
    (non-withdrawn) affected range. ``all_withdrawn`` is whether every advisory
    merged into the vulnerability is withdrawn. ``fixed_version`` is the merged
    fixed version for this dependency (A6). ``dependency_ids`` are the installed
    entries the finding links to while it is in range.
    """

    in_range: bool
    all_withdrawn: bool
    fixed_version: str | None
    dependency_ids: list[int]


def _audit(
    session: Session,
    finding_id: int,
    previous: str | None,
    new_value: str,
    *,
    actor: str = ACTOR_RESCAN,
    source: str = SOURCE_OSV,
    reason: str | None = None,
    restores_entry_id: int | None = None,
) -> AuditEntry:
    entry = AuditEntry(
        finding_id=finding_id,
        asset_id=None,
        field="status",
        previous_value=previous,
        new_value=new_value,
        actor=actor,
        source=source,
        reason=reason,
        restores_entry_id=restores_entry_id,
    )
    session.add(entry)
    session.flush()
    return entry


def _start_lifecycle(session: Session, finding: Finding, tier: str) -> Lifecycle:
    """Open a new lifecycle for the finding and point ``current_lifecycle_id`` at it."""
    last = session.scalar(
        select(Lifecycle.number)
        .where(Lifecycle.finding_id == finding.id)
        .order_by(Lifecycle.number.desc())
    )
    number = (last or 0) + 1
    now = _now()
    lifecycle = Lifecycle(
        finding_id=finding.id,
        number=number,
        started_at=now,
        due_at=now,  # the real US-9 due date is task 10a; a placeholder until then
        highest_tier=tier,
    )
    session.add(lifecycle)
    session.flush()
    finding.current_lifecycle_id = lifecycle.id
    return lifecycle


def _set_dependency_links(session: Session, finding: Finding, dependency_ids: list[int]) -> None:
    """Replace the finding's dependency links with the currently vulnerable set (A6)."""
    session.execute(
        FindingDependency.__table__.delete().where(
            FindingDependency.finding_id == finding.id
        )
    )
    for dep_id in dependency_ids:
        session.add(FindingDependency(finding_id=finding.id, dependency_id=dep_id))


def create_finding(
    session: Session,
    asset_id: int,
    vulnerability_id: int,
    ecosystem: str,
    package: str,
    state: MatchState,
) -> Finding:
    """Create a new ``open`` finding, its first lifecycle, dependency links and audit."""
    now = _now()
    finding = Finding(
        asset_id=asset_id,
        vulnerability_id=vulnerability_id,
        ecosystem=ecosystem,
        package=package,
        fixed_version=state.fixed_version,
        status=FindingStatus.OPEN.value,
        tier=Tier.P4.value,  # ranking (task 7) overwrites this after enrichment
        rank_inputs={},
        rank_reason="",
        first_detected_at=now,
    )
    session.add(finding)
    session.flush()
    _audit(session, finding.id, None, FindingStatus.OPEN.value, actor=ACTOR_SYSTEM, source=SOURCE_OSV)
    _start_lifecycle(session, finding, Tier.P4.value)
    _set_dependency_links(session, finding, state.dependency_ids)
    return finding


def apply_rescan(session: Session, finding: Finding, state: MatchState) -> None:
    """Move an existing finding to its new status for this scan, and audit it.

    The fixed version and (while in range) the dependency links are refreshed on
    every scan; the status transitions follow the spec's finding-status table.
    """
    finding.fixed_version = state.fixed_version
    status = finding.status

    if state.all_withdrawn:
        _to_withdrawn(session, finding)
        return

    # At least one live advisory remains.
    if status == FindingStatus.WITHDRAWN.value:
        _restore_from_withdrawn(session, finding, state)
        return

    if state.in_range:
        _set_dependency_links(session, finding, state.dependency_ids)
        if status == FindingStatus.FIXED.value:
            _reopen(session, finding)  # E7
        # open / risk accepted while still in range: no status change.
        return

    # Out of every live range: the upgrade cleared it (US-10, E8).
    if status in (FindingStatus.OPEN.value, FindingStatus.RISK_ACCEPTED.value):
        _to_fixed(session, finding)


def _to_withdrawn(session: Session, finding: Finding) -> None:
    if finding.status == FindingStatus.WITHDRAWN.value:
        return  # already withdrawn; nothing to record
    finding.status_before_withdrawal = finding.status
    previous = finding.status
    finding.status = FindingStatus.WITHDRAWN.value
    _audit(session, finding.id, previous, FindingStatus.WITHDRAWN.value)


def _to_fixed(session: Session, finding: Finding) -> None:
    previous = finding.status
    finding.status = FindingStatus.FIXED.value
    finding.fixed_at = _now()
    _audit(session, finding.id, previous, FindingStatus.FIXED.value)


def _reopen(session: Session, finding: Finding) -> None:
    """E7: a fixed finding's vulnerable version returned."""
    previous = finding.status
    finding.status = FindingStatus.OPEN.value
    finding.fixed_at = None
    _audit(session, finding.id, previous, FindingStatus.OPEN.value)
    _start_lifecycle(session, finding, finding.tier)


def _restore_from_withdrawn(session: Session, finding: Finding, state: MatchState) -> None:
    """E4 restore: an advisory was reinstated for a withdrawn finding."""
    if not state.in_range:
        _set_fixed_from_withdrawn(session, finding)
        return
    prior = finding.status_before_withdrawal or FindingStatus.OPEN.value
    _set_dependency_links(session, finding, state.dependency_ids)
    if prior == FindingStatus.RISK_ACCEPTED.value:
        restores = _last_acceptance_entry_id(session, finding.id)
        finding.status = FindingStatus.RISK_ACCEPTED.value
        _audit(session, finding.id, FindingStatus.WITHDRAWN.value,
               FindingStatus.RISK_ACCEPTED.value, restores_entry_id=restores)
    else:
        finding.status = FindingStatus.OPEN.value
        _audit(session, finding.id, FindingStatus.WITHDRAWN.value, FindingStatus.OPEN.value)
    finding.status_before_withdrawal = None


def _set_fixed_from_withdrawn(session: Session, finding: Finding) -> None:
    finding.status = FindingStatus.FIXED.value
    finding.fixed_at = _now()
    finding.status_before_withdrawal = None
    _audit(session, finding.id, FindingStatus.WITHDRAWN.value, FindingStatus.FIXED.value)


def _last_acceptance_entry_id(session: Session, finding_id: int) -> int | None:
    """The most recent audit entry that set this finding to ``risk accepted``."""
    return session.scalar(
        select(AuditEntry.id)
        .where(
            AuditEntry.finding_id == finding_id,
            AuditEntry.field == "status",
            AuditEntry.new_value == FindingStatus.RISK_ACCEPTED.value,
        )
        .order_by(AuditEntry.id.desc())
    )
