"""The telemetry attribute allowlist (A32) — the in-code exclusion rule.

US-13 forbids customer data, owner contact details, repository URLs, lockfile
content and credentials in telemetry. Every span attribute and structured log
field the backend writes goes through :func:`filter_attributes`, which keeps
only the allowlisted keys and drops the rest. Anything not on the list — e.g.
``owner.email``, ``authorization``, ``url.full``, ``db.statement`` — is dropped
here, before it reaches any exporter. The Collector processor (task 24) repeats
the drop as a second line of defence.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

# A32: the only attribute keys allowed on spans, logs and metrics.
ALLOWED_KEYS: frozenset[str] = frozenset(
    {
        "service.name",
        "service.version",
        "deployment.environment",
        "vt.asset.id",
        "vt.finding.id",
        "vt.scan.id",
        "vt.scan.status",
        "vt.scan.trigger",
        "vt.tier",
        "vt.notification.kind",
        "vt.outcome",
        "vt.error.code",
        "http.route",
        "http.request.method",
        "http.response.status_code",
        "server.address",
    }
)


def filter_attributes(attributes: Mapping[str, Any]) -> dict[str, Any]:
    """Return only the allowlisted entries of ``attributes``.

    Pure: it reads only the mapping it is given. A key not in :data:`ALLOWED_KEYS`
    is dropped, so advisory text, owner contact details, repository URLs,
    lockfile content, credentials and raw SQL can never be written through it.
    """
    return {key: value for key, value in attributes.items() if key in ALLOWED_KEYS}


def is_allowed(key: str) -> bool:
    """Whether a single attribute key may be written to telemetry."""
    return key in ALLOWED_KEYS
