"""#198: Migration 0002 adds ``internal error`` to the failure-reason checks.

These drive Alembic ``upgrade 0001`` / ``head`` / ``downgrade`` on the in-memory
SQLite engine, in the same style as ``test_db_migration.py``. They are ``unit``
only: under the Postgres harness the schema already exists at head, and the raw
inserts use SQLite's integer boolean, so they are not ``sqlite_integration``.
"""

from __future__ import annotations

import pytest
from alembic import command
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from test_db_migration import alembic_config

pytestmark = pytest.mark.unit


def _insert_asset(engine: Engine, reason: str | None) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO assets (name, criticality, internet_facing, repository_url,"
                " scan_status, scan_failure_reason) VALUES ('n', 'low', 0, 'u', 'scan failed', :r)"
            ),
            {"r": reason},
        )


def test_migration_adds_internal_error_and_still_rejects_other_values(sqlite_engine: Engine) -> None:
    with sqlite_engine.connect() as connection:
        command.upgrade(alembic_config(connection), "0001")
        connection.commit()
    with pytest.raises(IntegrityError):
        _insert_asset(sqlite_engine, "internal error")

    with sqlite_engine.connect() as connection:
        command.upgrade(alembic_config(connection), "head")
        connection.commit()
    _insert_asset(sqlite_engine, "internal error")
    _insert_asset(sqlite_engine, "feed unavailable")
    with pytest.raises(IntegrityError):
        _insert_asset(sqlite_engine, "something else")
    inspector = inspect(sqlite_engine)
    for table, name in (("assets", "ck_assets_scan_failure_reason"), ("scans", "ck_scans_failure_reason")):
        checks = {c["name"]: c["sqltext"] for c in inspector.get_check_constraints(table)}
        assert "internal error" in checks[name]

    # The scans constraint widened too.
    with sqlite_engine.begin() as conn:
        asset_id = conn.execute(text("SELECT id FROM assets LIMIT 1")).scalar_one()
        insert = (
            "INSERT INTO scans (asset_id, trigger, started_at, scan_status, failure_reason,"
            " warnings, trace_id) VALUES (:a, 'person', '2026-01-01', 'scan failed', :r, '[]', 't')"
        )
        conn.execute(text(insert), {"a": asset_id, "r": "internal error"})
    with pytest.raises(IntegrityError), sqlite_engine.begin() as conn:
        conn.execute(text(insert), {"a": asset_id, "r": "nope"})


def test_migration_downgrades_cleanly(sqlite_engine: Engine) -> None:
    with sqlite_engine.connect() as connection:
        command.upgrade(alembic_config(connection), "head")
        connection.commit()
        command.downgrade(alembic_config(connection), "0001")
        connection.commit()
    with pytest.raises(IntegrityError):
        _insert_asset(sqlite_engine, "internal error")
    _insert_asset(sqlite_engine, "feed unavailable")
