"""Task 1 smoke test: the app imports and the shared harness works."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from conftest import InvalidTestMode, validate_mode_environment
from vulntriage.main import app


@pytest.mark.unit
def test_smoke(sqlite_engine: Engine, sqlite_session: Session) -> None:
    assert isinstance(app, FastAPI)
    # Routes grow by task: #76 POST /assets; #81 auth; #82 the resource endpoints.
    paths = app.openapi()["paths"]
    assert set(paths) == {
        "/assets", "/assets/{asset_id}", "/assets/{asset_id}/rescan",
        "/findings", "/findings/{finding_id}", "/findings/{finding_id}/risk-acceptance",
        "/auth/login", "/auth/logout", "/auth/me",
    }
    assert set(paths["/assets"]) == {"get", "post"}
    assert set(paths["/assets/{asset_id}"]) == {"get", "patch"}
    assert set(paths["/assets/{asset_id}/rescan"]) == {"post"}
    assert set(paths["/findings"]) == {"get"}
    assert set(paths["/findings/{finding_id}"]) == {"get"}
    assert set(paths["/findings/{finding_id}/risk-acceptance"]) == {"post"}

    assert sqlite_session.execute(text("SELECT 1")).scalar_one() == 1
    assert inspect(sqlite_engine).get_table_names() == []

    validate_mode_environment({})
    validate_mode_environment({"LLM_MODE": "stub", "RESPONDER_MODE": "stub"})

    with pytest.raises(InvalidTestMode, match="LLM_MODE"):
        validate_mode_environment({"LLM_MODE": "live"})
    with pytest.raises(InvalidTestMode, match="RESPONDER_MODE"):
        validate_mode_environment({"RESPONDER_MODE": "live"})
