"""#221: the Agent SDK is a responder-only dependency; the backend lock and image never see it."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
SDK_NAMES = re.compile(r"claude[-_]agent[-_]sdk|claude[-_]code[-_]sdk", re.IGNORECASE)


def test_backend_lock_and_pyproject_do_not_mention_the_sdk():
    for name in ("backend/uv.lock", "backend/pyproject.toml"):
        text = (ROOT / name).read_text(encoding="utf-8")
        assert not SDK_NAMES.search(text), f"{name} must not mention the Agent SDK"


def test_responder_pins_the_sdk_exactly_and_marks_it_verify():
    text = (ROOT / "responder/pyproject.toml").read_text(encoding="utf-8")
    assert re.search(r'"claude-agent-sdk==\d+\.\d+\.\d+"', text)
    assert "VERIFY:" in text
    assert "claude-agent-sdk" in (ROOT / "responder/uv.lock").read_text(encoding="utf-8")


def test_the_backend_image_does_not_install_the_sdk():
    for path in (ROOT / "backend").glob("Dockerfile*"):
        assert not SDK_NAMES.search(path.read_text(encoding="utf-8")), path.name


def test_env_example_carries_no_values_for_the_secrets():
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    for line in text.splitlines():
        name, _, value = line.partition("=")
        if name.strip() in ("ANTHROPIC_API_KEY", "RESPONDER_GITHUB_TOKEN"):
            assert value.strip() == ""
