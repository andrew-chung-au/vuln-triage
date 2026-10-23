"""OSV matching: installed dependencies to findings (issue #77, task 5).

Given the asset's ``Dependency`` rows and an OSV client, this module:

1. Batches one ``(ecosystem, name, version)`` query per distinct installed
   package version (``version unknown`` entries are skipped: E10, no match).
2. Fetches each returned advisory in full, caching ``Advisory`` rows by id and
   ``modified`` so an unchanged advisory is not refetched.
3. Merges advisories whose alias sets intersect into one ``Vulnerability`` (E9),
   keyed by the CVE when present else the primary advisory id, and records every
   advisory id and alias in ``VulnerabilityAlias``.
4. Computes the fixed version for this dependency across every merged advisory's
   ranges and every vulnerable installed entry of that package (A6, the five-step
   rule in :mod:`vulntriage.ingest.osv_ranges`).
5. Reconciles each ``(asset, package, vulnerability)`` with its existing finding
   through :mod:`vulntriage.ingest.lifecycle`: a new vulnerable dependency gets an
   ``open`` finding and its first lifecycle; a re-scan may set ``fixed``,
   ``withdrawn``, reopen (E7) or restore (E4). An advisory already withdrawn when
   the scan first sees it creates no finding (E4).

Ranking (tier, rank inputs/reason) is task 7 and runs after enrichment, so a
newly created finding starts with placeholder rank fields that ``rank_asset``
overwrites in the same scan transaction.
"""

from __future__ import annotations

import datetime as dt
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vulntriage.db.enums import FindingStatus
from vulntriage.db.identity import identity_key
from vulntriage.db.models import (
    Advisory,
    Dependency,
    Finding,
    Vulnerability,
    VulnerabilityAlias,
)
from vulntriage.ingest.lifecycle import MatchState, apply_rescan, create_finding
from vulntriage.ingest.osv import OsvClientProtocol, Query
from vulntriage.ingest.osv_ranges import collect_intervals, fixed_version_from_intervals
from vulntriage.ingest.versions import compare


@dataclass
class _VulnGroup:
    """Advisories merged into one vulnerability during a single scan."""

    advisories: list[dict[str, Any]] = field(default_factory=list)
    ids: set[str] = field(default_factory=set)  # primary ids + aliases


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def _parse_modified(value: Any) -> dt.datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.UTC)


def _advisory_ids(advisory: dict[str, Any]) -> set[str]:
    """An advisory's own id plus every alias id (the alias set for E9)."""
    ids: set[str] = set()
    osv_id = advisory.get("id")
    if isinstance(osv_id, str):
        ids.add(osv_id)
    aliases = advisory.get("aliases")
    if isinstance(aliases, list):
        ids |= {a for a in aliases if isinstance(a, str)}
    return ids


def _cve_of(ids: set[str]) -> str | None:
    cves = sorted(i for i in ids if i.upper().startswith("CVE-"))
    return cves[0] if cves else None


def _primary_id(advisories: list[dict[str, Any]]) -> str:
    """The primary advisory id: the smallest OSV id, for a stable identity key."""
    return min(str(a.get("id")) for a in advisories if isinstance(a.get("id"), str))


def _is_withdrawn(advisory: dict[str, Any]) -> bool:
    return advisory.get("withdrawn") not in (None, "")


def _distinct_queries(deps: list[Dependency]) -> list[Query]:
    seen: set[tuple[str, str, str]] = set()
    queries: list[Query] = []
    for dep in deps:
        if dep.version is None:  # version unknown: no OSV match (E10)
            continue
        key = (dep.ecosystem, dep.name, dep.version)
        if key in seen:
            continue
        seen.add(key)
        queries.append(Query(dep.ecosystem, dep.name, dep.version))
    return queries


def match_asset(session: Session, asset_id: int, client: OsvClientProtocol) -> bool:
    """Match ``asset_id`` against OSV and drive every finding's lifecycle (task 8).

    Returns whether any finding is currently ``open`` or ``risk accepted`` (so the
    scan status is ``scanned, findings``). Called inside the scan's open
    transaction, after the ``Dependency`` rows are written and before commit.
    Raises :class:`vulntriage.ingest.osv.FeedUnavailable` straight through so the
    scan maps it to ``feed unavailable`` (E3).

    On a re-scan the installed versions may have changed, so this reconciles the
    asset's existing findings with the new OSV answer: a finding whose version
    left every live range, or whose advisories OSV no longer returns, is set
    ``fixed``; a withdrawn advisory sets ``withdrawn``; reinstatement restores or
    fixes; a returned vulnerable version reopens a ``fixed`` finding (E4/E7/E8).
    """
    deps = list(session.scalars(select(Dependency).where(Dependency.asset_id == asset_id)))
    queries = _distinct_queries(deps)

    results = client.query_batch(queries) if queries else []

    # Fetch each distinct advisory once (withdrawn ones included, so withdrawal
    # and reinstatement can be detected). Caching by id+modified is in the upsert.
    advisories: dict[str, dict[str, Any]] = {}
    for refs in results:
        for ref in refs:
            if ref.osv_id not in advisories:
                advisories[ref.osv_id] = client.get_vuln(ref.osv_id)

    groups = _group_by_alias(advisories)

    # Installed (ecosystem, package) -> dependency rows (A6 merges several files).
    deps_by_package: dict[tuple[str, str], list[Dependency]] = defaultdict(list)
    for dep in deps:
        if dep.version is not None:
            deps_by_package[(dep.ecosystem, dep.name)].append(dep)

    # The set of (vulnerability_id, ecosystem, package) reconciled this scan, so
    # the pass over existing findings below skips those already handled.
    seen: set[tuple[int, str, str]] = set()

    for group in groups.values():
        existing_vuln = _existing_vulnerability(session, group)
        for (ecosystem, package), entries in deps_by_package.items():
            if not _group_intervals_all(group, ecosystem, package):
                continue  # this vulnerability does not name this package at all
            state = _state_for(group, ecosystem, package, entries)
            finding = (
                _find_finding(session, asset_id, existing_vuln.id, ecosystem, package)
                if existing_vuln is not None
                else None
            )
            # Persist the vulnerability only when there is a finding to transition
            # or a new in-range, live match to create: an advisory withdrawn at
            # first sight, or an out-of-range version, records nothing (E4).
            if finding is None and not (state.in_range and not state.all_withdrawn):
                continue
            vuln = existing_vuln or _upsert_vulnerability(session, group)
            _record_advisories(session, group, vuln.id)  # record/refresh advisories+aliases
            _reconcile(session, asset_id, vuln.id, ecosystem, package, state, finding)
            seen.add((vuln.id, ecosystem, package))

    # Existing findings OSV did not mention this scan: the version left the range
    # (no advisory matched), so they are reconciled with an out-of-range state.
    existing = session.scalars(
        select(Finding).where(
            Finding.asset_id == asset_id,
            Finding.status.in_([FindingStatus.OPEN.value, FindingStatus.RISK_ACCEPTED.value]),
        )
    )
    for finding in existing:
        key = (finding.vulnerability_id, finding.ecosystem, finding.package)
        if key in seen:
            continue
        gone = MatchState(in_range=False, all_withdrawn=False, fixed_version=finding.fixed_version,
                          dependency_ids=[])
        apply_rescan(session, finding, gone)

    open_count = session.scalar(
        select(func.count())
        .select_from(Finding)
        .where(
            Finding.asset_id == asset_id,
            Finding.status.in_([FindingStatus.OPEN.value, FindingStatus.RISK_ACCEPTED.value]),
        )
    )
    return bool(open_count)


def _group_intervals_all(group: _VulnGroup, ecosystem: str, name: str) -> list:  # type: ignore[type-arg]
    """Intervals from every advisory (live or withdrawn) that names this package."""
    intervals = []
    for advisory in group.advisories:
        intervals += collect_intervals(advisory.get("affected", []) or [], ecosystem, name)
    return intervals


def _state_for(
    group: _VulnGroup, ecosystem: str, package: str, entries: list[Dependency]
) -> MatchState:
    """Compute the current match state for one (vulnerability, package)."""
    all_withdrawn = len(group.advisories) > 0 and all(
        _is_withdrawn(a) for a in group.advisories
    )
    # Range checks use only live (non-withdrawn) advisories.
    live_intervals = _group_intervals_live(group, ecosystem, package)
    matching_deps: list[Dependency] = []
    per_entry_fixed: list[str | None] = []
    for dep in entries:
        assert dep.version is not None
        matched, fixed = fixed_version_from_intervals(live_intervals, ecosystem, dep.version)
        if matched:
            matching_deps.append(dep)
            per_entry_fixed.append(fixed)
    in_range = bool(matching_deps)
    fixed_version = _merge_fixed(ecosystem, per_entry_fixed) if in_range else None
    return MatchState(
        in_range=in_range,
        all_withdrawn=all_withdrawn,
        fixed_version=fixed_version,
        dependency_ids=[d.id for d in matching_deps],
    )


def _group_intervals_live(group: _VulnGroup, ecosystem: str, name: str) -> list:  # type: ignore[type-arg]
    intervals = []
    for advisory in group.advisories:
        if _is_withdrawn(advisory):
            continue
        intervals += collect_intervals(advisory.get("affected", []) or [], ecosystem, name)
    return intervals


def _find_finding(
    session: Session, asset_id: int, vulnerability_id: int, ecosystem: str, package: str
) -> Finding | None:
    return session.scalar(
        select(Finding).where(
            Finding.asset_id == asset_id,
            Finding.ecosystem == ecosystem,
            Finding.package == package,
            Finding.vulnerability_id == vulnerability_id,
        )
    )


def _reconcile(
    session: Session,
    asset_id: int,
    vulnerability_id: int,
    ecosystem: str,
    package: str,
    state: MatchState,
    finding: Finding | None,
) -> None:
    """Create or transition the finding for one (asset, package, vulnerability)."""
    if finding is None:
        # A new finding is created only when the version is actually vulnerable
        # under a live advisory (the caller already checked this, E4).
        create_finding(session, asset_id, vulnerability_id, ecosystem, package, state)
        return
    apply_rescan(session, finding, state)


def _merge_fixed(ecosystem: str, per_entry: list[str | None]) -> str | None:
    """A6: the finding's fixed version is the highest per-entry value, or None if any entry has none."""
    if any(value is None for value in per_entry):
        return None
    highest = None
    for value in per_entry:
        assert value is not None
        if highest is None or compare(ecosystem, value, highest) > 0:
            highest = value
    return highest


def _group_by_alias(advisories: dict[str, dict[str, Any]]) -> dict[str, _VulnGroup]:
    """Union-find over advisories: two merge when their alias sets intersect (E9)."""
    groups: list[_VulnGroup] = []
    for advisory in advisories.values():
        ids = _advisory_ids(advisory)
        merged: _VulnGroup | None = None
        for group in list(groups):
            if group.ids & ids:
                if merged is None:
                    merged = group
                else:  # advisory bridges two groups: fold the second into the first
                    merged.advisories += group.advisories
                    merged.ids |= group.ids
                    groups.remove(group)
        if merged is None:
            merged = _VulnGroup()
            groups.append(merged)
        merged.advisories.append(advisory)
        merged.ids |= ids
    return {_primary_id(group.advisories): group for group in groups}


def _identity_key_of(group: _VulnGroup) -> str:
    return identity_key(_cve_of(group.ids), _primary_id(group.advisories))


def _existing_vulnerability(session: Session, group: _VulnGroup) -> Vulnerability | None:
    """The stored Vulnerability for this group, if one already exists (no create)."""
    return session.scalar(
        select(Vulnerability).where(Vulnerability.identity_key == _identity_key_of(group))
    )


def _upsert_vulnerability(session: Session, group: _VulnGroup) -> Vulnerability:
    """Find or create the Vulnerability for a group (advisories recorded separately)."""
    cve = _cve_of(group.ids)
    key = identity_key(cve, _primary_id(group.advisories))
    vuln = session.scalar(select(Vulnerability).where(Vulnerability.identity_key == key))
    if vuln is None:
        vuln = Vulnerability(identity_key=key, cve_id=cve)
        session.add(vuln)
        session.flush()  # assign vuln.id for the foreign keys below
    return vuln


def _record_advisories(session: Session, group: _VulnGroup, vulnerability_id: int) -> None:
    """Record (or refresh) every advisory and alias of the group for the vulnerability."""
    for advisory in group.advisories:
        _upsert_advisory(session, advisory, vulnerability_id)
    for alias in group.ids:
        if session.get(VulnerabilityAlias, alias) is None:
            session.add(VulnerabilityAlias(alias_id=alias, vulnerability_id=vulnerability_id))


def _upsert_advisory(session: Session, advisory: dict[str, Any], vulnerability_id: int) -> None:
    osv_id = str(advisory.get("id"))
    modified = _parse_modified(advisory.get("modified")) or _now()
    withdrawn = _parse_modified(advisory.get("withdrawn"))
    row = session.get(Advisory, osv_id)
    if row is None:
        session.add(
            Advisory(
                osv_id=osv_id,
                vulnerability_id=vulnerability_id,
                modified=modified,
                withdrawn_at=withdrawn,
                summary=_text(advisory.get("summary")),
                details=_text(advisory.get("details")),
                affected=advisory.get("affected", []) or [],
                references=advisory.get("references", []) or [],
            )
        )
        return
    # Cache by modified: refetch and rewrite only when OSV's modified moved on.
    if row.modified is None or modified > row.modified:
        row.modified = modified
        row.withdrawn_at = withdrawn
        row.summary = _text(advisory.get("summary"))
        row.details = _text(advisory.get("details"))
        row.affected = advisory.get("affected", []) or []
        row.references = advisory.get("references", []) or []


def _text(value: Any) -> str:
    return value if isinstance(value, str) else ""



