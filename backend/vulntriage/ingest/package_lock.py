"""Parse ``package-lock.json`` text (pure function; no network, no file access)."""

from __future__ import annotations

import json
import re
from typing import Any

from vulntriage.ingest.models import (
    VERSION_UNKNOWN,
    Entry,
    LockfileParseError,
    ParseResult,
    ScanWarning,
)

SOURCE_FILE = "package-lock.json"
_MARKER = "node_modules/"

# VERIFY: the official semver.org 2.0.0 regular expression.
_SEMVER = re.compile(
    r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?"
)

_ROOT_DEP_FIELDS = ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies")


def is_semver(version: str) -> bool:
    return _SEMVER.fullmatch(version) is not None


def parse_package_lock(text: str) -> ParseResult:
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, RecursionError) as exc:
        raise LockfileParseError("package-lock.json is not valid JSON") from exc
    if not isinstance(data, dict):
        raise LockfileParseError("package-lock.json is not a JSON object")
    if data.get("lockfileVersion") not in (2, 3) or isinstance(data.get("lockfileVersion"), bool):
        raise LockfileParseError("unsupported lockfileVersion")
    packages = data.get("packages")
    if not isinstance(packages, dict):
        raise LockfileParseError("package-lock.json has no packages table")

    root = packages.get("", {})
    root_deps: set[str] = set()
    if isinstance(root, dict):
        for key in _ROOT_DEP_FIELDS:
            value = root.get(key)
            if isinstance(value, dict):
                root_deps |= set(value)

    result = ParseResult()
    for key, entry in packages.items():
        if key == "":
            continue
        if not isinstance(entry, dict):
            raise LockfileParseError("package-lock.json has an invalid package entry")
        if entry.get("link") is True or _MARKER not in key:
            result.local_packages.append(key)
            continue
        name = key.rsplit(_MARKER, 1)[1]
        version = entry.get("version")
        if not isinstance(version, str) or not is_semver(version):
            version = None
            result.warnings.append(
                ScanWarning(VERSION_UNKNOWN, SOURCE_FILE, None, f"{name}: version unknown")
            )
        top_level = key.count(_MARKER) == 1 and key.startswith(_MARKER)
        result.entries.append(
            Entry("npm", name, version, SOURCE_FILE, top_level and name in root_deps)
        )
    return result
