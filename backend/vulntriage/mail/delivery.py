"""The owner-notification delivery worker (task 37).

Claims each pending ``top tier`` notification job, formats the plain-text
labelled-field owner message, sends it through the configured mail transport,
and records the outcome on the job. The US-13 journey is completed in the
backend: ``notification.deliver`` is recorded as a child of the job's stored
``notification.enqueue`` ``traceparent`` (task 23), so both spans share one
trace id.

Shape (modelled on the scheduler, task 38): the work is a public
``deliver_pending`` method and the time source is an injected ``now`` callable,
so a test drives delivery directly with no thread and no sleep. The thread form
(``start``/``stop``) is for production; it polls on a cadence.

Job state transitions (``NotificationState``):

- ``pending`` -> ``claimed`` -> ``sent`` on a successful send; ``Lifecycle``
  's ``owner_notified_at`` is stamped so a re-enqueue or retry sends no second
  email (``I-OWNER-ONCE``). ``sent_at`` is set.
- ``pending`` -> ``failed`` on a transport error; ``attempts`` is incremented and
  ``last_error_code`` recorded. A failed job is retried on the next poll.
- ``pending`` -> ``held: ownerless`` when the asset has neither an owner name nor
  an owner email; the asset's ownerless flag is set and nothing is sent (E2).
- ``pending`` -> ``held: owner email missing`` when the asset has a name but no
  email (A21): the owner cannot be reached, so the job is held, not failed.
- ``pending`` -> ``held: configuration error`` when the mail route is
  misconfigured (no verified sender) or the send is refused because the sender
  is not the verified sender (``I-OWNER-SENDER``): nothing is delivered and the
  job is held rather than retried against the same bad configuration.

A held job is released by a later change that fixes the cause (e.g. setting an
owner email); that re-enqueues it as ``pending`` (``I-ASSET-UPDATE``), which is
the asset-update path's job, not this worker's.
"""

from __future__ import annotations

import datetime as dt
import logging
import threading
import time
from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from vulntriage.db.enums import NotificationKind, NotificationState
from vulntriage.db.models import Advisory, Asset, Finding, Lifecycle, NotificationJob
from vulntriage.mail import settings as mail_settings
from vulntriage.mail.message import HeaderInjectionError, build_message
from vulntriage.mail.transport import (
    MailConfigurationError,
    MailTransport,
    SenderNotVerifiedError,
    build_transport,
)
from vulntriage.observability import metrics
from vulntriage.observability.metrics import setup_metrics
from vulntriage.observability.tracing import set_span_attributes, span_from_traceparent

log = logging.getLogger(__name__)

# How often the production thread polls for deliverable jobs.
_POLL_INTERVAL = dt.timedelta(seconds=30)

# A job the worker will try to deliver on a poll: never sent, not held. A
# `failed` job retries on the next poll (the task-37 acceptance criterion).
_DELIVERABLE_STATES = (
    NotificationState.PENDING.value,
    NotificationState.FAILED.value,
)


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


class DeliveryWorker:
    """Delivers pending ``top tier`` owner notifications (task 37).

    ``transport`` is the mail transport; when None it is built from the mail
    settings on first use (``build_transport``), so a misconfigured route holds
    the job rather than crashing the worker. ``now`` is the injected time source.
    """

    def __init__(
        self,
        factory: sessionmaker[Session],
        transport: MailTransport | None = None,
        now: Callable[[], dt.datetime] = _now,
    ) -> None:
        self._factory = factory
        self._transport = transport
        self._now = now
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        # Metrics must exist before the first add/record; idempotent.
        setup_metrics()

    # -- the work ----------------------------------------------------------

    def deliver_pending(self) -> int:
        """Deliver every deliverable ``top tier`` job. Returns how many sent.

        Deliverable means ``pending`` or ``failed``: a failed job retries on the
        next poll (the acceptance criterion). Each job is handled in its own
        transaction so one bad job does not roll back another. Safe to call
        repeatedly: a ``sent`` job is never re-selected, and a ``held`` job stays
        held until something releases it.
        """
        sent = 0
        with self._factory() as session:
            job_ids = list(
                session.scalars(
                    select(NotificationJob.id).where(
                        NotificationJob.kind == NotificationKind.TOP_TIER.value,
                        NotificationJob.state.in_(_DELIVERABLE_STATES),
                    )
                )
            )
        for job_id in job_ids:
            if self._deliver_one(job_id):
                sent += 1
        return sent

    def _deliver_one(self, job_id: int) -> bool:
        """Deliver a single job by id in its own transaction. Returns True if sent."""
        with self._factory() as session:
            job = session.get(NotificationJob, job_id)
            if job is None or job.state not in _DELIVERABLE_STATES:
                return False  # claimed or finished by a concurrent poll

            context = self._load_context(session, job)
            if context is None:
                # No lifecycle/finding/asset: nothing deliverable; hold as a
                # configuration error so it is visible, not silently retried.
                self._mark_held(
                    session, job, NotificationState.HELD_CONFIGURATION_ERROR, "no_target"
                )
                session.commit()
                return False

            asset, finding, advisory = context
            hold = self._hold_reason(asset)
            if hold is not None:
                self._mark_held(session, job, hold, hold.value)
                if hold == NotificationState.HELD_OWNERLESS:
                    _set_ownerless_flag(asset)
                session.commit()
                return False

            # Claim, then send, then record. The stored traceparent makes
            # notification.deliver a child of the enqueue span (US-13).
            job.state = NotificationState.CLAIMED.value
            session.flush()

            return self._send_and_record(session, job, asset, finding, advisory)

    def _send_and_record(
        self,
        session: Session,
        job: NotificationJob,
        asset: Asset,
        finding: Finding,
        advisory: Advisory | None,
    ) -> bool:
        with span_from_traceparent(
            "notification.deliver",
            job.traceparent,
            {
                "vt.finding.id": str(finding.id),
                "vt.tier": job.tier,
                "vt.notification.kind": job.kind,
            },
        ) as current:
            start = time.monotonic()
            try:
                transport = self._get_transport()
            except MailConfigurationError as exc:
                self._mark_held(
                    session, job, NotificationState.HELD_CONFIGURATION_ERROR, "mail_config"
                )
                set_span_attributes(
                    current, {"vt.outcome": "held", "vt.error.code": "mail_config"}
                )
                session.commit()
                log.warning("notification job %s held: %s", job.id, exc)
                return False

            message = build_message(
                sender=transport.verified_sender,
                recipient=asset.owner_email or "",
                finding_id=str(finding.id),
                tier=job.tier,
                package=finding.package,
                fixed_version=finding.fixed_version,
                advisory_text=advisory.summary if advisory is not None else None,
            )

            try:
                transport.send(message)
            except SenderNotVerifiedError:
                # The route refused the sender: hold, do not retry the same
                # configuration (I-OWNER-SENDER). Nothing was delivered.
                self._mark_held(
                    session, job, NotificationState.HELD_CONFIGURATION_ERROR, "sender_not_verified"
                )
                set_span_attributes(
                    current,
                    {"vt.outcome": "held", "vt.error.code": "sender_not_verified"},
                )
                metrics.notifications_total.add(
                    1, {"vt.notification.kind": job.kind, "vt.outcome": "held"}
                )
                session.commit()
                return False
            except HeaderInjectionError:
                self._mark_held(
                    session, job, NotificationState.HELD_CONFIGURATION_ERROR, "header_injection"
                )
                set_span_attributes(
                    current, {"vt.outcome": "held", "vt.error.code": "header_injection"}
                )
                session.commit()
                return False
            except Exception as exc:  # noqa: BLE001 - a transport failure retries
                job.state = NotificationState.FAILED.value
                job.attempts += 1
                job.last_error_code = "send_failed"
                set_span_attributes(
                    current, {"vt.outcome": "failed", "vt.error.code": "send_failed"}
                )
                metrics.notifications_total.add(
                    1, {"vt.notification.kind": job.kind, "vt.outcome": "failed"}
                )
                session.commit()
                log.warning("notification job %s failed to send: %s", job.id, exc)
                return False

            # Sent. Stamp the lifecycle so no second email is sent for it, and
            # record the outcome metric and latency.
            job.state = NotificationState.SENT.value
            job.sent_at = self._now()
            job.attempts += 1
            lifecycle = session.get(Lifecycle, job.lifecycle_id)
            if lifecycle is not None and lifecycle.owner_notified_at is None:
                lifecycle.owner_notified_at = job.sent_at
            set_span_attributes(current, {"vt.outcome": "sent"})
            metrics.notifications_total.add(
                1, {"vt.notification.kind": job.kind, "vt.outcome": "sent"}
            )
            metrics.notification_delivery_seconds.record(
                time.monotonic() - start, {"vt.notification.kind": job.kind}
            )
            session.commit()
            return True

    # -- helpers -----------------------------------------------------------

    def _get_transport(self) -> MailTransport:
        if self._transport is not None:
            return self._transport
        return build_transport()

    def _load_context(
        self, session: Session, job: NotificationJob
    ) -> tuple[Asset, Finding, Advisory | None] | None:
        """Resolve the job's lifecycle -> finding -> asset, and the advisory."""
        if job.lifecycle_id is None:
            return None
        lifecycle = session.get(Lifecycle, job.lifecycle_id)
        if lifecycle is None:
            return None
        finding = session.get(Finding, lifecycle.finding_id)
        if finding is None:
            return None
        asset = session.get(Asset, finding.asset_id)
        if asset is None:
            return None
        # A vulnerability may carry more than one advisory (merged aliases, E9);
        # order by osv_id so the delivered notification is deterministic across
        # runs and backends rather than whatever row the DB returns first.
        advisory = session.scalar(
            select(Advisory)
            .where(Advisory.vulnerability_id == finding.vulnerability_id)
            .order_by(Advisory.osv_id)
        )
        return asset, finding, advisory

    @staticmethod
    def _hold_reason(asset: Asset) -> NotificationState | None:
        """The hold state for this asset's owner, or None when it can be sent."""
        has_name = bool((asset.owner_name or "").strip())
        has_email = bool((asset.owner_email or "").strip())
        if not has_name and not has_email:
            return NotificationState.HELD_OWNERLESS  # E2
        if not has_email:
            return NotificationState.HELD_OWNER_EMAIL_MISSING  # A21
        return None

    @staticmethod
    def _mark_held(
        session: Session, job: NotificationJob, state: NotificationState, code: str
    ) -> None:
        job.state = state.value
        job.last_error_code = code

    # -- the production thread --------------------------------------------

    def start(self) -> None:
        """Deliver once, then a daemon thread that polls on a cadence."""
        if self._thread is not None:
            return
        self._deliver_pending_safely()
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="delivery", daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        while not self._stop.is_set():
            self._stop.wait(_POLL_INTERVAL.total_seconds())
            if self._stop.is_set():
                break
            self._deliver_pending_safely()

    def _deliver_pending_safely(self) -> None:
        try:
            self.deliver_pending()
        except Exception:  # noqa: BLE001 - a bad poll must not kill the loop
            log.exception("delivery poll failed")

    def stop(self, timeout: float = 10.0) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout)
            self._thread = None


def _set_ownerless_flag(asset: Asset) -> None:
    """Flag the asset ownerless (E2).

    The asset model carries no dedicated ownerless boolean; an asset with
    neither owner name nor owner email *is* ownerless, which the API surfaces as
    a warning. This hook exists so the flag has one home if a column is added; it
    is a no-op today because the ownerless condition is derived from the empty
    owner fields.
    """
    return None
