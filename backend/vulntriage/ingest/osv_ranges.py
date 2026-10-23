"""Interval evaluation and the fixed version for this dependency (issue #77).

A pure module (no network, no DB), mirroring the parser design so the
``U-FIXED`` cases test it directly. It implements the five-step rule from
``_docs/architecture.md`` § Ingestion and matching, which realises the defined
term "fixed version for this dependency" in ``_docs/specs.md``.

OSV shape used (``affected[]`` entries of an advisory):
- ``package``: ``{"ecosystem", "name"}``
- ``ranges[]``: ``{"type": "ECOSYSTEM"|"SEMVER"|"GIT", "events": [...]}`` where
  each event is ``{"introduced"|"fixed"|"last_affected"|"limit": "<value>"}``.
  ``introduced: "0"`` means "from the start"; ``fixed`` closes an interval
  exclusive; ``last_affected`` closes it inclusive; ``limit`` is ignored here.
- ``versions[]``: explicit affected versions, each a one-version interval.

``GIT`` ranges carry commit hashes, not versions, so they are skipped.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from vulntriage.ingest.versions import UnorderableVersion, VersionKey, parse_key

__all__ = [
    "Interval",
    "collect_intervals",
    "contains",
    "fixed_version",
    "fixed_version_from_intervals",
]


@dataclass(frozen=True)
class Interval:
    """A half-/fully-bounded affected interval for one ecosystem+package.

    ``introduced`` is the inclusive lower bound (None = from the start).
    ``fixed`` is the exclusive upper bound (the first unaffected version).
    ``last_affected`` is the inclusive upper bound. An interval with neither
    ``fixed`` nor ``last_affected`` is open-ended.
    """

    introduced: str | None
    fixed: str | None = None
    last_affected: str | None = None


def _events_to_intervals(events: list[dict[str, Any]]) -> list[Interval]:
    """Turn an OSV range's event list into intervals.

    Events arrive in OSV order. ``introduced`` opens an interval; the next
    ``fixed`` or ``last_affected`` closes it; a further ``introduced`` opens the
    next one. ``"0"`` as the introduced value means "from the start" (None).
    """
    intervals: list[Interval] = []
    current_introduced: str | None = None
    open_interval = False
    for event in events:
        if not isinstance(event, dict):
            continue
        if "introduced" in event:
            if open_interval:  # an introduced with no closing event: open-ended
                intervals.append(Interval(current_introduced))
            value = event["introduced"]
            current_introduced = None if value in ("0", 0) else _as_str(value)
            open_interval = True
        elif "fixed" in event and open_interval:
            intervals.append(Interval(current_introduced, fixed=_as_str(event["fixed"])))
            open_interval = False
        elif "last_affected" in event and open_interval:
            intervals.append(
                Interval(current_introduced, last_affected=_as_str(event["last_affected"]))
            )
            open_interval = False
        # "limit" and any other event type are ignored (architecture A11 note).
    if open_interval:
        intervals.append(Interval(current_introduced))
    return intervals


def _as_str(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def collect_intervals(affected: list[dict[str, Any]], ecosystem: str, name: str) -> list[Interval]:
    """Every interval for ``ecosystem``+``name`` across one advisory's affected list.

    ``name`` is the normalised package name; OSV package names are compared
    case-insensitively for PyPI (callers pass the normalised installed name and
    the OSV name is lower-cased here as a defensive measure).
    """
    intervals: list[Interval] = []
    for entry in affected:
        if not isinstance(entry, dict):
            continue
        package = entry.get("package")
        if not isinstance(package, dict):
            continue
        if package.get("ecosystem") != ecosystem:
            continue
        if not _name_matches(package.get("name"), name):
            continue
        for osv_range in entry.get("ranges", []) or []:
            if not isinstance(osv_range, dict):
                continue
            if osv_range.get("type") not in ("ECOSYSTEM", "SEMVER"):
                continue  # GIT ranges carry commit hashes, not versions
            events = osv_range.get("events")
            if isinstance(events, list):
                intervals += _events_to_intervals(events)
        for version in entry.get("versions", []) or []:
            if isinstance(version, str):
                intervals.append(Interval(version, last_affected=version))
    return intervals


def _name_matches(osv_name: Any, name: str) -> bool:
    return isinstance(osv_name, str) and osv_name.lower() == name.lower()


def contains(interval: Interval, ecosystem: str, version_key: VersionKey) -> bool:
    """Whether ``version_key`` falls inside ``interval`` under the ecosystem order."""
    try:
        if interval.introduced is not None:
            if version_key < parse_key(ecosystem, interval.introduced):
                return False
        if interval.fixed is not None:
            if not (version_key < parse_key(ecosystem, interval.fixed)):
                return False
        if interval.last_affected is not None:
            if version_key > parse_key(ecosystem, interval.last_affected):
                return False
    except UnorderableVersion:
        return False
    return True


def fixed_version_from_intervals(
    intervals: list[Interval], ecosystem: str, installed: str
) -> tuple[bool, str | None]:
    """The five-step rule over an already-collected interval set.

    ``intervals`` are all intervals for one ecosystem+package across every
    advisory merged into the finding (E9), so the result clears every range at
    once. Returns ``(matched, fixed)``: ``matched`` is whether the installed
    version falls in any interval (step 3); ``fixed`` is the fixed version for
    this dependency, or None when there is none.
    """
    try:
        v = parse_key(ecosystem, installed)
    except UnorderableVersion:
        return (False, None)

    containing = [iv for iv in intervals if contains(iv, ecosystem, v)]
    if not containing:  # step 3: C empty -> no finding
        return (False, None)

    # Step 4: candidates are the fixed values of containing intervals above v.
    candidates: list[str] = []
    for interval in containing:
        if interval.fixed is None:
            continue
        try:
            if parse_key(ecosystem, interval.fixed) > v:
                candidates.append(interval.fixed)
        except UnorderableVersion:
            continue

    # Step 5: the lowest candidate that lies outside every containing interval.
    qualifying = [
        c
        for c in candidates
        if not any(contains(iv, ecosystem, parse_key(ecosystem, c)) for iv in containing)
    ]
    if not qualifying:  # open-ended or last_affected-only interval (E1, A11)
        return (True, None)
    lowest = min(qualifying, key=lambda c: parse_key(ecosystem, c))
    return (True, lowest)


def fixed_version(
    affected: list[dict[str, Any]], ecosystem: str, name: str, installed: str
) -> tuple[bool, str | None]:
    """Apply the five-step rule for a single advisory's ``affected`` list."""
    intervals = collect_intervals(affected, ecosystem, name)
    return fixed_version_from_intervals(intervals, ecosystem, installed)
