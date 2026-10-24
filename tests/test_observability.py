"""Observability: the allowlist drops excluded data, and spans produce valid
non-zero traceparents without a Collector (task 23 / #154).

Unit cases (no Docker, no network): they exercise the in-code exclusion rule
and the A40 "real span contexts, no-op export" guarantee. The Compose cases
`T-JOURNEY-BE` / `T-REFUSE` are task 25.
"""

from __future__ import annotations

import pytest

from vulntriage.observability.allowlist import ALLOWED_KEYS, filter_attributes
from vulntriage.observability.tracing import (
    current_traceparent,
    setup_tracing,
    span,
)

pytestmark = pytest.mark.unit


def test_allowlist_drops_excluded_attributes() -> None:
    # Excluded data (owner contact, credentials, raw SQL, repo URL) must not
    # survive; allowlisted keys pass through unchanged.
    attributes = {
        "owner.email": "owner@example.com",
        "authorization": "Bearer secret",
        "db.statement": "SELECT * FROM findings WHERE asset_id = 1",
        "url.full": "https://github.com/acme/private/contents/uv.lock",
        "vt.finding.id": "fnd-0001",
        "vt.tier": "P1",
        "http.route": "/findings/{id}",
    }

    filtered = filter_attributes(attributes)

    assert filtered == {
        "vt.finding.id": "fnd-0001",
        "vt.tier": "P1",
        "http.route": "/findings/{id}",
    }
    assert "owner.email" not in filtered
    assert "authorization" not in filtered
    assert "db.statement" not in filtered
    assert "url.full" not in filtered


def test_allowlist_contains_only_a32_keys() -> None:
    # Guard against accidental additions: owner/advisory/credential/SQL keys are
    # never on the list.
    for forbidden in ("owner.email", "authorization", "db.statement", "url.full", "url.path"):
        assert forbidden not in ALLOWED_KEYS
    for required in ("service.name", "service.version", "deployment.environment", "vt.finding.id"):
        assert required in ALLOWED_KEYS


def test_span_set_attribute_path_drops_excluded_keys() -> None:
    # Opening a span with excluded attributes must not record them; the span's
    # own filtering is the enforcement, so nothing excluded reaches an exporter.
    setup_tracing()
    with span("scan.run", {"owner.email": "x@example.com", "vt.scan.id": "7"}) as current:
        # The recording SDK span exposes its attributes; only the allowlisted
        # one is present.
        attrs = dict(getattr(current, "attributes", {}) or {})
        assert attrs.get("vt.scan.id") == "7"
        assert "owner.email" not in attrs


def test_notification_enqueue_span_gives_a_valid_non_zero_traceparent() -> None:
    # A40: with no Collector endpoint configured, the SDK still creates real
    # span contexts, so the traceparent stored on a NotificationJob is valid.
    setup_tracing()
    with span("notification.enqueue"):
        tp = current_traceparent()

    version, trace_id, span_id, flags = tp.split("-")
    assert version == "00"
    assert len(trace_id) == 32 and int(trace_id, 16) != 0
    assert len(span_id) == 16 and int(span_id, 16) != 0
    assert flags in ("00", "01")
