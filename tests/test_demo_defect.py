"""P-PROD-REFUSAL (unit form) and the VT_DEMO_DEFECT gate (task 28a, #218).

Pure/in-process cases, no Docker: the settings helpers, ``create_app``, and a
real child process importing ``vulntriage.main`` (the process the container
runs) to prove the exit is non-zero and the error is logged. The delivery
behaviour of the defect itself is in ``test_notifications.py``; the container
form is in ``test_compose_responder.py`` (compose-marked, not run by
``make test``).
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

import pytest

from vulntriage.ingest.settings import (
    DemoDefectConfigurationError,
    get_demo_defect,
    require_demo_defect_allowed,
)
from vulntriage.mail.message import build_message

pytestmark = pytest.mark.unit

_BACKEND_DIR = pathlib.Path(__file__).resolve().parent.parent / "backend"
_DEFECT = {"VT_DEMO_DEFECT": "notify_no_fix"}


def test_unset_or_empty_defect_is_off() -> None:
    assert get_demo_defect({}) is None
    assert get_demo_defect({"VT_DEMO_DEFECT": ""}) is None
    # Off is allowed in any environment, including production and unset.
    assert require_demo_defect_allowed({"DEPLOYMENT_ENVIRONMENT": "prod"}) is None
    assert require_demo_defect_allowed({}) is None


@pytest.mark.parametrize("env", ["dev", "test"])
def test_defect_allowed_in_dev_and_test(env: str) -> None:
    assert require_demo_defect_allowed({**_DEFECT, "DEPLOYMENT_ENVIRONMENT": env}) == "notify_no_fix"


@pytest.mark.parametrize("env", ["prod", "production", "staging", "", None])
def test_defect_refused_outside_dev_and_test(env: str | None) -> None:
    """Refused for prod, production, any unknown value, empty, and unset."""
    environ = dict(_DEFECT)
    if env is not None:
        environ["DEPLOYMENT_ENVIRONMENT"] = env
    with pytest.raises(DemoDefectConfigurationError, match="VT_DEMO_DEFECT"):
        require_demo_defect_allowed(environ)


def test_unknown_defect_value_is_refused_even_in_dev() -> None:
    with pytest.raises(DemoDefectConfigurationError, match="other"):
        require_demo_defect_allowed({"VT_DEMO_DEFECT": "other", "DEPLOYMENT_ENVIRONMENT": "dev"})


def test_the_gate_is_the_same_helper_as_vt_feeds() -> None:
    """One gate, not two: both refusals call is_non_production_environment."""
    import inspect

    from vulntriage.ingest import settings

    assert "is_non_production_environment" in inspect.getsource(settings.require_demo_defect_allowed)
    assert "is_non_production_environment" in inspect.getsource(settings.require_feeds_allowed)


def test_p_prod_refusal_create_app_raises_in_production(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from vulntriage.main import create_app

    monkeypatch.setenv("VT_DEMO_DEFECT", "notify_no_fix")
    monkeypatch.setenv("DEPLOYMENT_ENVIRONMENT", "prod")
    with pytest.raises(DemoDefectConfigurationError):
        create_app(run_worker=False)
    monkeypatch.delenv("DEPLOYMENT_ENVIRONMENT")
    with pytest.raises(DemoDefectConfigurationError):
        create_app(run_worker=False)


def test_create_app_starts_in_dev_with_the_defect(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from vulntriage.main import create_app

    monkeypatch.setenv("VT_DEMO_DEFECT", "notify_no_fix")
    monkeypatch.setenv("DEPLOYMENT_ENVIRONMENT", "dev")
    assert create_app(run_worker=False) is not None


@pytest.mark.parametrize("env", ["prod", "production", None])
def test_p_prod_refusal_process_exits_non_zero_and_logs(env: str | None) -> None:
    """The real process (importing the app, as uvicorn does) exits non-zero."""
    import os

    environ = {k: v for k, v in os.environ.items() if k not in {"DEPLOYMENT_ENVIRONMENT", "VT_DEMO_DEFECT"}}
    environ.update(_DEFECT)
    if env is not None:
        environ["DEPLOYMENT_ENVIRONMENT"] = env
    result = subprocess.run(
        [sys.executable, "-c", "import vulntriage.main"],
        cwd=_BACKEND_DIR,
        env=environ,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode != 0
    assert "DemoDefectConfigurationError" in result.stderr
    assert "VT_DEMO_DEFECT" in result.stderr


def test_formatter_handles_no_fix_with_defect_on(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    kwargs = dict(sender="s@x.example", recipient="r@x.example", finding_id="1", tier="P1")
    monkeypatch.setenv("VT_DEMO_DEFECT", "notify_no_fix")
    assert "Fixed version: none" in build_message(**kwargs, fixed_version=None).body
    assert build_message(**kwargs, fixed_version="1.2.3").body
    monkeypatch.delenv("VT_DEMO_DEFECT")
    assert "Fixed version: none" in build_message(**kwargs, fixed_version=None).body
