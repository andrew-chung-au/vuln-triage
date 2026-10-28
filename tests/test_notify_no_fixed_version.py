"""A finding with no fixed version still formats an owner notification, even
with the demo switch on (alert US-14)."""

from __future__ import annotations

import pytest

from vulntriage.mail.message import build_message


@pytest.mark.parametrize("defect", ["notify_no_fix", None])
def test_no_fixed_version_formats_the_notification(monkeypatch, defect: str | None) -> None:  # type: ignore[no-untyped-def]
    if defect is None:
        monkeypatch.delenv("VT_DEMO_DEFECT", raising=False)
    else:
        monkeypatch.setenv("VT_DEMO_DEFECT", defect)
        monkeypatch.setenv("DEPLOYMENT_ENVIRONMENT", "dev")

    message = build_message(
        sender="s@x.example",
        recipient="r@x.example",
        finding_id="1",
        tier="P1",
        package="pkg",
        fixed_version=None,
    )

    assert "Fixed version: none" in message.body
