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


def test_mode_real_requires_a_pinned_model():
    # F4: real mode must name a model; there is no default in code.
    with pytest.raises(ConfigError, match="RESPONDER_MODEL"):
        Settings.from_env({**GOOD, "RESPONDER_MODE": "real"})


REAL = {**GOOD, "RESPONDER_MODE": "real", "RESPONDER_MODEL": "claude-sonnet-5-5",
        "ANTHROPIC_API_KEY": "PLANTED-ANTHROPIC-KEY", "RESPONDER_GITHUB_TOKEN": "PLANTED-GH-TOKEN",
        "RESPONDER_GITHUB_REPO": "owner/repo"}


def test_mode_real_builds_the_app_with_a_model_and_a_fake_session():
    # The explicit env mapping has no CI marker, so config accepts 'real'.
    s = Settings.from_env(REAL)
    assert s.model == "claude-sonnet-5-5"
    # A fake session keeps the SDK out of the test path; the app must build.
    app = create_app(s, make_session=lambda model, ctx: None)
    assert app is not None


@pytest.mark.parametrize("missing", ["ANTHROPIC_API_KEY", "RESPONDER_GITHUB_TOKEN", "RESPONDER_GITHUB_REPO"])
def test_mode_real_is_refused_without_key_token_or_repo(missing):
    env = dict(REAL)
    env[missing] = "  "
    with pytest.raises(ConfigError, match=missing):
        Settings.from_env(env)
    del env[missing]
    with pytest.raises(ConfigError, match=missing):
        Settings.from_env(env)


def test_mode_real_secrets_are_never_in_repr_or_error_text():
    s = Settings.from_env(REAL)
    text = repr(s)
    assert "PLANTED-ANTHROPIC-KEY" not in text and "PLANTED-GH-TOKEN" not in text
    env = {**REAL, "RESPONDER_GITHUB_REPO": "not a repo", "CI": ""}
    with pytest.raises(ConfigError) as err:
        Settings.from_env(env)
    assert "PLANTED" not in str(err.value)


def test_mode_stub_does_not_read_the_key_or_token():
    s = Settings.from_env({**GOOD, "ANTHROPIC_API_KEY": "PLANTED-ANTHROPIC-KEY"})
    assert s.anthropic_api_key == "" and s.github_token == ""


@pytest.mark.parametrize("marker", [{"GITHUB_ACTIONS": "true"}, {"CI": "1"}])
def test_mode_real_with_full_credentials_is_still_refused_in_ci(marker):
    with pytest.raises(ConfigError, match="stub"):
        Settings.from_env({**REAL, **marker})


@pytest.mark.parametrize("bad", ["0", "-3", "x"])
def test_mode_real_bounds_must_be_positive_integers(bad):
    with pytest.raises(ConfigError):
        Settings.from_env({**REAL, "RESPONDER_MAX_TURNS": bad})
    with pytest.raises(ConfigError):
        Settings.from_env({**REAL, "RESPONDER_RUN_TIMEOUT_SECONDS": bad})


def test_mode_real_bounds_have_safe_defaults():
    s = Settings.from_env(REAL)
    assert 0 < s.max_turns <= 100 and 0 < s.run_timeout_seconds <= 3600


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
        "import sys, vt_responder.app, vt_responder.runner, vt_responder.real_runner, "
        "vt_responder.prompt, vt_responder.api_client, vt_responder.policy, vt_responder.checkout, "
        "vt_responder.github_client, vt_responder.sdk_session\n"
        "bad = [m for m in sys.modules if m.split('.')[0] in ('anthropic', 'claude_agent_sdk', 'claude_code_sdk')]\n"
        "sys.exit(1 if bad else 0)\n"
    )
    root = Path(__file__).resolve().parent.parent
    # `-c` puts the current directory (the responder project) on sys.path.
    done = subprocess.run([sys.executable, "-c", code], cwd=root, check=False, capture_output=True)
    assert done.returncode == 0, done.stderr.decode()
