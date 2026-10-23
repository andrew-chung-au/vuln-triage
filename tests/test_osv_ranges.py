"""Fixed version for this dependency (issue #77, ``U-FIXED``): the five-step rule."""

from __future__ import annotations

import pytest

from vulntriage.ingest.osv_ranges import (
    Interval,
    collect_intervals,
    fixed_version,
    fixed_version_from_intervals,
)

pytestmark = pytest.mark.unit


def _affected(name: str, events: list[dict], ecosystem: str = "PyPI") -> list[dict]:
    return [
        {
            "package": {"ecosystem": ecosystem, "name": name},
            "ranges": [{"type": "ECOSYSTEM", "events": events}],
        }
    ]


# -- the spec example -------------------------------------------------------


def test_spec_example_two_release_lines() -> None:
    affected = _affected(
        "pkg",
        [
            {"introduced": "1.0.0"},
            {"fixed": "1.2.5"},
            {"introduced": "2.0.0"},
            {"fixed": "2.0.1"},
        ],
    )
    assert fixed_version(affected, "PyPI", "pkg", "1.2.0") == (True, "1.2.5")
    assert fixed_version(affected, "PyPI", "pkg", "2.0.0") == (True, "2.0.1")


def test_version_outside_every_range_is_clean() -> None:
    affected = _affected("pkg", [{"introduced": "1.0.0"}, {"fixed": "1.2.5"}])
    assert fixed_version(affected, "PyPI", "pkg", "1.2.5") == (False, None)
    assert fixed_version(affected, "PyPI", "pkg", "3.0.0") == (False, None)


# -- no fixed version (E1, A11) ---------------------------------------------


def test_open_ended_interval_gives_no_fixed_version() -> None:
    affected = _affected("pkg", [{"introduced": "1.0.0"}])
    assert fixed_version(affected, "PyPI", "pkg", "1.5.0") == (True, None)


def test_last_affected_only_gives_no_fixed_version() -> None:
    affected = _affected("pkg", [{"introduced": "1.0.0"}, {"last_affected": "1.9.9"}])
    assert fixed_version(affected, "PyPI", "pkg", "1.5.0") == (True, None)


def test_last_affected_is_inclusive() -> None:
    affected = _affected("pkg", [{"introduced": "1.0.0"}, {"last_affected": "1.9.9"}])
    assert fixed_version(affected, "PyPI", "pkg", "1.9.9")[0] is True
    assert fixed_version(affected, "PyPI", "pkg", "2.0.0")[0] is False


# -- merged ranges across advisories (E9) -----------------------------------


def test_fixed_is_outside_every_containing_interval() -> None:
    # Overlapping intervals: 1.5.0 is a fixed value but lies inside the second
    # containing interval, so the lowest qualifying fixed is 1.8.0.
    intervals = [
        Interval("1.0.0", fixed="1.5.0"),
        Interval("1.3.0", fixed="1.8.0"),
    ]
    assert fixed_version_from_intervals(intervals, "PyPI", "1.4.0") == (True, "1.8.0")


def test_introduced_zero_means_from_the_start() -> None:
    affected = _affected("pkg", [{"introduced": "0"}, {"fixed": "1.26.17"}])
    assert fixed_version(affected, "PyPI", "pkg", "1.0.0") == (True, "1.26.17")


# -- collection / filtering -------------------------------------------------


def test_only_matching_ecosystem_and_package_count() -> None:
    affected = [
        {"package": {"ecosystem": "npm", "name": "pkg"}, "ranges": [
            {"type": "SEMVER", "events": [{"introduced": "0"}, {"fixed": "2.0.0"}]}]},
        {"package": {"ecosystem": "PyPI", "name": "other"}, "ranges": [
            {"type": "ECOSYSTEM", "events": [{"introduced": "0"}, {"fixed": "9.9.9"}]}]},
    ]
    assert collect_intervals(affected, "PyPI", "pkg") == []
    assert fixed_version(affected, "npm", "pkg", "1.0.0") == (True, "2.0.0")


def test_git_ranges_are_skipped() -> None:
    affected = [
        {"package": {"ecosystem": "PyPI", "name": "pkg"},
         "ranges": [{"type": "GIT", "events": [{"introduced": "0"}, {"fixed": "abc123"}]}]},
    ]
    assert collect_intervals(affected, "PyPI", "pkg") == []


def test_explicit_versions_are_one_version_intervals() -> None:
    affected = [{"package": {"ecosystem": "PyPI", "name": "pkg"}, "versions": ["1.2.3"]}]
    assert fixed_version(affected, "PyPI", "pkg", "1.2.3") == (True, None)
    assert fixed_version(affected, "PyPI", "pkg", "1.2.4") == (False, None)


def test_package_name_match_is_case_insensitive() -> None:
    affected = _affected("PyYAML", [{"introduced": "0"}, {"fixed": "5.4"}])
    assert fixed_version(affected, "PyPI", "pyyaml", "5.1") == (True, "5.4")
