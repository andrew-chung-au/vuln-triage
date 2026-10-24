"""US-14 overdue metric (task 26): ``vt_top_tier_notification_overdue``.

SQLite-integration cases with an injected fake clock, no Docker and no network.
They seed a P1 finding (so the enqueue path creates one ``top tier`` job), flip
the stored job state, and assert the per-finding series the observable gauge
emits:

- ``failed`` → 1; ``sent`` → 0 (kept 24h after ``sent_at``, then dropped);
  ``pending``/``claimed`` → 1 only after the 30-minute window; ``held: *`` never
  emits; and a constant label-less ``0`` heartbeat always exists so a system
  with no jobs still exports the metric (``NoData`` then means the backend is
  down, not an empty system).

Two seams are exercised: ``compute_overdue_series`` directly (the DB → series
logic with a fake clock), and the full observable-gauge callback read back
through an ``InMemoryMetricReader`` on an isolated ``MeterProvider`` (the global
provider can be installed only once per process, so the callback is registered
on a local provider here).
"""

from __future__ import annotations

import datetime as dt

import pytest
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from github_stub import FixtureTransport
from osv_stub import OsvFixtureTransport
from signals_stub import EpssFixtureTransport, KevFixtureTransport
from vulntriage.db.enums import NotificationState, ScanTrigger
from vulntriage.db.models import Asset, Base, NotificationJob
from vulntriage.ingest.github import GitHubReader
from vulntriage.ingest.osv import OsvClient
from vulntriage.ingest.scan import enqueue_scan, run_pending_scans
from vulntriage.ingest.signals import EpssClient, KevClient
from vulntriage.observability import metrics
from vulntriage.observability.tracing import build_resource

pytestmark = pytest.mark.sqlite_integration


@pytest.fixture()
def factory(sqlite_engine) -> sessionmaker[Session]:  # type: ignore[no-untyped-def]
    Base.metadata.create_all(sqlite_engine)
    return sessionmaker(sqlite_engine, expire_on_commit=False)


class Clock:
    """A mutable fake clock; the gauge source is installed with ``clock.now``."""

    def __init__(self, start: dt.datetime) -> None:
        self._t = start

    def now(self) -> dt.datetime:
        return self._t

    def set(self, t: dt.datetime) -> None:
        self._t = t


def _stub_clients():  # type: ignore[no-untyped-def]
    return (
        GitHubReader(FixtureTransport().client(), token_provider=lambda: None),
        OsvClient(OsvFixtureTransport().client()),
        KevClient(KevFixtureTransport().client()),
        EpssClient(EpssFixtureTransport().client()),
    )


def _seed_p1_asset(factory: sessionmaker[Session]) -> int:
    """Register an exposed pygoat asset and scan it: one KEV-listed P1 finding.

    The scan's enqueue path creates exactly one ``top tier`` NotificationJob for
    the P1 finding's lifecycle (``tier`` = ``P1``, ``state`` = ``pending``).
    """
    with factory() as session:
        asset = Asset(
            name="pygoat", owner_name="Owner", owner_email="owner@team.example",
            criticality="high", internet_facing=True,
            repository_url="https://github.com/adeyosemanputra/pygoat",
        )
        session.add(asset)
        session.flush()
        enqueue_scan(session, asset, ScanTrigger.REGISTRATION)
        aid = asset.id
        session.commit()
    reader, osv, kev, epss = _stub_clients()
    run_pending_scans(factory, reader, osv, kev, epss)
    return aid


def _only_job(factory: sessionmaker[Session]) -> NotificationJob:
    with factory() as session:
        job = session.scalar(select(NotificationJob))
        assert job is not None, "expected exactly one top-tier job from the seed"
        return job


def _set_job(
    factory: sessionmaker[Session],
    job_id: int,
    *,
    state: str,
    created_at: dt.datetime | None = None,
    sent_at: dt.datetime | None = None,
) -> None:
    """Flip a seeded job's stored state/timestamps in one transaction."""
    with factory() as session:
        job = session.get(NotificationJob, job_id)
        assert job is not None
        job.state = state
        if created_at is not None:
            job.created_at = created_at
        if sent_at is not None:
            job.sent_at = sent_at
        session.commit()


# -- compute_overdue_series: the DB -> series logic (fake clock) ------------


def _series(factory: sessionmaker[Session], now: dt.datetime) -> list[tuple[int, str, int]]:
    with factory() as session:
        return metrics.compute_overdue_series(session, now)


def test_failed_job_is_overdue_value_one(factory) -> None:  # type: ignore[no-untyped-def]
    _seed_p1_asset(factory)
    job = _only_job(factory)
    _set_job(factory, job.id, state=NotificationState.FAILED.value)

    series = _series(factory, dt.datetime(2026, 1, 1, tzinfo=dt.UTC))

    assert len(series) == 1
    finding_id, tier, value = series[0]
    assert tier == "P1"
    assert value == 1
    assert finding_id > 0  # resolved through the job's lifecycle


def test_sent_job_is_zero_and_kept_24h_then_dropped(factory) -> None:  # type: ignore[no-untyped-def]
    _seed_p1_asset(factory)
    job = _only_job(factory)
    sent_at = dt.datetime(2026, 1, 1, 12, 0, tzinfo=dt.UTC)
    _set_job(factory, job.id, state=NotificationState.SENT.value, sent_at=sent_at)

    # Within 24h: a 0 series still exists (the alert resolves rather than vanishes).
    within = _series(factory, sent_at + dt.timedelta(hours=23, minutes=59))
    assert len(within) == 1
    assert within[0][2] == 0

    # Past 24h: the series is dropped so the series set stays bounded.
    after = _series(factory, sent_at + dt.timedelta(hours=24, minutes=1))
    assert after == []


def test_pending_job_overdue_only_after_the_30_minute_window(factory) -> None:  # type: ignore[no-untyped-def]
    _seed_p1_asset(factory)
    job = _only_job(factory)
    created = dt.datetime(2026, 1, 1, 0, 0, tzinfo=dt.UTC)
    _set_job(factory, job.id, state=NotificationState.PENDING.value, created_at=created)

    # 29 minutes in: still within the window, value 0 (not yet overdue).
    just_before = _series(factory, created + dt.timedelta(minutes=29))
    assert len(just_before) == 1
    assert just_before[0][2] == 0

    # 31 minutes in: past the window, value 1.
    just_after = _series(factory, created + dt.timedelta(minutes=31))
    assert len(just_after) == 1
    assert just_after[0][2] == 1


def test_claimed_job_follows_the_same_window(factory) -> None:  # type: ignore[no-untyped-def]
    _seed_p1_asset(factory)
    job = _only_job(factory)
    created = dt.datetime(2026, 1, 1, 0, 0, tzinfo=dt.UTC)
    _set_job(factory, job.id, state=NotificationState.CLAIMED.value, created_at=created)

    assert _series(factory, created + dt.timedelta(minutes=10))[0][2] == 0
    assert _series(factory, created + dt.timedelta(minutes=45))[0][2] == 1


def test_held_jobs_never_emit(factory) -> None:  # type: ignore[no-untyped-def]
    _seed_p1_asset(factory)
    job = _only_job(factory)
    for held in (
        NotificationState.HELD_OWNERLESS.value,
        NotificationState.HELD_OWNER_EMAIL_MISSING.value,
        NotificationState.HELD_CONFIGURATION_ERROR.value,
    ):
        _set_job(factory, job.id, state=held)
        assert _series(factory, dt.datetime(2026, 6, 1, tzinfo=dt.UTC)) == []


def test_empty_system_has_no_finding_series(factory) -> None:  # type: ignore[no-untyped-def]
    # No jobs at all: the series logic yields nothing (the heartbeat is added by
    # the callback, not here).
    assert _series(factory, dt.datetime(2026, 1, 1, tzinfo=dt.UTC)) == []


# -- the observable-gauge callback through an InMemoryMetricReader ----------


def _read_overdue_points(reader: InMemoryMetricReader) -> list[tuple[dict, float]]:
    """Return ``(attributes, value)`` for every vt_top_tier_notification_overdue point."""
    data = reader.get_metrics_data()
    points: list[tuple[dict, float]] = []
    if data is None:
        return points
    for rm in data.resource_metrics:
        for sm in rm.scope_metrics:
            for metric in sm.metrics:
                if metric.name != "vt_top_tier_notification_overdue":
                    continue
                for dp in metric.data.data_points:
                    points.append((dict(dp.attributes), dp.value))
    return points


def _isolated_reader_with_overdue_gauge():  # type: ignore[no-untyped-def]
    """A local MeterProvider whose only instrument is the overdue gauge.

    The global provider can be set once per process, so the callback is
    registered on a throwaway provider here and read synchronously via
    ``InMemoryMetricReader.get_metrics_data()``.
    """
    reader = InMemoryMetricReader()
    provider = MeterProvider(resource=build_resource(), metric_readers=[reader])
    meter = provider.get_meter("vulntriage-test")
    meter.create_observable_gauge(
        "vt_top_tier_notification_overdue",
        callbacks=[metrics._observe_overdue],
    )
    return reader, provider


def test_callback_emits_heartbeat_with_no_source() -> None:
    # No overdue source installed: only the label-less 0 heartbeat.
    metrics.set_overdue_source(None)
    reader, provider = _isolated_reader_with_overdue_gauge()
    try:
        points = _read_overdue_points(reader)
    finally:
        provider.shutdown()

    assert len(points) == 1
    attrs, value = points[0]
    assert attrs == {}
    assert value == 0


def test_callback_emits_heartbeat_plus_finding_series(factory) -> None:  # type: ignore[no-untyped-def]
    _seed_p1_asset(factory)
    job = _only_job(factory)
    _set_job(factory, job.id, state=NotificationState.FAILED.value)

    clock = Clock(dt.datetime(2026, 1, 1, tzinfo=dt.UTC))
    metrics.set_overdue_source(factory, now=clock.now)
    reader, provider = _isolated_reader_with_overdue_gauge()
    try:
        points = _read_overdue_points(reader)
    finally:
        provider.shutdown()
        metrics.set_overdue_source(None)  # leave the module clean for other tests

    # Exactly two points: the heartbeat (no labels) and the failed finding (=1).
    assert len(points) == 2
    heartbeat = [p for p in points if p[0] == {}]
    finding = [p for p in points if p[0] != {}]
    assert len(heartbeat) == 1 and heartbeat[0][1] == 0
    assert len(finding) == 1
    attrs, value = finding[0]
    assert attrs.get("tier") == "P1"
    assert "finding_id" in attrs
    assert value == 1


def test_callback_empty_system_emits_only_heartbeat(factory) -> None:  # type: ignore[no-untyped-def]
    # A system with no jobs: the source is wired but yields only the heartbeat,
    # so NoData can mean "backend down", never "no work to do".
    metrics.set_overdue_source(factory, now=lambda: dt.datetime(2026, 1, 1, tzinfo=dt.UTC))
    reader, provider = _isolated_reader_with_overdue_gauge()
    try:
        points = _read_overdue_points(reader)
    finally:
        provider.shutdown()
        metrics.set_overdue_source(None)

    assert len(points) == 1
    assert points[0][0] == {} and points[0][1] == 0
