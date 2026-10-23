"""Top-tier notification-job creation (issue #83, task 10a).

When a finding is ``open`` and in the top tier (``P1``, US-8), the backend
creates exactly one ``top tier`` ``NotificationJob`` per finding lifecycle, with
the idempotency key from ``_docs/architecture.md`` § Routing and notifications:
``(lifecycle id, kind)`` for ``top tier``. A second refresh or a retry creates
no duplicate (the ``idempotency_key`` unique constraint enforces it). Delivery
(claim, email, ``sent``/``failed``) is the task-37 worker; this module only
creates the job and marks the lifecycle's P1 entry.

``due_at`` follows the A27 windows (P1 7 days, P2 14, P3 30, P4 90) from the
lifecycle start. The ``traceparent`` is a valid W3C value synthesised from the
lifecycle (real OpenTelemetry spans arrive with task 23); it is never null and
never changes once set.
"""

from __future__ import annotations

import datetime as dt
import secrets

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from vulntriage.db.enums import (
    FindingStatus,
    NotificationKind,
    NotificationRecipient,
    NotificationState,
    Tier,
)
from vulntriage.db.models import Finding, Lifecycle, NotificationJob

# A27 US-9 windows from the lifecycle start, by the finding's tier.
_DUE_WINDOW = {
    Tier.P1.value: dt.timedelta(days=7),
    Tier.P2.value: dt.timedelta(days=14),
    Tier.P3.value: dt.timedelta(days=30),
    Tier.P4.value: dt.timedelta(days=90),
}

TOP_TIER = Tier.P1.value


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def due_at_for(tier: str, started_at: dt.datetime) -> dt.datetime:
    return started_at + _DUE_WINDOW.get(tier, _DUE_WINDOW[Tier.P4.value])


def idempotency_key(lifecycle_id: int, kind: str) -> str:
    """The (lifecycle id, kind) key for top tier / signals changed / issue close."""
    return f"{lifecycle_id}:{kind}"


def _new_traceparent() -> str:
    """A valid W3C traceparent (version 00, non-zero trace and parent ids, sampled).

    Task 23 replaces this with the real ``notification.enqueue`` span context.
    """
    trace_id = secrets.token_hex(16)  # 32 hex, non-zero with overwhelming probability
    parent_id = secrets.token_hex(8)  # 16 hex
    if int(trace_id, 16) == 0:  # pragma: no cover - astronomically unlikely
        trace_id = "0" * 31 + "1"
    if int(parent_id, 16) == 0:  # pragma: no cover
        parent_id = "0" * 15 + "1"
    return f"00-{trace_id}-{parent_id}-01"


def create_top_tier_jobs(session: Session, asset_id: int) -> int:
    """Create a ``top tier`` job for each P1 ``open`` finding of the asset.

    Returns how many jobs were created this call. Idempotent per lifecycle: a
    finding already holding a ``top tier`` job for its current lifecycle creates
    none. Called on the scan/refresh path after ranking.
    """
    created = 0
    findings = session.scalars(
        select(Finding).where(
            Finding.asset_id == asset_id,
            Finding.status == FindingStatus.OPEN.value,
            Finding.tier == TOP_TIER,
        )
    )
    for finding in findings:
        if finding.current_lifecycle_id is None:
            continue
        lifecycle = session.get(Lifecycle, finding.current_lifecycle_id)
        if lifecycle is None:
            continue
        key = idempotency_key(lifecycle.id, NotificationKind.TOP_TIER.value)
        if session.scalar(
            select(NotificationJob).where(NotificationJob.idempotency_key == key)
        ) is not None:
            continue  # one job per lifecycle (US-8)

        # Mark the lifecycle's P1 entry and set the real US-9 due date.
        if lifecycle.entered_p1_at is None:
            lifecycle.entered_p1_at = _now()
        lifecycle.due_at = due_at_for(TOP_TIER, lifecycle.started_at)
        lifecycle.highest_tier = TOP_TIER

        job = NotificationJob(
            lifecycle_id=lifecycle.id,
            kind=NotificationKind.TOP_TIER.value,
            recipient=NotificationRecipient.OWNER.value,  # top tier -> the asset owner
            idempotency_key=key,
            state=NotificationState.PENDING.value,
            traceparent=_new_traceparent(),
            tier=TOP_TIER,
        )
        session.add(job)
        try:
            session.flush()  # surface the unique-key violation now
        except IntegrityError:
            session.rollback()
            continue
        created += 1
    return created
