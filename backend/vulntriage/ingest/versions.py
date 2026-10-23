"""Version ordering per ecosystem (issue #77; architecture.md § Ingestion and matching).

Used for "lowest version greater than", range checks and the fixed version. No
raw string compare: PyPI uses PEP 440 through ``packaging`` (already a
dependency), npm uses SemVer 2.0.0 precedence implemented here so no new
dependency is added (a SemVer library is approval-gated). ``node-semver`` reads
a leading ``v`` loosely, so we strip one before parsing.

``parse_key(ecosystem, value)`` returns an opaque, orderable key: two keys from
the same ecosystem support ``<``, ``>`` and ``==`` and work with ``sorted``. A
parse that fails raises :class:`UnorderableVersion`; the caller decides what an
unorderable version means (an OSV range the backend cannot evaluate records a
"range evaluation mismatch" warning, A10).
"""

from __future__ import annotations

import re

from packaging.version import InvalidVersion, Version

from vulntriage.db.enums import Ecosystem

__all__ = ["UnorderableVersion", "VersionKey", "compare", "parse_key"]

# SemVer 2.0.0 core + optional pre-release and build metadata (semver.org).
_SEMVER = re.compile(
    r"(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+(?:[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?"
)
_NUMERIC = re.compile(r"\d+")


class UnorderableVersion(ValueError):
    """A version string cannot be ordered under the ecosystem's rules."""


class VersionKey:
    """An orderable version key. Keys compare only within the same ecosystem."""

    __slots__ = ("_order", "_text")

    def __init__(self, order: tuple[object, ...], text: str) -> None:
        self._order = order
        self._text = text

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"VersionKey({self._text!r})"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, VersionKey) and self._order == other._order

    def __hash__(self) -> int:
        return hash(self._order)

    def __lt__(self, other: "VersionKey") -> bool:
        return _lt(self._order, other._order)

    def __le__(self, other: "VersionKey") -> bool:
        return self == other or _lt(self._order, other._order)

    def __gt__(self, other: "VersionKey") -> bool:
        return not (self == other or _lt(self._order, other._order))

    def __ge__(self, other: "VersionKey") -> bool:
        return not _lt(self._order, other._order)


def _lt(a: tuple[object, ...], b: tuple[object, ...]) -> bool:
    """Lexicographic less-than over heterogeneous, possibly nested, key tuples."""
    for left, right in zip(a, b):
        if left == right:
            continue
        if isinstance(left, tuple) and isinstance(right, tuple):
            return _lt(left, right)
        return bool(left < right)  # type: ignore[operator]
    return len(a) < len(b)


def _strip_leading_v(value: str) -> str:
    return value[1:] if value[:1] in ("v", "V") else value


def _prerelease_order(prerelease: str | None) -> tuple[object, ...]:
    """SemVer 2.0.0 §11 pre-release precedence.

    A release (no pre-release) outranks every pre-release, so it sorts as a
    trailing ``(1,)`` while any pre-release begins ``(0, ...)``. Numeric
    identifiers compare numerically and rank below alphanumeric ones.
    """
    if prerelease is None:
        return (1,)
    identifiers: list[object] = [0]
    for part in prerelease.split("."):
        if _NUMERIC.fullmatch(part):
            identifiers.append((0, int(part)))  # numeric < alphanumeric
        else:
            identifiers.append((1, part))
    return tuple(identifiers)


def _semver_order(value: str) -> tuple[object, ...]:
    match = _SEMVER.fullmatch(_strip_leading_v(value.strip()))
    if match is None:
        raise UnorderableVersion(f"not a SemVer version: {value!r}")
    return (
        int(match.group("major")),
        int(match.group("minor")),
        int(match.group("patch")),
        _prerelease_order(match.group("prerelease")),
    )


def _pypi_order(value: str) -> tuple[object, ...]:
    try:
        version = Version(value)
    except InvalidVersion as exc:
        raise UnorderableVersion(f"not a PEP 440 version: {value!r}") from exc
    # Version implements PEP 440 rich comparison directly, so it is its own key.
    return (version,)


def parse_key(ecosystem: str, value: str) -> VersionKey:
    """An orderable key for ``value`` under ``ecosystem``; raises UnorderableVersion."""
    if ecosystem == Ecosystem.PYPI.value:
        return VersionKey(_pypi_order(value), value)
    if ecosystem == Ecosystem.NPM.value:
        return VersionKey(_semver_order(value), value)
    raise UnorderableVersion(f"unknown ecosystem: {ecosystem!r}")


def compare(ecosystem: str, a: str, b: str) -> int:
    """-1, 0 or 1 for ``a`` versus ``b`` under ``ecosystem``'s ordering."""
    ka = parse_key(ecosystem, a)
    kb = parse_key(ecosystem, b)
    if ka == kb:
        return 0
    return -1 if ka < kb else 1
