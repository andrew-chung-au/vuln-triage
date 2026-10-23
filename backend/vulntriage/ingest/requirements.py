"""Parse ``requirements.txt`` text (pure function; no network, no file access).

``-r`` includes are returned as targets for the reader to resolve with
:func:`resolve_include`; index options and URLs are never followed.
"""

from __future__ import annotations

import posixpath
import re

from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion, Version

from vulntriage.ingest.models import (
    CONSTRAINTS_IGNORED,
    INDEX_IGNORED,
    VERSION_UNKNOWN,
    Entry,
    IncludeTarget,
    RequirementsResult,
    ScanWarning,
)

_NAME = re.compile(r"([A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)\s*(?:\[[^\]]*\])?\s*(.*)", re.S)
_EXACT = re.compile(r"(===|==)\s*([^\s,;]+)")
_INCLUDE_FLAGS = ("--requirement", "-r")
_CONSTRAINT_FLAGS = ("--constraint", "-c")
_INDEX_FLAGS = ("--index-url", "--extra-index-url", "--find-links", "-i", "-f")
_EDITABLE_FLAGS = ("--editable", "-e")


def _logical_lines(text: str) -> list[tuple[int, str]]:
    """Join ``\\`` continuations; return (1-based first line number, text)."""
    out: list[tuple[int, str]] = []
    buffer = ""
    start = 0
    for number, raw in enumerate(text.splitlines(), start=1):
        if not buffer:
            start = number
        line = raw.rstrip()
        if line.endswith("\\"):
            buffer += line[:-1] + " "
            continue
        out.append((start, buffer + line))
        buffer = ""
    if buffer:
        out.append((start, buffer))
    return out


def _strip_comment(line: str) -> str:
    if line.lstrip().startswith("#"):
        return ""
    match = re.search(r"\s#", line)
    return line[: match.start()] if match else line


def _flag_value(line: str, flags: tuple[str, ...]) -> tuple[bool, str]:
    """If ``line`` starts with one of ``flags``, return (True, value)."""
    for flag in flags:
        if not line.startswith(flag):
            continue
        rest = line[len(flag) :]
        if flag.startswith("--"):
            if rest.startswith("="):
                return True, rest[1:].strip()
            if rest[:1].isspace():
                return True, rest.strip()
        else:
            if rest[:1] in (" ", "\t", "="):
                return True, rest.lstrip(" \t=").strip()
            if rest and not rest.startswith("-"):
                return True, rest.strip()  # -rfile
    return False, ""


def _name_from_url(value: str) -> str:
    egg = re.search(r"[#&]egg=([A-Za-z0-9._-]+)", value)
    if egg:
        return canonicalize_name(egg.group(1))
    base = re.split(r"[#?]", value, maxsplit=1)[0].rstrip("/")
    base = base.rsplit("/", 1)[-1]
    base = re.sub(r"\.git$", "", base)
    for suffix in (".whl", ".tar.gz", ".zip"):
        if base.endswith(suffix):
            base = base[: -len(suffix)].split("-", 1)[0]
    name = canonicalize_name(base)
    return name if re.search(r"[a-z0-9]", name) else "unknown"


def _unknown(name: str, source_file: str, line: int, why: str) -> tuple[Entry, ScanWarning]:
    return (
        Entry("PyPI", name, None, source_file, True),
        ScanWarning(VERSION_UNKNOWN, source_file, line, f"{name}: {why}"),
    )


def parse_requirements(text: str, source_file: str) -> RequirementsResult:
    result = RequirementsResult()
    for number, raw in _logical_lines(text):
        line = _strip_comment(raw).strip()
        if not line:
            continue

        if line.startswith("-"):
            is_include, target = _flag_value(line, _INCLUDE_FLAGS)
            if is_include:
                result.includes.append(IncludeTarget(target, number))
                continue
            if _flag_value(line, _CONSTRAINT_FLAGS)[0]:
                result.warnings.append(
                    ScanWarning(CONSTRAINTS_IGNORED, source_file, number, "constraints file ignored")
                )
                continue
            if _flag_value(line, _INDEX_FLAGS)[0]:
                result.warnings.append(
                    ScanWarning(INDEX_IGNORED, source_file, number, "index option ignored")
                )
                continue
            is_editable, target = _flag_value(line, _EDITABLE_FLAGS)
            if is_editable:
                entry, warning = _unknown(
                    _name_from_url(target), source_file, number, "editable requirement, version unknown"
                )
                result.entries.append(entry)
                result.warnings.append(warning)
            # Any other option (--no-binary, --prefer-binary, ...) is ignored.
            continue

        # Per-requirement options (--hash=..., --config-settings ...) are ignored.
        line = re.split(r"\s--[A-Za-z]", line, maxsplit=1)[0].strip()

        if re.match(r"[A-Za-z][A-Za-z0-9+.-]*://", line) or re.match(r"git\+", line):
            entry, warning = _unknown(
                _name_from_url(line), source_file, number, "URL requirement, version unknown"
            )
            result.entries.append(entry)
            result.warnings.append(warning)
            continue

        match = _NAME.fullmatch(line)
        if not match:
            result.warnings.append(
                ScanWarning(VERSION_UNKNOWN, source_file, number, "unparseable requirement line")
            )
            continue
        name = canonicalize_name(match.group(1))
        rest = match.group(2).strip()

        if rest.startswith("@"):
            entry, warning = _unknown(name, source_file, number, "URL requirement, version unknown")
        elif ";" in rest:
            entry, warning = _unknown(name, source_file, number, "environment marker, version unknown")
        else:
            exact = _EXACT.fullmatch(rest)
            version: str | None = None
            if exact:
                candidate = exact.group(2)
                try:
                    if "*" not in candidate:
                        Version(candidate)
                        version = candidate
                except InvalidVersion:
                    version = None
            if version is not None:
                result.entries.append(Entry("PyPI", name, version, source_file, True))
                continue
            entry, warning = _unknown(name, source_file, number, "version unknown")
        result.entries.append(entry)
        result.warnings.append(warning)
    return result


def resolve_include(including_file: str, target: str) -> str | None:
    """Resolve a ``-r`` target to a repository-relative path, or None to refuse.

    Refused: empty, NUL, backslash, any ``:`` (URL scheme or drive letter), an
    absolute path, and any path that leaves the repository root.
    """
    if not target or "\x00" in target or "\\" in target or ":" in target:
        return None
    if target.startswith("/"):
        return None
    joined = posixpath.normpath(posixpath.join(posixpath.dirname(including_file), target))
    if joined in (".", "..") or joined.startswith("../") or joined.startswith("/"):
        return None
    return joined
