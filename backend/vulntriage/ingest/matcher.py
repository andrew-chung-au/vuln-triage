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
5. Creates one ``open`` ``Finding`` per ``(asset, package, vulnerability)`` with
   its ``FindingDependency`` links. An advisory already withdrawn when the scan
   first sees it creates no finding, and a scan only ever creates ``open``
   findings (E4).

Re-scan status transitions (``fixed``/``withdrawn``/restore, E4/E7) and the
audit trail are task 8; ranking (tier, rank inputs/reason) is task 7, so new
findings get placeholder rank fields (see ``_PLACEHOLDER_*``).
"""

from __future__ import annotations

import datetime as dt
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from vulntriage.db.enums import FindingStatus, Tier
from vulntriage.db.identity import identity_key
from vulntriage.db.models import (
    Advisory,
    Dependency,
    Finding,
    FindingDependency,
    Vulnerability,
    VulnerabilityAlias,
)
from vulntriage.ingest.osv import OsvClientProtocol, Query
from vulntriage.ingest.osv_ranges import collect_intervals, fixed_version_from_intervals
from vulntriage.ingest.versions import compare

# Ranking is task 7; findings are created with placeholder rank fields until then.
_PLACEHOLDER_TIER = Tier.P4.value
_PLACEHOLDER_RANK_INPUTS: dict[str, Any] = {}
_PLACEHOLDER_RANK_REASON = ""


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
    """Create findings for ``asset_id`` from OSV. Returns whether any were created.

    Called inside the scan's open transaction, after the ``Dependency`` rows are
    written and before commit. Raises :class:`vulntriage.ingest.osv.FeedUnavailable`
    straight through so the scan maps it to ``feed unavailable`` (E3).
    """
    deps = list(
        session.scalars(select(Dependency).where(Dependency.asset_id == asset_id))
    )
    queries = _distinct_queries(deps)
    if not queries:
        return False

    results = client.query_batch(queries)

    # Fetch each distinct advisory once, caching by id+modified.
    advisories: dict[str, dict[str, Any]] = {}
    for refs in results:
        for ref in refs:
            if ref.osv_id in advisories:
                continue
            advisories[ref.osv_id] = client.get_vuln(ref.osv_id)

    # An advisory already withdrawn at first sight creates no finding (E4): drop
    # it before grouping so it never contributes a range or an alias.
    live = {oid: adv for oid, adv in advisories.items() if not _is_withdrawn(adv)}

    groups = _group_by_alias(live)
    vuln_by_group = {gid: _upsert_vulnerability(session, group) for gid, group in groups.items()}

    # Distinct installed (ecosystem, package) pairs and their dependency rows,
    # so A6 merges the same package read from several files into one finding.
    deps_by_package: dict[tuple[str, str], list[Dependency]] = defaultdict(list)
    for dep in deps:
        if dep.version is not None:
            deps_by_package[(dep.ecosystem, dep.name)].append(dep)

    created = False
    # The backend evaluates the ranges itself (A10), so for each vulnerability
    # and each installed package it merges every advisory's intervals and asks
    # whether the installed versions fall inside.
    for gid, group in groups.items():
        vuln = vuln_by_group[gid]
        for (ecosystem, package), entries in deps_by_package.items():
            intervals = _group_intervals(group, ecosystem, package)
            if not intervals:
                continue
            matching_deps: list[Dependency] = []
            per_entry_fixed: list[str | None] = []
            for dep in entries:
                assert dep.version is not None
                matched, fixed = fixed_version_from_intervals(intervals, ecosystem, dep.version)
                if matched:
                    matching_deps.append(dep)
                    per_entry_fixed.append(fixed)
            if not matching_deps:  # step 3: nothing in range -> no finding
                continue
            fixed_version = _merge_fixed(ecosystem, per_entry_fixed)
            if _create_finding(
                session, asset_id, vuln, ecosystem, package, fixed_version, matching_deps
            ):
                created = True
    return created


def _group_intervals(group: _VulnGroup, ecosystem: str, name: str) -> list:  # type: ignore[type-arg]
    """Every interval for ecosystem+package across every advisory in the group (E9)."""
    intervals = []
    for advisory in group.advisories:
        intervals += collect_intervals(advisory.get("affected", []) or [], ecosystem, name)
    return intervals


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


def _upsert_vulnerability(session: Session, group: _VulnGroup) -> Vulnerability:
    """Find or create the Vulnerability for a group and record advisories and aliases."""
    cve = _cve_of(group.ids)
    key = identity_key(cve, _primary_id(group.advisories))

    vuln = session.scalar(
        select(Vulnerability).where(Vulnerability.identity_key == key)
    )
    if vuln is None:
        vuln = Vulnerability(identity_key=key, cve_id=cve)
        session.add(vuln)
        session.flush()  # assign vuln.id for the foreign keys below

    for advisory in group.advisories:
        _upsert_advisory(session, advisory, vuln.id)
    for alias in group.ids:
        if session.get(VulnerabilityAlias, alias) is None:
            session.add(VulnerabilityAlias(alias_id=alias, vulnerability_id=vuln.id))
    return vuln


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


def _create_finding(
    session: Session,
    asset_id: int,
    vuln: Vulnerability,
    ecosystem: str,
    package: str,
    fixed_version: str | None,
    deps: list[Dependency],
) -> bool:
    """Create the finding and its dependency links if it does not already exist."""
    existing = session.scalar(
        select(Finding).where(
            Finding.asset_id == asset_id,
            Finding.ecosystem == ecosystem,
            Finding.package == package,
            Finding.vulnerability_id == vuln.id,
        )
    )
    if existing is not None:
        return False  # re-scan transitions are task 8; a scan does not duplicate
    finding = Finding(
        asset_id=asset_id,
        vulnerability_id=vuln.id,
        ecosystem=ecosystem,
        package=package,
        fixed_version=fixed_version,
        status=FindingStatus.OPEN.value,
        tier=_PLACEHOLDER_TIER,
        rank_inputs=dict(_PLACEHOLDER_RANK_INPUTS),
        rank_reason=_PLACEHOLDER_RANK_REASON,
        first_detected_at=_now(),
    )
    session.add(finding)
    session.flush()  # assign finding.id for the link rows
    for dep in deps:
        session.add(FindingDependency(finding_id=finding.id, dependency_id=dep.id))
    return True
