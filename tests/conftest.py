"""Shared test harness: network guard, stub-mode check and SQLite fixtures."""

from __future__ import annotations

import os
from collections.abc import Iterator, Mapping

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from network_guard import install_network_guard, restore_network_guard

DEFAULT_MODE = "stub"
ACCEPTED_MODES = frozenset({DEFAULT_MODE})


class InvalidTestMode(RuntimeError):
    """Raised when LLM_MODE or RESPONDER_MODE is not the test stub."""


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


def pytest_configure(config: pytest.Config) -> None:
    try:
        validate_mode_environment(os.environ)
    except InvalidTestMode as exc:
        raise pytest.UsageError(str(exc)) from exc
    install_network_guard()


def pytest_unconfigure(config: pytest.Config) -> None:
    restore_network_guard()


@pytest.fixture()
def sqlite_engine() -> Iterator[Engine]:
    """A fresh in-memory SQLite engine with no tables, disposed after the test."""
    engine = create_engine(
        "sqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture()
def sqlite_session(sqlite_engine: Engine) -> Iterator[Session]:
    """A session bound to the per-test in-memory SQLite engine."""
    session = Session(sqlite_engine)
    try:
        yield session
    finally:
        session.close()
