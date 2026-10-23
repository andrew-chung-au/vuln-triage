"""Parse ``uv.lock`` text (pure function; no network, no file access)."""

from __future__ import annotations

import tomllib
from typing import Any

from packaging.utils import canonicalize_name

from vulntriage.ingest.models import (
    VERSION_UNKNOWN,
    Entry,
    LockfileParseError,
    ParseResult,
    ScanWarning,
)

SOURCE_FILE = "uv.lock"


def _is_project_package(package: dict[str, Any]) -> bool:
    source = package.get("source")
    if not isinstance(source, dict):
        return False
    return source.get("virtual") == "." or source.get("editable") == "."


def _dependency_names(value: Any) -> set[str]:
    """Names in a list of ``{name = ...}`` tables, or a table of such lists."""
    names: set[str] = set()
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict) and isinstance(item.get("name"), str):
                names.add(canonicalize_name(item["name"]))
    elif isinstance(value, dict):
        for inner in value.values():
            names |= _dependency_names(inner)
    return names


def parse_uv_lock(text: str) -> ParseResult:
    # VERIFY: uv lock format: root ``version = 1``, ``[[package]]`` tables, the
    # project's own package has ``source = { virtual = "." }`` or
    # ``{ editable = "." }``, and its dependencies are in ``dependencies``,
    # ``optional-dependencies`` and ``dev-dependencies``.
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise LockfileParseError("uv.lock is not valid TOML") from exc
    if data.get("version") != 1:
        raise LockfileParseError("unsupported uv.lock version")
    packages = data.get("package", [])
    if "package" not in data:
        # A lockfile with no packages has no [[package]] tables at all.
        packages = []
    if not isinstance(packages, list) or not all(isinstance(p, dict) for p in packages):
        raise LockfileParseError("uv.lock has no valid package list")

    direct: set[str] = set()
    for package in packages:
        if _is_project_package(package):
            direct |= _dependency_names(package.get("dependencies"))
            direct |= _dependency_names(package.get("optional-dependencies"))
            direct |= _dependency_names(package.get("dev-dependencies"))

    result = ParseResult()
    for package in packages:
        if _is_project_package(package):
            continue
        raw_name = package.get("name")
        if not isinstance(raw_name, str) or not raw_name:
            raise LockfileParseError("uv.lock package without a name")
        name = canonicalize_name(raw_name)
        version = package.get("version")
        if not isinstance(version, str) or not version:
            version = None
            result.warnings.append(
                ScanWarning(VERSION_UNKNOWN, SOURCE_FILE, None, f"{name}: version unknown")
            )
        result.entries.append(Entry("PyPI", name, version, SOURCE_FILE, name in direct))
    return result
