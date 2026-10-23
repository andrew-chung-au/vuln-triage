"""U-UV: uv.lock parser (hand-written text; the parser is a pure function)."""

from __future__ import annotations

import pytest

from vulntriage.ingest.models import LockfileParseError
from vulntriage.ingest.uv_lock import parse_uv_lock

LOCK = """\
version = 1
requires-python = ">=3.12"

[[package]]
name = "My_App"
version = "0.1.0"
source = { virtual = "." }
dependencies = [{ name = "Requests" }]

[package.optional-dependencies]
extra = [{ name = "click" }]

[package.dev-dependencies]
dev = [{ name = "pytest" }]

[[package]]
name = "requests"
version = "2.31.0"
source = { registry = "https://pypi.org/simple" }
dependencies = [{ name = "urllib3" }]

[[package]]
name = "urllib3"
version = "2.0.7"
source = { registry = "https://pypi.org/simple" }

[[package]]
name = "click"
version = "8.1.7"
source = { registry = "https://pypi.org/simple" }

[[package]]
name = "pytest"
version = "8.0.0"
source = { registry = "https://pypi.org/simple" }
"""


def test_every_package_is_an_entry_and_the_project_is_skipped() -> None:
    result = parse_uv_lock(LOCK)
    by_name = {e.name: e for e in result.entries}
    assert set(by_name) == {"requests", "urllib3", "click", "pytest"}
    assert by_name["requests"].version == "2.31.0"
    assert all(e.source_file == "uv.lock" and e.ecosystem == "PyPI" for e in result.entries)
    assert result.warnings == []
    assert result.local_packages == []


def test_direct_flag_follows_the_project_package_dependencies() -> None:
    by_name = {e.name: e for e in parse_uv_lock(LOCK).entries}
    assert by_name["requests"].direct is True
    assert by_name["click"].direct is True
    assert by_name["pytest"].direct is True
    assert by_name["urllib3"].direct is False


def test_package_without_version_is_unknown_with_a_warning() -> None:
    text = 'version = 1\n[[package]]\nname = "Foo.Bar"\nsource = { directory = "x" }\n'
    result = parse_uv_lock(text)
    assert [(e.name, e.version) for e in result.entries] == [("foo-bar", None)]
    assert [w.kind for w in result.warnings] == ["version unknown"]
    assert result.warnings[0].file == "uv.lock"
    assert result.warnings[0].line is None


def test_editable_project_package_is_skipped_too() -> None:
    text = 'version = 1\n[[package]]\nname = "app"\nversion = "1"\nsource = { editable = "." }\n'
    assert parse_uv_lock(text).entries == []


def test_lockfile_with_no_packages_is_not_an_error() -> None:
    result = parse_uv_lock("version = 1\n")
    assert result.entries == [] and result.warnings == []


@pytest.mark.parametrize(
    "text",
    [
        "this is = = not toml",
        "version = 2\n",
        "[[package]]\nname = 'a'\nversion = '1'\n",
        'version = 1\npackage = "nope"\n',
        "version = 1\n[[package]]\nversion = '1'\n",
    ],
)
def test_malformed_lockfiles_raise(text: str) -> None:
    with pytest.raises(LockfileParseError):
        parse_uv_lock(text)
