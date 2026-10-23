"""Version ordering per ecosystem (issue #77): PEP 440 and SemVer 2.0.0 precedence."""

from __future__ import annotations

import pytest

from vulntriage.ingest.versions import UnorderableVersion, compare, parse_key

pytestmark = pytest.mark.unit


# -- PyPI (PEP 440 through packaging) ---------------------------------------


def test_pypi_leading_v_normalises() -> None:
    assert compare("PyPI", "v1.2.5", "1.2.5") == 0


@pytest.mark.parametrize(
    ("a", "b"),
    [
        ("1.2.0", "1.2.5"),
        ("1.9.0", "1.10.0"),  # not a string compare
        ("2.0.0a1", "2.0.0"),  # pre-release below release
        ("1.0.0.dev1", "1.0.0"),
        ("1.26.9", "1.26.17"),
    ],
)
def test_pypi_strict_ordering(a: str, b: str) -> None:
    assert compare("PyPI", a, b) == -1
    assert compare("PyPI", b, a) == 1


def test_pypi_sorted_uses_the_key() -> None:
    versions = ["1.26.17", "1.26.9", "2.0.6", "1.26.9rc1"]
    ordered = sorted(versions, key=lambda v: parse_key("PyPI", v))
    assert ordered == ["1.26.9rc1", "1.26.9", "1.26.17", "2.0.6"]


# -- npm (SemVer 2.0.0) -----------------------------------------------------


def test_npm_leading_v_normalises() -> None:
    assert compare("npm", "v1.2.3", "1.2.3") == 0


def test_npm_precedence_chain_semver_spec() -> None:
    # SemVer 2.0.0 §11.4: the documented increasing precedence.
    chain = [
        "1.0.0-alpha",
        "1.0.0-alpha.1",
        "1.0.0-alpha.beta",
        "1.0.0-beta",
        "1.0.0-beta.2",
        "1.0.0-beta.11",
        "1.0.0-rc.1",
        "1.0.0",
    ]
    for lower, higher in zip(chain, chain[1:]):
        assert compare("npm", lower, higher) == -1, (lower, higher)


@pytest.mark.parametrize(("a", "b"), [("1.2.0", "1.10.0"), ("1.2.9", "1.3.0"), ("0.9.0", "1.0.0")])
def test_npm_numeric_not_string_ordering(a: str, b: str) -> None:
    assert compare("npm", a, b) == -1


def test_npm_build_metadata_ignored() -> None:
    assert compare("npm", "1.0.0+build.1", "1.0.0+build.2") == 0


# -- failure modes ----------------------------------------------------------


@pytest.mark.parametrize(
    ("ecosystem", "value"),
    [("npm", "1.2"), ("npm", "not-a-version"), ("PyPI", "not a version"), ("Go", "1.0.0")],
)
def test_unorderable_versions_raise(ecosystem: str, value: str) -> None:
    with pytest.raises(UnorderableVersion):
        parse_key(ecosystem, value)
