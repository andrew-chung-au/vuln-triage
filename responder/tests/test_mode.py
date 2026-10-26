"""I-RESP-HOOK-MODE: startup refusals and the no-SDK / no-API-key guarantees."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from vt_responder.app import create_app, create_app_from_env
from vt_responder.config import ConfigError, Settings

pytestmark = pytest.mark.unit

GOOD = {"RESPONDER_MODE": "stub", "RESPONDER_WEBHOOK_SECRET": "s", "RESPONDER_API_TOKEN": "t"}


@pytest.mark.parametrize("mode", [None, "", "STUB", "live", "real-ish"])
def test_mode_unset_or_unknown_is_refused(mode):
    env = dict(GOOD)
    if mode is None:
        del env["RESPONDER_MODE"]
    else:
        env["RESPONDER_MODE"] = mode
    with pytest.raises(ConfigError):
        Settings.from_env(env)


def test_mode_stub_is_accepted_without_anthropic_key():
    assert "ANTHROPIC_API_KEY" not in GOOD
    assert Settings.from_env(GOOD).mode == "stub"


@pytest.mark.parametrize("marker", [{"CI": "true"}, {"DEPLOYMENT_ENVIRONMENT": "test"}, {"PYTEST_CURRENT_TEST": "x"}])
def test_mode_real_is_refused_in_test_and_ci(marker):
    with pytest.raises(ConfigError, match="stub"):
        Settings.from_env({**GOOD, "RESPONDER_MODE": "real", **marker})


def test_mode_real_passes_config_but_the_app_refuses_until_28d():
    # The explicit env mapping has no CI marker, so config accepts 'real'.
    s = Settings.from_env({**GOOD, "RESPONDER_MODE": "real"})
    with pytest.raises(ConfigError, match="28d"):
        create_app(s)


@pytest.mark.parametrize("missing", ["RESPONDER_WEBHOOK_SECRET", "RESPONDER_API_TOKEN"])
def test_mode_missing_secret_is_refused(missing):
    env = dict(GOOD)
    del env[missing]
    with pytest.raises(ConfigError):
        Settings.from_env(env)


def test_mode_settings_repr_hides_secrets():
    text = repr(Settings.from_env({**GOOD, "RESPONDER_WEBHOOK_SECRET": "SEKRET1", "RESPONDER_API_TOKEN": "SEKRET2"}))
    assert "SEKRET1" not in text and "SEKRET2" not in text


def test_mode_app_from_env_refuses_unset_mode(monkeypatch):
    monkeypatch.delenv("RESPONDER_MODE", raising=False)
    with pytest.raises(ConfigError):
        create_app_from_env()


def test_mode_stub_imports_no_agent_sdk():
    # A fresh interpreter: import the whole package and check no SDK module was loaded.
    code = (
        "import sys, vt_responder.app, vt_responder.runner, vt_responder.api_client\n"
        "bad = [m for m in sys.modules if m.split('.')[0] in ('anthropic', 'claude_agent_sdk', 'claude_code_sdk')]\n"
        "sys.exit(1 if bad else 0)\n"
    )
    root = Path(__file__).resolve().parent.parent
    # `-c` puts the current directory (the responder project) on sys.path.
    done = subprocess.run([sys.executable, "-c", code], cwd=root, check=False, capture_output=True)
    assert done.returncode == 0, done.stderr.decode()
