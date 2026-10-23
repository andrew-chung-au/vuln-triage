"""U-NPM: package-lock.json parser (hand-written text)."""

from __future__ import annotations

import json

import pytest

from vulntriage.ingest.models import LockfileParseError
from vulntriage.ingest.package_lock import parse_package_lock


def lock(packages: dict, version: int = 3) -> str:
    return json.dumps({"name": "app", "lockfileVersion": version, "packages": packages})


PACKAGES = {
    "": {"name": "app", "dependencies": {"a": "^1"}, "devDependencies": {"@types/node": "^20"}},
    "node_modules/a": {"version": "1.2.3"},
    "node_modules/a/node_modules/b": {"version": "0.0.1-beta.2+build5"},
    "node_modules/b": {"version": "2.0.0"},
    "node_modules/@types/node": {"version": "20.1.0"},
    "node_modules/mine": {"resolved": "packages/mine", "link": True},
    "packages/mine": {"version": "1.0.0"},
}


def test_entries_cover_transitive_and_nested_packages() -> None:
    result = parse_package_lock(lock(PACKAGES))
    got = [(e.name, e.version, e.direct) for e in result.entries]
    assert got == [
        ("a", "1.2.3", True),
        ("b", "0.0.1-beta.2+build5", False),
        ("b", "2.0.0", False),
        ("@types/node", "20.1.0", True),
    ]
    assert all(e.ecosystem == "npm" and e.source_file == "package-lock.json" for e in result.entries)
    assert result.warnings == []


def test_link_and_workspace_entries_are_local_packages_without_warning() -> None:
    result = parse_package_lock(lock(PACKAGES))
    assert result.local_packages == ["node_modules/mine", "packages/mine"]
    assert result.warnings == []


def test_missing_or_invalid_version_is_unknown_with_a_warning() -> None:
    result = parse_package_lock(lock({"": {}, "node_modules/x": {}, "node_modules/y": {"version": "latest"}}))
    assert [(e.name, e.version) for e in result.entries] == [("x", None), ("y", None)]
    assert [w.kind for w in result.warnings] == ["version unknown", "version unknown"]


def test_lockfile_version_2_is_accepted() -> None:
    assert parse_package_lock(lock({"": {}}, version=2)).entries == []


@pytest.mark.parametrize("version", [1, 4, "3", True, None])
def test_unsupported_lockfile_version_raises(version: object) -> None:
    text = json.dumps({"lockfileVersion": version, "packages": {}})
    with pytest.raises(LockfileParseError, match="unsupported lockfileVersion"):
        parse_package_lock(text)


def test_missing_lockfile_version_raises() -> None:
    with pytest.raises(LockfileParseError, match="unsupported lockfileVersion"):
        parse_package_lock('{"packages": {}}')


@pytest.mark.parametrize("text", ["{not json", "[]", '{"lockfileVersion": 3}', '{"lockfileVersion": 3, "packages": {"node_modules/a": 5}}'])
def test_invalid_documents_raise(text: str) -> None:
    with pytest.raises(LockfileParseError):
        parse_package_lock(text)
