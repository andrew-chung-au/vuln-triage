"""#198: a scan that dies from an unexpected exception ends as scan failed / internal error.

Drives ``run_scan`` against in-memory SQLite with a fake reader and an OSV stub
that raises an unexpected exception. Covers the stored end state, the rollback
of the half-written scan, the single ``scan.finished`` log, secret hygiene, a
failing recovery commit, the worker surviving, and a later success clearing the
failure. The migration cases are in ``test_migration_0002.py``.
"""

from __future__ import annotations

import datetime as dt
import json
import threading
from collections.abc import Callable, Iterator, Sequence
from typing import Any

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from sqlalchemy import select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from test_ingest import NPM, UV, FakeReader, make_asset
from vulntriage.api.assets import asset_to_wire
from vulntriage.db.enums import FailureReason, ScanStatus, ScanTrigger
from vulntriage.db.models import Asset, Base, Dependency, Finding, Scan, Vulnerability
from vulntriage.ingest import scan as scan_mod
from vulntriage.ingest.scan import enqueue_scan, run_scan
from vulntriage.worker import ScanWorker

pytestmark = pytest.mark.sqlite_integration

SECRET = "SECRET-EXC-MARKER-5521"
NOW = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)


@pytest.fixture()
def factory(sqlite_engine) -> sessionmaker[Session]:  # type: ignore[no-untyped-def]
    Base.metadata.create_all(sqlite_engine)
    return sessionmaker(sqlite_engine, expire_on_commit=False)


@pytest.fixture()
def captured_spans() -> Iterator[Callable[[], Sequence[ReadableSpan]]]:
    from vulntriage.observability.tracing import setup_tracing

    setup_tracing()
    provider = trace.get_tracer_provider()
    exporter = InMemorySpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(exporter))  # type: ignore[attr-defined]
    try:
        yield exporter.get_finished_spans
    finally:
        exporter.clear()


class ExplodingOsv:
    def query_batch(self, queries: list[Any]) -> list[list[Any]]:
        raise RuntimeError(f"boom {SECRET}")

    def get_vuln(self, osv_id: str) -> dict[str, Any]:
        raise RuntimeError(f"boom {SECRET}")


class CleanOsv:
    def query_batch(self, queries: list[Any]) -> list[list[Any]]:
        return [[] for _ in queries]

    def get_vuln(self, osv_id: str) -> dict[str, Any]:
        raise AssertionError("no advisories expected")


class OnceExploding(CleanOsv):
    """Raises an unexpected exception on the first query only."""

    def __init__(self) -> None:
        self.calls = 0

    def query_batch(self, queries: list[Any]) -> list[list[Any]]:
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError(SECRET)
        return super().query_batch(queries)


def _enqueue(factory: sessionmaker[Session], asset_id: int) -> int:
    with factory() as session:
        scan = enqueue_scan(session, session.get(Asset, asset_id), ScanTrigger.PERSON)
        session.commit()
        return scan.id


def _finished_logs(out: str) -> list[dict[str, Any]]:
    lines = [json.loads(line) for line in out.splitlines() if line.startswith("{")]
    return [r for r in lines if r["event"] == "scan.finished"]


def _seed_good_scan(factory: sessionmaker[Session]) -> tuple[int, int]:
    """One clean scan, then a finding on the asset; returns (asset id, finding id)."""
    aid = make_asset(factory)
    run_scan(factory, FakeReader({"uv.lock": UV}), _enqueue(factory, aid), CleanOsv())
    with factory() as session:
        vuln = Vulnerability(identity_key="CVE-2024-0001", cve_id="CVE-2024-0001")
        session.add(vuln)
        session.flush()
        finding = Finding(
            asset_id=aid, vulnerability_id=vuln.id, ecosystem="PyPI", package="requests",
            tier="P2", rank_inputs={}, rank_reason="r", first_detected_at=NOW,
        )
        session.add(finding)
        session.commit()
        return aid, finding.id


def _dependencies(factory: sessionmaker[Session], aid: int) -> list[tuple[Any, ...]]:
    with factory() as session:
        rows = session.scalars(select(Dependency).where(Dependency.asset_id == aid).order_by(Dependency.id))
        return [(d.id, d.ecosystem, d.name, d.version, d.source_file) for d in rows]


def test_unexpected_exception_ends_as_scan_failed_internal_error(
    factory, captured_spans, capsys  # type: ignore[no-untyped-def]
) -> None:
    aid, finding_id = _seed_good_scan(factory)
    before = _dependencies(factory, aid)
    assert before
    scan_id = _enqueue(factory, aid)
    capsys.readouterr()

    # Different lockfiles than the first scan, so a leaked write would show.
    run_scan(factory, FakeReader({"uv.lock": UV, "package-lock.json": NPM}), scan_id, ExplodingOsv())
    captured = capsys.readouterr()

    with factory() as session:
        scan = session.get(Scan, scan_id)
        asset = session.get(Asset, aid)
        assert scan.finished_at is not None
        assert scan.scan_status == "scan failed"
        assert scan.failure_reason == "internal error" == FailureReason.INTERNAL_ERROR.value
        assert asset.scan_status == "scan failed"
        assert asset.scan_failure_reason == "internal error"
        wire = asset_to_wire(asset, session)
        assert wire["scanFailureReason"] == "internal error"
        finding = session.get(Finding, finding_id)
        assert finding.stale is True
        assert finding.stale_since is not None
        run_trace_id = scan.trace_id

    # The half-written dependency set is rolled back.
    assert _dependencies(factory, aid) == before

    finished = _finished_logs(captured.out)
    assert len(finished) == 1
    log = finished[0]
    assert log["vt.scan.id"] == str(scan_id)
    assert log["vt.scan.status"] == "scan failed"
    assert log["vt.error.code"] == "internal error"
    assert {k for k in log if k.startswith("vt.")} == {"vt.scan.id", "vt.scan.status", "vt.error.code"}
    runs = [s for s in captured_spans() if s.name == "scan.run" and s.attributes["vt.scan.id"] == str(scan_id)]
    assert len(runs) == 1
    assert log["trace_id"] == format(runs[0].get_span_context().trace_id, "032x") == run_trace_id

    # No exception text anywhere.
    assert SECRET not in captured.out
    assert SECRET not in captured.err
    assert SECRET not in json.dumps(wire, default=str)
    for span in captured_spans():
        assert SECRET not in repr(span.attributes)
        assert all(SECRET not in repr(e.attributes) for e in span.events)
    with factory() as session:
        assert SECRET not in repr(session.execute(text("SELECT * FROM scans")).all())
        assert SECRET not in repr(session.execute(text("SELECT * FROM assets")).all())


def test_first_scan_failure_leaves_no_dependency_rows(factory) -> None:  # type: ignore[no-untyped-def]
    aid = make_asset(factory)
    scan_id = _enqueue(factory, aid)
    run_scan(factory, FakeReader({"uv.lock": UV}), scan_id, ExplodingOsv())
    assert _dependencies(factory, aid) == []
    with factory() as session:
        assert session.get(Scan, scan_id).failure_reason == "internal error"


def test_failing_recovery_commit_leaves_the_scan_unfinished(
    factory, capsys, monkeypatch  # type: ignore[no-untyped-def]
) -> None:
    aid = make_asset(factory)
    scan_id = _enqueue(factory, aid)

    def broken_commit(self: Session) -> None:
        raise OperationalError("COMMIT", {}, Exception("database is gone"))

    monkeypatch.setattr(Session, "commit", broken_commit)
    capsys.readouterr()
    with pytest.raises(Exception):  # noqa: B017,PT011 - the re-raised failure, whatever its class
        run_scan(factory, FakeReader({"uv.lock": UV}), scan_id, ExplodingOsv())
    monkeypatch.undo()

    assert _finished_logs(capsys.readouterr().out) == []
    with factory() as session:
        scan = session.get(Scan, scan_id)
        assert scan.finished_at is None
        assert scan.failure_reason is None
    assert scan_id in scan_mod.unfinished_scan_ids(factory)


def test_worker_survives_a_failing_recovery_and_runs_the_next_scan(
    factory, monkeypatch  # type: ignore[no-untyped-def]
) -> None:
    bad_aid = make_asset(factory)
    good_aid = make_asset(factory)
    bad_scan = _enqueue(factory, bad_aid)
    good_scan = _enqueue(factory, good_aid)

    real_commit = Session.commit
    calls = {"n": 0}
    lock = threading.Lock()

    def flaky_commit(self: Session) -> None:
        with lock:
            calls["n"] += 1
            first = calls["n"] == 1
        if first:
            raise OperationalError("COMMIT", {}, Exception("database is gone"))
        real_commit(self)

    monkeypatch.setattr(Session, "commit", flaky_commit)
    worker = ScanWorker(factory, FakeReader({"uv.lock": UV}), OnceExploding())
    worker.start()  # re-queues both unfinished scans in id order
    # stop() queues the sentinel behind both scans, then joins the thread.
    worker.stop(timeout=10)
    monkeypatch.undo()

    with factory() as session:
        assert session.get(Scan, good_scan).finished_at is not None
        bad = session.get(Scan, bad_scan)
        assert bad.finished_at is None  # the recovery commit failed: retried at next start-up
    assert scan_mod.unfinished_scan_ids(factory) == [bad_scan]


def test_worker_survives_an_unexpected_exception_and_runs_the_next_scan(
    factory,  # type: ignore[no-untyped-def]
) -> None:
    bad_aid = make_asset(factory)
    good_aid = make_asset(factory)
    bad_scan = _enqueue(factory, bad_aid)
    good_scan = _enqueue(factory, good_aid)

    worker = ScanWorker(factory, FakeReader({"uv.lock": UV}), OnceExploding())
    worker.start()
    worker.stop(timeout=10)

    with factory() as session:
        bad = session.get(Scan, bad_scan)
        assert bad.finished_at is not None and bad.failure_reason == "internal error"
        good = session.get(Scan, good_scan)
        assert good.finished_at is not None and good.scan_status == ScanStatus.SCANNED_CLEAN.value


def test_a_later_success_clears_the_failure_and_the_stale_mark(factory) -> None:  # type: ignore[no-untyped-def]
    aid, finding_id = _seed_good_scan(factory)
    run_scan(factory, FakeReader({"uv.lock": UV}), _enqueue(factory, aid), ExplodingOsv())
    with factory() as session:
        assert session.get(Finding, finding_id).stale is True

    run_scan(factory, FakeReader({"uv.lock": UV}), _enqueue(factory, aid), CleanOsv())
    with factory() as session:
        asset = session.get(Asset, aid)
        assert asset.scan_failure_reason is None
        assert asset.scan_status == ScanStatus.SCANNED_CLEAN.value
        finding = session.get(Finding, finding_id)
        assert finding.stale is False
        assert finding.stale_since is None


def test_exception_after_the_scan_is_committed_is_not_rewritten(
    factory, monkeypatch  # type: ignore[no-untyped-def]
) -> None:
    """A log failure after a successful commit keeps the finished scan as it is."""
    aid = make_asset(factory)
    scan_id = _enqueue(factory, aid)

    def broken_log(event: str, attributes: Any = None, **kw: Any) -> None:
        raise RuntimeError("log sink down")

    monkeypatch.setattr(scan_mod, "log_event", broken_log)
    with pytest.raises(RuntimeError, match="log sink down"):
        run_scan(factory, FakeReader({"uv.lock": UV}), scan_id, CleanOsv())
    with factory() as session:
        scan = session.get(Scan, scan_id)
        assert scan.scan_status == ScanStatus.SCANNED_CLEAN.value
        assert scan.failure_reason is None
