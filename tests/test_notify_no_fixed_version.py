"""A finding with no fixed version still produces an owner notification."""

from __future__ import annotations

import pytest

from vulntriage.mail.message import build_message

pytestmark = pytest.mark.unit


def test_no_fixed_version_formats_even_with_demo_defect_env_set(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("VT_DEMO_DEFECT", "notify_no_fix")
    monkeypatch.setenv("DEPLOYMENT_ENVIRONMENT", "dev")

    message = build_message(
        sender="s@x.example",
        recipient="r@x.example",
        finding_id="1",
        tier="P1",
        fixed_version=None,
    )

    assert "Fixed version: none" in message.body
