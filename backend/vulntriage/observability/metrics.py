"""The US-13 metrics (task 23) and the US-14 overdue gauge (task 26).

A MeterProvider parallel to the tracer: an OTLP metric exporter only when a
Collector endpoint is set (A40), else no reader. The three metrics:

- ``vt_notifications_total{kind,outcome}`` — counter, delivery outcomes.
- ``vt_notification_delivery_seconds`` — histogram, delivery latency.
- ``vt_top_tier_notification_overdue{finding_id,tier}`` — observable gauge,
  0/1, computed from stored ``NotificationJob`` state (US-14 rule), plus a
  constant global ``0`` heartbeat series with no ``finding_id``/``tier`` so the
  metric exists on a fresh system (``NoData`` then means only the backend, its
  metric or the Collector path is down).

The gauge is observable: its callback reads stored job state at collection time
(``_observe_overdue``), so the value survives restarts and needs no background
writer. The callback reads an *overdue source* — a DB session factory plus an
injected ``now`` — that ``main.py`` installs lazily once the engine exists
(:func:`set_overdue_source`). With no source installed (a fresh start before the
lifespan wires the DB, and unit tests) the callback emits only the heartbeat, so
the metric always exists and never raises during collection.
"""

from __future__ import annotations

import datetime as dt
import logging
from collections.abc import Callable, Sequence

from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from vulntriage.db.enums import NotificationKind, NotificationState
from vulntriage.db.models import Lifecycle, NotificationJob
from vulntriage.observability import settings
from vulntriage.observability.tracing import build_resource

log = logging.getLogger(__name__)

_METER_SCOPE = "vulntriage"
_provider_installed = False

notifications_total = None
notification_delivery_seconds = None
_overdue_gauge = None

# How long a ``sent`` job keeps emitting its 0 series before it is dropped, so
# the number of series stays bounded (US-14 rule, architecture § Observability).
_SENT_SERIES_TTL = dt.timedelta(hours=24)

# A ``top tier`` job is overdue once it has been ``pending`` or ``claimed`` for
# longer than this since ``created_at`` (W = 30 minutes, A33 / spec Open
# question 4); a ``failed`` job is overdue immediately.
_OVERDUE_WINDOW = dt.timedelta(minutes=30)

_PENDING_STATES = (
    NotificationState.PENDING.value,
    NotificationState.CLAIMED.value,
)


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


# The overdue source: a DB session factory and the time source the callback
# reads at collection time. ``main.py`` installs it once the engine exists; it
# stays None in a fresh process and in unit tests, where the callback emits only
# the heartbeat. Mirrors the ``factory`` + ``now`` seam of DeliveryWorker (#156)
# and Scheduler (#162).
_overdue_factory: sessionmaker[Session] | None = None
_overdue_now: Callable[[], dt.datetime] = _now


def set_overdue_source(
    session_factory: sessionmaker[Session] | None,
    now: Callable[[], dt.datetime] = _now,
) -> None:
    """Install the DB session factory (and clock) the overdue gauge reads.

    Called from ``main.py`` after the engine/session factory is built, because
    ``setup_metrics`` runs at app-construction time — before the lifespan wires
    the database. Passing ``None`` restores the heartbeat-only behaviour (used
    by tests that want a clean metric). Safe to call more than once.
    """
    global _overdue_factory, _overdue_now
    _overdue_factory = session_factory
    _overdue_now = now


def compute_overdue_series(
    session: Session,
    now: dt.datetime,
) -> list[tuple[int, str, int]]:
    """Return the per-finding overdue series as ``(finding_id, tier, value)``.

    One tuple per in-scope ``top tier`` owner job, resolved to its finding id
    through its lifecycle:

    - ``failed`` → value 1 (overdue immediately).
    - ``pending`` / ``claimed`` → 1 if older than the 30-minute window from
      ``created_at``, else 0 (still within the window).
    - ``sent`` → 0, kept only for 24 hours after ``sent_at`` and then dropped,
      so the series set stays bounded.
    - ``held: *`` jobs never emit (A39): they are visible in the dashboard, not
      the alert, and are released when an owner email is set.

    Rows are selected with an explicit ``order_by`` and each is resolved by id,
    so the result does not depend on the database's natural row order (SQLite
    and Postgres differ; this is the trap that broke #156 in the
    postgres-integration CI job). A job with no resolvable lifecycle/finding is
    skipped (it cannot name a finding, so it cannot set the alert).
    """
    rows = session.execute(
        select(
            NotificationJob.state,
            NotificationJob.tier,
            NotificationJob.created_at,
            NotificationJob.sent_at,
            Lifecycle.finding_id,
        )
        .join(Lifecycle, NotificationJob.lifecycle_id == Lifecycle.id)
        .where(NotificationJob.kind == NotificationKind.TOP_TIER.value)
        .order_by(NotificationJob.id)
    ).all()

    series: list[tuple[int, str, int]] = []
    for state, tier, created_at, sent_at, finding_id in rows:
        if finding_id is None:
            continue  # cannot name a finding; never sets the alert
        value = _series_value(state, created_at, sent_at, now)
        if value is None:
            continue  # held, or a dropped/expired sent series: no point
        series.append((finding_id, tier, value))
    return series


def _series_value(
    state: str,
    created_at: dt.datetime | None,
    sent_at: dt.datetime | None,
    now: dt.datetime,
) -> int | None:
    """The 0/1 value for one job, or None when the job emits no point."""
    if state == NotificationState.FAILED.value:
        return 1
    if state in _PENDING_STATES:
        if created_at is None:
            return 0
        return 1 if (now - created_at) > _OVERDUE_WINDOW else 0
    if state == NotificationState.SENT.value:
        if sent_at is not None and (now - sent_at) > _SENT_SERIES_TTL:
            return None  # kept 24h after sent_at, then dropped
        return 0
    return None  # held: * (A39) and any other state never set the metric


def setup_metrics() -> None:
    """Install the global MeterProvider and create the instruments once."""
    global _provider_installed, notifications_total, notification_delivery_seconds, _overdue_gauge
    if _provider_installed:
        return

    readers = []
    endpoint = settings.get_otlp_endpoint()
    if endpoint is not None:
        from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
            OTLPMetricExporter,
        )

        readers.append(PeriodicExportingMetricReader(OTLPMetricExporter(endpoint=endpoint)))

    provider = MeterProvider(resource=build_resource(), metric_readers=readers)
    metrics.set_meter_provider(provider)
    meter = metrics.get_meter(_METER_SCOPE)

    notifications_total = meter.create_counter(
        "vt_notifications_total",
        description="Owner-notification delivery outcomes by kind and outcome.",
    )
    notification_delivery_seconds = meter.create_histogram(
        "vt_notification_delivery_seconds",
        unit="s",
        description="Owner-notification delivery latency in seconds.",
    )

    _overdue_gauge = meter.create_observable_gauge(
        "vt_top_tier_notification_overdue",
        callbacks=[_observe_overdue],
        description="1 while a top-tier owner notification is overdue; 0 otherwise. "
        "Per-finding series carry finding_id and tier; the label-less series is a "
        "constant 0 heartbeat so NoData means only the backend or metric is down.",
    )
    _provider_installed = True


def _observe_overdue(options):  # type: ignore[no-untyped-def]
    """Observable-gauge callback: the heartbeat plus the per-finding series.

    The constant label-less ``0`` heartbeat is always emitted (from start-up,
    before any DB source is wired), so the metric exists on a fresh system. When
    an overdue source is installed, each in-scope job adds a ``{finding_id,tier}``
    series. The callback never raises out of a collection: a DB error falls back
    to the heartbeat alone, so a transient database problem shows as ``NoData``
    (handled by the rule) rather than crashing the metric pipeline.
    """
    from opentelemetry.metrics import Observation

    observations = [Observation(0)]  # the global heartbeat, no labels
    factory = _overdue_factory
    if factory is None:
        return observations
    try:
        now = _overdue_now()
        with factory() as session:
            series = compute_overdue_series(session, now)
    except Exception:  # noqa: BLE001 - a collection must never raise
        log.warning("overdue gauge collection failed; emitting heartbeat only", exc_info=True)
        return observations
    for finding_id, tier, value in series:
        observations.append(
            Observation(value, {"finding_id": str(finding_id), "tier": tier})
        )
    return observations
