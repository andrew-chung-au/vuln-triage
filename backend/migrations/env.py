"""Alembic environment.

Uses a connection from ``config.attributes["connection"]`` when the caller
supplies one (the tests do), else an engine for ``DATABASE_URL``. Batch mode
is on so later migrations can alter tables on SQLite.
"""

from __future__ import annotations

from alembic import context

from vulntriage.db.models import Base
from vulntriage.db.session import create_db_engine, get_database_url

config = context.config
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=get_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _run(connection) -> None:  # type: ignore[no-untyped-def]
    context.configure(
        connection=connection, target_metadata=target_metadata, render_as_batch=True
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connection = config.attributes.get("connection")
    if connection is not None:
        _run(connection)
        return
    engine = create_db_engine()
    try:
        with engine.connect() as connection:
            _run(connection)
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
