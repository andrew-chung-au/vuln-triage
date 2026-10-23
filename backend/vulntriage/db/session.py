"""Engine and session factory. Nothing here opens a database at import time."""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker

DEFAULT_DATABASE_URL = "sqlite:///./.scratch/vulntriage.db"


def get_database_url() -> str:
    """The single database setting: ``DATABASE_URL`` or the SQLite default."""
    return os.environ.get("DATABASE_URL") or DEFAULT_DATABASE_URL


def enable_sqlite_foreign_keys(engine: Engine) -> None:
    """Turn on ``PRAGMA foreign_keys`` for every SQLite connection of ``engine``.

    SQLite ignores foreign keys unless this is set on each connection.
    """

    @event.listens_for(engine, "connect")
    def _set_pragma(dbapi_connection, _record) -> None:  # type: ignore[no-untyped-def]
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
        finally:
            cursor.close()


def create_db_engine(url: str | None = None) -> Engine:
    """Create an engine for ``url`` (default: :func:`get_database_url`)."""
    parsed = make_url(url or get_database_url())
    is_sqlite = parsed.get_backend_name() == "sqlite"
    if is_sqlite and parsed.database and parsed.database != ":memory:":
        Path(parsed.database).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(parsed)
    if is_sqlite:
        enable_sqlite_foreign_keys(engine)
    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(engine, expire_on_commit=False)
