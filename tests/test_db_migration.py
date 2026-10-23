"""Issue #26: the Alembic migration creates the schema and matches the models (U-SCHEMA)."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import inspect
from sqlalchemy.engine import Connection, Engine

from vulntriage.db.models import Base

ALEMBIC_INI = Path(__file__).resolve().parents[1] / "backend" / "alembic.ini"
EXPECTED_TABLES = {
    "users", "sessions", "assets", "scans", "dependencies", "vulnerabilities", "advisories",
    "vulnerability_aliases", "signals", "findings", "finding_dependencies", "lifecycles",
    "notification_jobs", "audit_entries",
}


def alembic_config(connection: Connection) -> Config:
    config = Config(str(ALEMBIC_INI))
    config.attributes["connection"] = connection
    return config


def app_tables(engine: Engine) -> set[str]:
    return set(inspect(engine).get_table_names()) - {"alembic_version"}


@pytest.fixture()
def connection(sqlite_engine: Engine) -> Iterator[Connection]:
    with sqlite_engine.connect() as conn:
        yield conn


@pytest.mark.unit
def test_upgrade_creates_exactly_the_tables_and_downgrade_removes_them(
    sqlite_engine: Engine, connection: Connection
) -> None:
    command.upgrade(alembic_config(connection), "head")
    connection.commit()
    assert app_tables(sqlite_engine) == EXPECTED_TABLES

    command.downgrade(alembic_config(connection), "base")
    connection.commit()
    assert app_tables(sqlite_engine) == set()


@pytest.mark.unit
def test_migrated_schema_has_no_drift_from_the_models(
    sqlite_engine: Engine, connection: Connection
) -> None:
    command.upgrade(alembic_config(connection), "head")
    connection.commit()
    context = MigrationContext.configure(connection)
    assert compare_metadata(context, Base.metadata) == []


@pytest.mark.unit
def test_migrated_schema_keeps_the_constraints(sqlite_engine: Engine, connection: Connection) -> None:
    command.upgrade(alembic_config(connection), "head")
    connection.commit()
    inspector = inspect(sqlite_engine)
    checks = {c["name"] for c in inspector.get_check_constraints("findings")}
    assert {"ck_findings_status", "ck_findings_tier", "ck_findings_ecosystem"} <= checks
    uniques = {u["name"] for u in inspector.get_unique_constraints("findings")}
    assert "uq_findings_identity" in uniques
    audit_checks = {c["name"] for c in inspector.get_check_constraints("audit_entries")}
    assert {"ck_audit_entries_one_target", "ck_audit_entries_risk_accepted_reason"} <= audit_checks
