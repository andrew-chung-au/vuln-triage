"""I-SCHED: the backend scheduler runs the daily refresh and re-scan (task 38).

Fake-clock + stubbed-feed cases, no thread and no sleep: the scheduler's
``run_once`` / ``tick`` / ``catch_up`` are called directly and time is an
injected ``now`` callable. Covers US-7 and the scheduled-re-scan clause of
US-10. These run under ``make test`` (SQLite, no Docker, no network).
"""

from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from github_stub import FixtureTransport
from osv_stub import OsvFixtureTransport
from signals_stub import EpssFixtureTransport, KevFixtureTransport
from vulntriage.db.enums import ScanTrigger
from vulntriage.db.models import Asset, Base, NotificationJob, Scan
from vulntriage.ingest.github import GitHubReader
from vulntriage.ingest.osv import OsvClient
from vulntriage.ingest.scan import enqueue_scan, run_pending_scans
from vulntriage.ingest.signals import EpssClient, KevClient
from vulntriage.scheduler import Scheduler

pytestmark = pytest.mark.sqlite_integration


@pytest.fixture()
def factory(sqlite_engine) -> sessionmaker[Session]:  # type: ignore[no-untyped-def]
    Base.metadata.create_all(sqlite_engine)
    return sessionmaker(sqlite_engine, expire_on_commit=False)


class Clock:
    """A mutable fake clock; the scheduler is built with `now=clock.now`."""

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
    """Register an exposed pygoat asset and scan it, so a KEV-listed finding is P1."""
    with factory() as session:
        asset = Asset(
            name="pygoat", owner_name=None, owner_email="o@example.com",
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


def _scheduled_scan_count(factory: sessionmaker[Session]) -> int:
    with factory() as session:
        return session.scalar(
            select(func.count()).select_from(Scan).where(Scan.trigger == ScanTrigger.SCHEDULE.value)
        )


def _job_count(factory: sessionmaker[Session]) -> int:
    with factory() as session:
        return session.scalar(select(func.count()).select_from(NotificationJob))


def _make_scheduler(factory, clock) -> Scheduler:  # type: ignore[no-untyped-def]
    _reader, _osv, kev, epss = _stub_clients()
    # worker=None: scheduled scans are enqueued as rows and run by the test.
    return Scheduler(factory, worker=None, kev_client=kev, epss_client=epss, now=clock.now)


def test_i_sched_run_once_rescans_every_asset_and_is_idempotent(factory) -> None:  # type: ignore[no-untyped-def]
    _seed_p1_asset(factory)
    # A second asset with no findings, to prove "every asset" is re-scanned.
    with factory() as session:
        session.add(Asset(name="clean", owner_name=None, owner_email=None,
                          criticality="low", internet_facing=False,
                          repository_url="https://github.com/acme/clean"))
        session.commit()

    clock = Clock(dt.datetime(2026, 10, 24, 6, 0, tzinfo=dt.UTC))
    sched = _make_scheduler(factory, clock)

    # Seeding already created the one top-tier job for the P1 finding.
    assert _job_count(factory) == 1

    ids = sched.run_once()
    assert len(ids) == 2  # one schedule scan per asset ("every asset")
    assert _scheduled_scan_count(factory) == 2

    # The refresh is idempotent: the same-lifecycle P1 makes no second job (US-8).
    assert _job_count(factory) == 1

    # A second run the same day still creates no second notification job.
    sched.run_once()
    assert _job_count(factory) == 1


def test_i_sched_catch_up_runs_when_last_run_is_over_24h_old(factory) -> None:  # type: ignore[no-untyped-def]
    _seed_p1_asset(factory)
    # Seed a finished scheduled scan 30 hours before "now".
    now = dt.datetime(2026, 10, 24, 12, 0, tzinfo=dt.UTC)
    with factory() as session:
        asset_id = session.scalar(select(Asset.id))
        session.add(Scan(
            asset_id=asset_id, trigger=ScanTrigger.SCHEDULE.value,
            started_at=now - dt.timedelta(hours=30),
            finished_at=now - dt.timedelta(hours=30),
            scan_status="scanned, findings", failure_reason=None, warnings=[],
            trace_id="0" * 32,
        ))
        session.commit()
    before = _scheduled_scan_count(factory)

    clock = Clock(now)
    sched = _make_scheduler(factory, clock)
    ids = sched.catch_up()

    assert ids, "a last run 30h old should trigger an immediate catch-up"
    assert _scheduled_scan_count(factory) > before


def test_i_sched_catch_up_skips_when_last_run_is_recent(factory) -> None:  # type: ignore[no-untyped-def]
    _seed_p1_asset(factory)
    now = dt.datetime(2026, 10, 24, 12, 0, tzinfo=dt.UTC)
    with factory() as session:
        asset_id = session.scalar(select(Asset.id))
        session.add(Scan(
            asset_id=asset_id, trigger=ScanTrigger.SCHEDULE.value,
            started_at=now - dt.timedelta(hours=10),
            finished_at=now - dt.timedelta(hours=10),
            scan_status="scanned, findings", failure_reason=None, warnings=[],
            trace_id="0" * 32,
        ))
        session.commit()
    before = _scheduled_scan_count(factory)

    clock = Clock(now)
    sched = _make_scheduler(factory, clock)

    # Catch-up does nothing (last run 10h old) ...
    assert sched.catch_up() == []
    assert _scheduled_scan_count(factory) == before
    # ... and a tick the same day does nothing more (already counted as done).
    assert sched.tick() == []
    assert _scheduled_scan_count(factory) == before


def test_i_sched_tick_waits_until_0600_utc(factory) -> None:  # type: ignore[no-untyped-def]
    _seed_p1_asset(factory)
    # Before 06:00 with no prior run: tick does nothing.
    clock = Clock(dt.datetime(2026, 10, 24, 5, 59, tzinfo=dt.UTC))
    sched = _make_scheduler(factory, clock)
    assert sched.tick() == []
    assert _scheduled_scan_count(factory) == 0

    # At 06:00: tick runs once.
    clock.set(dt.datetime(2026, 10, 24, 6, 0, tzinfo=dt.UTC))
    ids = sched.tick()
    assert ids
    count_after = _scheduled_scan_count(factory)
    assert count_after == 1  # one asset

    # A later tick the same day does not run again.
    clock.set(dt.datetime(2026, 10, 24, 9, 0, tzinfo=dt.UTC))
    assert sched.tick() == []
    assert _scheduled_scan_count(factory) == count_after
