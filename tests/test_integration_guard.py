"""E-GUARD: the Postgres integration suite refuses any non-test database.

These are pure-function cases over ``guard_test_database_url`` (issue #138), so
they run under ``make test`` on SQLite with no Docker. They prove the guard
accepts the ``vt-test`` database and rejects anything else, which is what stops
``make test-integration`` ever pointing at a real or dev database.
"""

from __future__ import annotations

import pytest

from conftest import UnsafeTestDatabase, guard_test_database_url

pytestmark = pytest.mark.unit


def test_e_guard_accepts_the_vt_test_database() -> None:
    # The vt-test `db` service, on the Compose network and via a published port.
    guard_test_database_url("postgresql+psycopg://vt:vt@db:5432/vt")
    guard_test_database_url("postgresql+psycopg://vt:vt@localhost:5432/vt")
    guard_test_database_url("postgresql+psycopg://vt:vt@127.0.0.1:5432/vt")


@pytest.mark.parametrize(
    "url",
    [
        # Not Postgres (a stray SQLite URL must never be accepted here).
        "sqlite:///./vulntriage.db",
        # Wrong database name (a real/dev database, not the test one).
        "postgresql+psycopg://vt:vt@db:5432/production",
        "postgresql+psycopg://vt:vt@db:5432/vt_prod",
        # Host outside the test allowlist (a remote/managed database).
        "postgresql+psycopg://vt:vt@db.example.com:5432/vt",
        "postgresql+psycopg://vt:vt@10.0.0.5:5432/vt",
        # Garbage.
        "not-a-url",
    ],
)
def test_e_guard_refuses_a_non_test_database(url: str) -> None:
    with pytest.raises(UnsafeTestDatabase):
        guard_test_database_url(url)
