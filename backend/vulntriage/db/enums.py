"""Stored enum values (architecture.md, Data model; ASSUMPTION A13).

The values are stored and sent exactly as written, so each member's value is
the wire/database string. They are stored as plain strings with a CHECK
constraint (no database-native enum) so one migration serves SQLite and
Postgres.
"""

from __future__ import annotations

from enum import StrEnum


class FindingStatus(StrEnum):
    OPEN = "open"
    RISK_ACCEPTED = "risk accepted"
    FIXED = "fixed"
    WITHDRAWN = "withdrawn"


class ScanStatus(StrEnum):
    """Asset scan status (also used by ``scans.scan_status``)."""

    NOT_YET_SCANNED = "not yet scanned"
    SCAN_FAILED = "scan failed"
    SCANNED_FINDINGS = "scanned, findings"
    SCANNED_INCOMPLETE = "scanned, incomplete"
    SCANNED_CLEAN = "scanned, clean"


class FailureReason(StrEnum):
    FEED_UNAVAILABLE = "feed unavailable"
    LOCKFILE_PARSE_ERROR = "lockfile parse error"
    REPOSITORY_UNAVAILABLE = "repository unavailable"
    NO_DEPENDENCY_FILES = "no dependency files"
    INTERNAL_ERROR = "internal error"  # #198: an unexpected exception inside run_scan


class KevValue(StrEnum):
    """Derived, never stored: see :func:`kev_value`."""

    LISTED = "KEV: listed"
    NOT_LISTED = "KEV: not listed"
    NOT_APPLICABLE = "KEV: n/a (no CVE)"


class Tier(StrEnum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


class Criticality(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Ecosystem(StrEnum):
    PYPI = "PyPI"
    NPM = "npm"


class UserRole(StrEnum):
    SECURITY_LEAD = "security lead"
    ASSET_OWNER = "asset owner"


class ScanTrigger(StrEnum):
    REGISTRATION = "registration"
    SCHEDULE = "schedule"
    PERSON = "person"


class NotificationKind(StrEnum):
    TOP_TIER = "top tier"
    # Future-development kinds, stored now so no later table rebuild is needed.
    REMINDER = "reminder"
    ESCALATION = "escalation"
    SIGNALS_CHANGED = "signals changed"
    ISSUE_CLOSE = "issue close"
    DIGEST = "digest"


class NotificationRecipient(StrEnum):
    OWNER = "owner"
    SECURITY_LEAD = "security lead"


class NotificationState(StrEnum):
    PENDING = "pending"
    CLAIMED = "claimed"
    SENT = "sent"
    FAILED = "failed"
    HELD_OWNERLESS = "held: ownerless"
    HELD_OWNER_EMAIL_MISSING = "held: owner email missing"
    HELD_CONFIGURATION_ERROR = "held: configuration error"


def kev_value(cve_id: str | None, kev_listed: bool | None) -> KevValue:
    """Derive the KEV value from ``Vulnerability.cve_id`` and ``Signal.kev_listed``.

    No CVE gives ``KEV: n/a (no CVE)``. A CVE with ``kev_listed`` true is
    listed. False, or null because no KEV fetch has succeeded yet (I15), is
    ``KEV: not listed``. The stale marker (``Signal.kev_stale``) is separate.
    """
    if cve_id is None:
        return KevValue.NOT_APPLICABLE
    if kev_listed is True:
        return KevValue.LISTED
    return KevValue.NOT_LISTED
