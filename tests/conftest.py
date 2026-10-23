"""Shared test harness: network guard, stub-mode check and DB fixtures.

By default the DB fixtures are in-memory SQLite (``make test``; no Docker). When
``VT_TEST_DATABASE_URL`` is set they are a real Postgres database in the
``vt-test`` Compose project (``make test-integration``; issue #138): the schema
is built once by Alembic ``upgrade head`` and each test is isolated by a
transaction rollback. The ``E-GUARD`` check refuses any URL that is not the
test database, so the integration suite can never touch a real or dev database.

The public fixtures (``db_engine``/``db_session`` and their legacy
``sqlite_engine``/``sqlite_session`` aliases) have the same shape in both modes,
so the existing integration cases run unchanged against either backend.
"""

from __future__ import annotations

import os
from collections.abc import Iterator, Mapping

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from network_guard import install_network_guard, restore_network_guard
from vulntriage.db.models import Base
from vulntriage.db.session import enable_sqlite_foreign_keys

DEFAULT_MODE = "stub"
ACCEPTED_MODES = frozenset({DEFAULT_MODE})

# When set, the DB fixtures use this Postgres database instead of SQLite.
TEST_DATABASE_URL_ENV = "VT_TEST_DATABASE_URL"

# E-GUARD: the only database name and hosts the integration suite may use. The
# vt-test Compose project's `db` service is reachable as `db` (on the Compose
# network) or `localhost`/`127.0.0.1` (when the port is published to the host).
GUARD_ALLOWED_DB_NAME = "vt"
GUARD_ALLOWED_HOSTS = frozenset({"db", "localhost", "127.0.0.1"})


class InvalidTestMode(RuntimeError):
    """Raised when LLM_MODE or RESPONDER_MODE is not the test stub."""


class UnsafeTestDatabase(RuntimeError):
    """E-GUARD: raised when VT_TEST_DATABASE_URL is not the test database."""


def validate_mode_environment(environ: Mapping[str, str]) -> None:
    """Refuse any mode other than ``stub``; an unset mode means ``stub``.

    The function is pure: it reads only the mapping it is given and never
    touches ``.env`` or the live environment by itself.
    """
    for name in ("LLM_MODE", "RESPONDER_MODE"):
        value = environ.get(name, DEFAULT_MODE)
        if value not in ACCEPTED_MODES:
            raise InvalidTestMode(
                f"{name}={value!r} is not allowed in tests; "
                f"only {DEFAULT_MODE!r} (or unset) is accepted"
            )


def guard_test_database_url(url: str) -> None:
    """E-GUARD: raise unless ``url`` names the ``vt-test`` Postgres database.

    Pure: it inspects only the URL it is given. It refuses a non-Postgres URL,
    a database name other than ``vt``, and a host outside the test allowlist, so
    the integration suite cannot be pointed at a real or dev database.
    """
    try:
        parsed = make_url(url)
    except Exception as exc:  # noqa: BLE001 - any parse failure is unsafe
        raise UnsafeTestDatabase(f"{TEST_DATABASE_URL_ENV} is not a valid URL: {url!r}") from exc

    backend = parsed.get_backend_name()
    if backend != "postgresql":
        raise UnsafeTestDatabase(
            f"{TEST_DATABASE_URL_ENV} must be a postgresql URL, got {backend!r}"
        )
    if parsed.database != GUARD_ALLOWED_DB_NAME:
        raise UnsafeTestDatabase(
            f"{TEST_DATABASE_URL_ENV} database must be {GUARD_ALLOWED_DB_NAME!r} "
            f"(the vt-test database), got {parsed.database!r}"
        )
    host = (parsed.host or "").lower()
    if host not in GUARD_ALLOWED_HOSTS:
        raise UnsafeTestDatabase(
            f"{TEST_DATABASE_URL_ENV} host must be one of "
            f"{sorted(GUARD_ALLOWED_HOSTS)} (the vt-test service), got {host!r}"
        )


def _run_migrations(url: str) -> None:
    """Build the schema with Alembic ``upgrade head`` against ``url``.

    Imported lazily so the SQLite path never loads Alembic.
    """
    from pathlib import Path

    from alembic import command
    from alembic.config import Config

    ini = Path(__file__).resolve().parents[1] / "backend" / "alembic.ini"
    config = Config(str(ini))
    # The env reads DATABASE_URL (get_database_url); point it at the test DB.
    os.environ["DATABASE_URL"] = url
    command.upgrade(config, "head")


def pytest_configure(config: pytest.Config) -> None:
    try:
        validate_mode_environment(os.environ)
    except InvalidTestMode as exc:
        raise pytest.UsageError(str(exc)) from exc

    url = os.environ.get(TEST_DATABASE_URL_ENV)
    if url:
        # E-GUARD before anything connects.
        try:
            guard_test_database_url(url)
        except UnsafeTestDatabase as exc:
            raise pytest.UsageError(str(exc)) from exc
        # Build the schema once for the whole Postgres session.
        _run_migrations(url)

    install_network_guard()


def pytest_unconfigure(config: pytest.Config) -> None:
    restore_network_guard()


def _make_sqlite_engine() -> Engine:
    engine = create_engine(
        "sqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    enable_sqlite_foreign_keys(engine)
    return engine


@pytest.fixture()
def db_engine() -> Iterator[Engine]:
    """A per-test database engine.

    SQLite (default): a fresh in-memory engine with no tables; the caller's
    ``factory`` fixture runs ``Base.metadata.create_all`` as before.

    Postgres (``VT_TEST_DATABASE_URL`` set): an engine bound to a single
    connection running one outer transaction, rolled back after the test so no
    data persists between tests. The schema was built once by Alembic in
    ``pytest_configure``; ``create_all`` on this engine is a no-op because the
    tables already exist (``checkfirst`` is on by default), so the existing
    ``factory`` fixtures work unchanged.
    """
    url = os.environ.get(TEST_DATABASE_URL_ENV)
    if not url:
        engine = _make_sqlite_engine()
        try:
            yield engine
        finally:
            engine.dispose()
        return

    # Postgres: isolate each test in a transaction that is rolled back. Binding
    # the engine to one connection with an open transaction means every session
    # and every `create_all(checkfirst=True)` runs inside it, and the rollback
    # undoes all data changes at teardown.
    outer = create_engine(url)
    connection = outer.connect()
    transaction = connection.begin()
    bound = create_engine(url, poolclass=StaticPool, creator=lambda: connection.connection)
    try:
        yield bound
    finally:
        bound.dispose()
        if transaction.is_active:
            transaction.rollback()
        connection.close()
        outer.dispose()


@pytest.fixture()
def db_session(db_engine: Engine) -> Iterator[Session]:
    """A session bound to the per-test engine."""
    session = Session(db_engine)
    try:
        yield session
    finally:
        session.close()


# Legacy aliases: the existing integration modules depend on these names. They
# now follow VT_TEST_DATABASE_URL too, so the same cases run on Postgres when it
# is set and on SQLite otherwise.
@pytest.fixture()
def sqlite_engine(db_engine: Engine) -> Engine:
    return db_engine


@pytest.fixture()
def sqlite_session(db_session: Session) -> Session:
    return db_session
