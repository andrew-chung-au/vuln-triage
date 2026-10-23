"""One in-process scan worker thread fed by a queue (D4, issue #76).

The ``Scan`` row is the job: ``start`` re-queues every unfinished scan, so a
restart loses nothing. The worker opens its own ``Session`` per scan.
"""

from __future__ import annotations

import logging
import queue
import threading

from sqlalchemy.orm import Session, sessionmaker

from vulntriage.ingest.github import RepositoryReader
from vulntriage.ingest.osv import OsvClientProtocol
from vulntriage.ingest.scan import run_scan, unfinished_scan_ids
from vulntriage.ingest.signals import EpssClientProtocol, KevClientProtocol

log = logging.getLogger(__name__)


class ScanWorker:
    def __init__(
        self,
        factory: sessionmaker[Session],
        reader: RepositoryReader,
        osv_client: OsvClientProtocol | None = None,
        kev_client: KevClientProtocol | None = None,
        epss_client: EpssClientProtocol | None = None,
    ) -> None:
        self._factory = factory
        self._reader = reader
        self._osv_client = osv_client
        self._kev_client = kev_client
        self._epss_client = epss_client
        self._queue: queue.Queue[int | None] = queue.Queue()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None:
            return
        for scan_id in unfinished_scan_ids(self._factory):
            self._queue.put(scan_id)
        self._thread = threading.Thread(target=self._loop, name="scan-worker", daemon=True)
        self._thread.start()

    def enqueue(self, scan_id: int) -> None:
        self._queue.put(scan_id)

    def stop(self, timeout: float = 10.0) -> None:
        if self._thread is None:
            return
        self._queue.put(None)
        self._thread.join(timeout)
        self._thread = None

    def _loop(self) -> None:
        while True:
            scan_id = self._queue.get()
            if scan_id is None:
                return
            try:
                run_scan(
                    self._factory,
                    self._reader,
                    scan_id,
                    self._osv_client,
                    self._kev_client,
                    self._epss_client,
                )
            except Exception:  # noqa: BLE001 - the worker must survive one bad scan
                # The scan stays unfinished (and is re-queued at the next start-up).
                log.error("scan %s failed unexpectedly", scan_id, exc_info=False)
