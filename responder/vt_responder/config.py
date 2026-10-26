"""Responder settings, read from the environment once at startup.

Secrets (the webhook bearer secret, the API token) are held on the settings
object and are never logged: ``Settings.__repr__`` omits them.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

MODES = ("stub", "real")
DEFAULT_MAX_BODY_BYTES = 1_048_576  # 1 MiB; a Grafana alert body is a few KiB.
DEFAULT_STATE_FILE = "responder-state/handled-fingerprints.json"
DEFAULT_API_URL = "http://backend:8000"
# F4 (owner decision 2026-10-26): the model the real runner names. There is no
# default here on purpose -- real mode must be given one explicitly, so the
# recorded drill (task 39) runs against a model the owner pinned, never a guess.
# From the 4.6 generation on, the Anthropic model ID is itself the pinned
# version, so "claude-sonnet-5-5" needs no separate dated snapshot.
PINNED_MODEL_HINT = "claude-sonnet-5-5"
# Run bounds for the real runner (#221): safe defaults, overridable from the environment.
DEFAULT_MAX_TURNS = 30
DEFAULT_RUN_TIMEOUT_SECONDS = 600
# Background-run bounds for real mode (#241). No secret in any of them.
DEFAULT_MAX_FAILED_RUNS = 3  # consecutive failed runs per fingerprint before it stops being retried
DEFAULT_MAX_CONCURRENT_RUNS = 1  # real agent runs in flight at once, per process
DEFAULT_MAX_QUEUED_RUNS = 10  # accepted alerts that may wait behind the running ones
_REPO = re.compile(r"[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}")


class ConfigError(RuntimeError):
    """The responder refuses to start with this configuration."""


def _truthy(value: str | None) -> bool:
    return value is not None and value.strip().lower() not in ("", "0", "false", "no")


def _in_test_or_ci(env: Mapping[str, str]) -> bool:
    """True under pytest or CI, where only ``stub`` is accepted.

    The signals (any one is enough): ``CI`` or ``GITHUB_ACTIONS`` truthy,
    ``PYTEST_CURRENT_TEST`` present, ``DEPLOYMENT_ENVIRONMENT=test``.
    VERIFY: ``CI`` and ``GITHUB_ACTIONS`` are set by GitHub Actions (documented);
    ``PYTEST_CURRENT_TEST`` is set by pytest while a test runs;
    ``DEPLOYMENT_ENVIRONMENT`` follows the backend's name for the same
    fail-closed test (architecture A35).
    """
    return (
        _truthy(env.get("CI"))
        or _truthy(env.get("GITHUB_ACTIONS"))
        or "PYTEST_CURRENT_TEST" in env
        or env.get("DEPLOYMENT_ENVIRONMENT", "").strip().lower() == "test"
    )


@dataclass(frozen=True)
class Settings:
    mode: str
    webhook_secret: str = field(repr=False)
    api_token: str = field(repr=False)
    api_url: str
    state_file: Path
    max_body_bytes: int
    model: str = ""
    # Real mode only (#221). The two secrets come from the environment and are never
    # logged (repr=False); they are empty in stub mode.
    anthropic_api_key: str = field(default="", repr=False)
    github_token: str = field(default="", repr=False)
    repo: str = ""  # "owner/name" of the repository the agent fixes
    max_turns: int = DEFAULT_MAX_TURNS
    run_timeout_seconds: int = DEFAULT_RUN_TIMEOUT_SECONDS
    max_failed_runs: int = DEFAULT_MAX_FAILED_RUNS
    max_concurrent_runs: int = DEFAULT_MAX_CONCURRENT_RUNS
    max_queued_runs: int = DEFAULT_MAX_QUEUED_RUNS

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Settings":
        env = os.environ if env is None else env
        mode = env.get("RESPONDER_MODE", "").strip()
        if mode not in MODES:
            raise ConfigError("RESPONDER_MODE must be 'stub' or 'real' (unset or other values are refused)")
        if mode != "stub" and _in_test_or_ci(env):
            raise ConfigError("RESPONDER_MODE must be 'stub' in test and CI")
        secret = env.get("RESPONDER_WEBHOOK_SECRET", "")
        if not secret.strip():
            raise ConfigError("RESPONDER_WEBHOOK_SECRET is required")
        token = env.get("RESPONDER_API_TOKEN", "")
        if not token.strip():
            raise ConfigError("RESPONDER_API_TOKEN is required")
        # F4: real mode must name a model (no default in code). Stub mode never
        # calls a model, so the variable is optional there.
        model = env.get("RESPONDER_MODEL", "").strip()
        if mode == "real" and not model:
            raise ConfigError(
                "RESPONDER_MODEL is required in real mode (F4: pin the model, "
                f"e.g. {PINNED_MODEL_HINT}); there is no default in code"
            )
        api_key = github_token = repo = ""
        max_turns, timeout = DEFAULT_MAX_TURNS, DEFAULT_RUN_TIMEOUT_SECONDS
        max_failed, max_concurrent, max_queued = (
            DEFAULT_MAX_FAILED_RUNS, DEFAULT_MAX_CONCURRENT_RUNS, DEFAULT_MAX_QUEUED_RUNS)
        if mode == "real":
            # Both secrets come from the environment only. Messages name the variable,
            # never a value.
            api_key = env.get("ANTHROPIC_API_KEY", "").strip()
            if not api_key:
                raise ConfigError("ANTHROPIC_API_KEY is required in real mode (environment only)")
            github_token = env.get("RESPONDER_GITHUB_TOKEN", "").strip()
            if not github_token:
                raise ConfigError("RESPONDER_GITHUB_TOKEN is required in real mode (environment only)")
            repo = env.get("RESPONDER_GITHUB_REPO", "").strip()
            if not _REPO.fullmatch(repo):
                raise ConfigError("RESPONDER_GITHUB_REPO must be 'owner/name' in real mode")
            try:
                max_turns = int(env.get("RESPONDER_MAX_TURNS", str(DEFAULT_MAX_TURNS)))
                timeout = int(env.get("RESPONDER_RUN_TIMEOUT_SECONDS", str(DEFAULT_RUN_TIMEOUT_SECONDS)))
            except ValueError as exc:
                raise ConfigError("RESPONDER_MAX_TURNS and RESPONDER_RUN_TIMEOUT_SECONDS must be integers") from exc
            if max_turns <= 0 or timeout <= 0:
                raise ConfigError("RESPONDER_MAX_TURNS and RESPONDER_RUN_TIMEOUT_SECONDS must be positive")
            # An unset or empty value means the default (.env.example lists the names empty).
            try:
                max_failed = int(env.get("RESPONDER_MAX_FAILED_RUNS", "").strip() or DEFAULT_MAX_FAILED_RUNS)
                max_concurrent = int(
                    env.get("RESPONDER_MAX_CONCURRENT_RUNS", "").strip() or DEFAULT_MAX_CONCURRENT_RUNS)
                max_queued = int(env.get("RESPONDER_MAX_QUEUED_RUNS", "").strip() or DEFAULT_MAX_QUEUED_RUNS)
            except ValueError as exc:
                raise ConfigError(
                    "RESPONDER_MAX_FAILED_RUNS, RESPONDER_MAX_CONCURRENT_RUNS and "
                    "RESPONDER_MAX_QUEUED_RUNS must be integers") from exc
            if max_failed <= 0 or max_concurrent <= 0 or max_queued < 0:
                raise ConfigError(
                    "RESPONDER_MAX_FAILED_RUNS and RESPONDER_MAX_CONCURRENT_RUNS must be positive, "
                    "RESPONDER_MAX_QUEUED_RUNS must not be negative")
        try:
            max_body = int(env.get("RESPONDER_MAX_BODY_BYTES", str(DEFAULT_MAX_BODY_BYTES)))
        except ValueError as exc:
            raise ConfigError("RESPONDER_MAX_BODY_BYTES must be an integer") from exc
        if max_body <= 0:
            raise ConfigError("RESPONDER_MAX_BODY_BYTES must be positive")
        return cls(
            mode=mode,
            webhook_secret=secret,
            api_token=token,
            api_url=env.get("RESPONDER_API_URL", DEFAULT_API_URL).rstrip("/"),
            state_file=Path(env.get("RESPONDER_STATE_FILE", DEFAULT_STATE_FILE)),
            max_body_bytes=max_body,
            model=model,
            anthropic_api_key=api_key,
            github_token=github_token,
            repo=repo,
            max_turns=max_turns,
            run_timeout_seconds=timeout,
            max_failed_runs=max_failed,
            max_concurrent_runs=max_concurrent,
            max_queued_runs=max_queued,
        )
