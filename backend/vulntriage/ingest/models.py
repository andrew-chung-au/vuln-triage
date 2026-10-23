"""Plain result types shared by the lockfile parsers and the scan (issue #76).

The parsers are pure functions of text: they import no network client, and
this module holds only data.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Warning kinds (ScanWarning.kind). Only the first three make a scan incomplete.
VERSION_UNKNOWN = "version unknown"
INCLUDE_REFUSED = "include refused"
INCLUDE_NOT_FOUND = "include not found"
CONSTRAINTS_IGNORED = "constraints file ignored"
INDEX_IGNORED = "index option ignored"

INCOMPLETE_KINDS = frozenset({VERSION_UNKNOWN, INCLUDE_REFUSED, INCLUDE_NOT_FOUND})


class LockfileParseError(Exception):
    """A lockfile is malformed or in an unsupported format (E5)."""


@dataclass(frozen=True)
class Entry:
    ecosystem: str  # "PyPI" or "npm"
    name: str
    version: str | None  # None = "version unknown"
    source_file: str
    direct: bool


@dataclass(frozen=True)
class ScanWarning:
    kind: str
    file: str
    line: int | None
    message: str

    def as_dict(self) -> dict[str, object]:
        return {"kind": self.kind, "file": self.file, "line": self.line, "message": self.message}


@dataclass
class ParseResult:
    entries: list[Entry] = field(default_factory=list)
    warnings: list[ScanWarning] = field(default_factory=list)
    local_packages: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class IncludeTarget:
    """A ``-r`` target found in a requirements file, for the reader to resolve."""

    target: str
    line: int


@dataclass
class RequirementsResult:
    entries: list[Entry] = field(default_factory=list)
    warnings: list[ScanWarning] = field(default_factory=list)
    includes: list[IncludeTarget] = field(default_factory=list)
