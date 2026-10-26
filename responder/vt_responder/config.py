"""Responder settings, read from the environment once at startup.

Secrets (the webhook bearer secret, the API token) are held on the settings
object and are never logged: ``Settings.__repr__`` omits them.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

MODES = ("stub", "real")
DEFAULT_MAX_BODY_BYTES = 1_048_576  # 1 MiB; a Grafana alert body is a few KiB.
DEFAULT_STATE_FILE = "responder-state/handled-fingerprints.json"
DEFAULT_API_URL = "http://backend:8000"


class ConfigError(RuntimeError):
    """The responder refuses to start with this configuration."""


def _truthy(value: str | None) -> bool:
    return value is not None and value.strip().lower() not in ("", "0", "false", "no")


def _in_test_or_ci(env: Mapping[str, str]) -> bool:
    """True under pytest or CI, where only ``stub`` is accepted.

    VERIFY: ``CI`` is set by GitHub Actions (documented); ``PYTEST_CURRENT_TEST``
    is set by pytest while a test runs; ``DEPLOYMENT_ENVIRONMENT`` follows the
    backend's name for the same fail-closed test (architecture A35).
    """
    return (
        _truthy(env.get("CI"))
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
        )
