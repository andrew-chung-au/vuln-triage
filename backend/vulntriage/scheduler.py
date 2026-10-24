"""The backend scheduler (task 38): the daily KEV/EPSS refresh and re-scan.

Replaces the n8n schedule for submission (US-7, and the scheduled-re-scan clause
of US-10). Once a day at 06:00 UTC it runs the same work as
``POST /signals/refresh`` (``refresh_all``) then enqueues a ``schedule`` scan of
every asset (the same as ``POST /scans``). A catch-up rule covers the server's
nightly stop: at start, if the last completed scheduled run is more than 24
hours old (or none has run), it runs once immediately, then follows the 06:00
schedule.

Testability: the time source is an injected ``now`` callable and the work is a
public ``run_once`` method, so a fake-clock test drives it directly without the
thread or any sleep. The thread form (``start``/``stop``) is for production; it
calls ``tick`` on a cadence and never does the work twice in one UTC day.
"""

from __future__ import annotations

import datetime as dt
import logging
import threading
from collections.abc import Callable

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from vulntriage.db.enums import ScanTrigger
from vulntriage.db.models import Asset, Scan
from vulntriage.ingest.refresh import refresh_all
from vulntriage.ingest.scan import enqueue_scan
from vulntriage.ingest.signals import EpssClientProtocol, KevClientProtocol

log = logging.getLogger(__name__)

# The daily run time and the catch-up threshold (A25, A37).
SCHEDULE_HOUR_UTC = 6
CATCH_UP_AFTER = dt.timedelta(hours=24)
# How often the production thread wakes to check whether 06:00 has passed.
_TICK_INTERVAL = dt.timedelta(minutes=5)


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def last_scheduled_run(session: Session) -> dt.datetime | None:
    """The newest finished ``schedule`` scan's completion time, or None."""
    return session.scalar(
        select(func.max(Scan.finished_at)).where(
            Scan.trigger == ScanTrigger.SCHEDULE.value,
            Scan.finished_at.is_not(None),
        )
    )


class Scheduler:
    """Runs the daily refresh + re-scan inside the backend.

    ``worker`` is the ScanWorker the enqueued ``schedule`` scans are handed to;
    when it is None (tests) the scans are enqueued as rows and run by the test's
    ``run_pending_scans``. ``now`` is the injected time source.
    """

    def __init__(
        self,
        factory: sessionmaker[Session],
        worker: object | None = None,
        kev_client: KevClientProtocol | None = None,
        epss_client: EpssClientProtocol | None = None,
        now: Callable[[], dt.datetime] = _now,
    ) -> None:
        self._factory = factory
        self._worker = worker
        self._kev = kev_client
        self._epss = epss_client
        self._now = now
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        # The UTC date whose 06:00 run has already been done, so a day runs once.
        self._last_run_date: dt.date | None = None

    # -- the work ----------------------------------------------------------

    def run_once(self) -> list[int]:
        """Run the refresh then enqueue a ``schedule`` scan of every asset.

        Returns the enqueued scan ids. Idempotent per lifecycle on the refresh
        side (``refresh_all``); a repeated run the same day creates no second
        notification job. Records today's date as done.
        """
        with self._factory() as session:
            refresh_all(session, self._kev, self._epss)
            session.commit()

        scan_ids: list[int] = []
        with self._factory() as session:
            for asset in session.scalars(select(Asset)):
                scan = enqueue_scan(session, asset, ScanTrigger.SCHEDULE)
                session.flush()
                scan_ids.append(scan.id)
            session.commit()

        if self._worker is not None:
            for scan_id in scan_ids:
                self._worker.enqueue(scan_id)

        self._last_run_date = self._now().date()
        return scan_ids

    def catch_up(self) -> list[int]:
        """Run once immediately if the last scheduled run is >24h old (or none).

        Called at start, before the schedule takes over. Returns the enqueued
        scan ids (empty if no catch-up was needed).
        """
        now = self._now()
        with self._factory() as session:
            last = last_scheduled_run(session)
        if last is None or (now - last) > CATCH_UP_AFTER:
            return self.run_once()
        # A recent run counts as today's run, so 06:00 today does not re-run.
        self._last_run_date = last.date() if last.date() == now.date() else self._last_run_date
        return []

    def tick(self) -> list[int]:
        """Run the daily job if 06:00 UTC has passed today and it has not run.

        Returns the enqueued scan ids (empty when nothing was due). Safe to call
        repeatedly; it runs at most once per UTC day.
        """
        now = self._now()
        if self._last_run_date == now.date():
            return []
        if now.hour < SCHEDULE_HOUR_UTC:
            return []
        return self.run_once()

    # -- the production thread --------------------------------------------

    def start(self) -> None:
        """Run catch-up, then a daemon thread that ticks on a cadence."""
        if self._thread is not None:
            return
        self.catch_up()
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="scheduler", daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self.tick()
            except Exception:  # noqa: BLE001 - a bad tick must not kill the loop
                log.exception("scheduler tick failed")
            self._stop.wait(_TICK_INTERVAL.total_seconds())

    def stop(self, timeout: float = 10.0) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout)
            self._thread = None
