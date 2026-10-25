"""#194: every terminal scan.run outcome emits exactly one scan.finished log.

Drives ``run_scan`` against in-memory SQLite and a fake reader, captures the
stdout JSON line of ``log_event`` with ``capsys`` and the exported ``scan.run``
span with an in-memory span exporter, and compares trace ids.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator, Sequence
from typing import Any

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from sqlalchemy.orm import Session, sessionmaker

from test_ingest import NPM, UV, FakeReader, make_asset
from vulntriage.db.enums import FailureReason, ScanStatus, ScanTrigger
from vulntriage.db.models import Asset, Base, Scan
from vulntriage.ingest import scan as scan_mod
from vulntriage.ingest.osv import FeedUnavailable
from vulntriage.ingest.scan import enqueue_scan, run_scan

pytestmark = pytest.mark.sqlite_integration

URL_MARKER = "https://github.com/url-marker-owner/url-marker-repo"
FILE_MARKER = "FILE-BODY-MARKER-9137"


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


class FailingOsv:
    def query_batch(self, queries: list[Any]) -> list[list[Any]]:
        raise FeedUnavailable("down")

    def get_vuln(self, osv_id: str) -> dict[str, Any]:
        raise FeedUnavailable("down")


class CleanOsv:
    def query_batch(self, queries: list[Any]) -> list[list[Any]]:
        return [[] for _ in queries]

    def get_vuln(self, osv_id: str) -> dict[str, Any]:
        raise AssertionError("no advisories expected")


def _enqueue(factory: sessionmaker[Session], asset_id: int) -> int:
    with factory() as session:
        scan = enqueue_scan(session, session.get(Asset, asset_id), ScanTrigger.PERSON)
        session.commit()
        return scan.id


def _log_lines(out: str) -> list[dict[str, Any]]:
    return [json.loads(line) for line in out.splitlines() if line.startswith("{")]


def _finished(out: str) -> list[dict[str, Any]]:
    return [r for r in _log_lines(out) if r["event"] == "scan.finished"]


def _run_span(spans: Sequence[ReadableSpan]) -> ReadableSpan:
    runs = [s for s in spans if s.name == "scan.run"]
    assert len(runs) == 1
    return runs[0]


def _id_hex(n: int, width: int) -> str:
    return format(n, f"0{width}x")


FAILURES = [
    pytest.param(
        "https://example.com/not-a-github-url", FakeReader(), None,
        FailureReason.REPOSITORY_UNAVAILABLE, id="unparseable-url",
    ),
    pytest.param(
        URL_MARKER, FakeReader(unavailable=True), None,
        FailureReason.REPOSITORY_UNAVAILABLE, id="repository-unavailable",
    ),
    pytest.param(
        URL_MARKER, FakeReader(), None,
        FailureReason.NO_DEPENDENCY_FILES, id="no-dependency-files",
    ),
    pytest.param(
        URL_MARKER, FakeReader({"uv.lock": "this is not toml " + FILE_MARKER + " ["}), None,
        FailureReason.LOCKFILE_PARSE_ERROR, id="lockfile-parse-error",
    ),
    pytest.param(
        URL_MARKER, FakeReader({"uv.lock": UV}), FailingOsv(),
        FailureReason.FEED_UNAVAILABLE, id="feed-unavailable",
    ),
]


@pytest.mark.parametrize(("url", "reader", "osv", "reason"), FAILURES)
def test_failed_scan_logs_one_scan_finished_with_the_run_trace(
    factory, captured_spans, capsys, monkeypatch, url, reader, osv, reason  # type: ignore[no-untyped-def]
) -> None:
    aid = make_asset(factory, url)
    scan_id = _enqueue(factory, aid)

    # Order: at the moment of the log the failure is already committed.
    seen: list[tuple[str | None, str | None]] = []
    real_log_event = scan_mod.log_event

    def spy(event: str, attributes: Any = None, **kw: Any) -> None:
        with factory() as other:
            row = other.get(Scan, scan_id)
            seen.append((row.scan_status, row.failure_reason))
        real_log_event(event, attributes, **kw)

    monkeypatch.setattr(scan_mod, "log_event", spy)
    capsys.readouterr()
    run_scan(factory, reader, scan_id, osv)
    out = capsys.readouterr().out

    finished = _finished(out)
    assert len(finished) == 1
    log = finished[0]
    assert seen == [(ScanStatus.SCAN_FAILED.value, reason.value)]
    assert log["vt.scan.id"] == str(scan_id)
    assert log["vt.scan.status"] == "scan failed"
    assert log["vt.error.code"] == reason.value
    assert {k for k in log if k.startswith("vt.")} == {"vt.scan.id", "vt.scan.status", "vt.error.code"}

    run = _run_span(captured_spans())
    run_ctx = run.get_span_context()
    run_trace = _id_hex(run_ctx.trace_id, 32)
    assert log["trace_id"] == run_trace
    assert log["trace_id"] != "0" * 32
    assert log["span_id"] != "0" * 16
    children = {_id_hex(s.get_span_context().span_id, 16) for s in captured_spans()
                if s.parent is not None and s.parent.span_id == run_ctx.span_id}
    assert log["span_id"] in children | {_id_hex(run_ctx.span_id, 16)}
    with factory() as session:
        assert session.get(Scan, scan_id).trace_id == run_trace

    # Allowlist limit: no URL, file content or exception text on the line.
    assert "url-marker" not in out
    assert FILE_MARKER not in out
    assert "not-a-github-url" not in out


def test_success_log_is_unchanged_and_in_the_run_trace(factory, captured_spans, capsys) -> None:  # type: ignore[no-untyped-def]
    aid = make_asset(factory)
    scan_id = _enqueue(factory, aid)
    capsys.readouterr()
    run_scan(factory, FakeReader({"uv.lock": UV, "package-lock.json": NPM}), scan_id, CleanOsv())
    out = capsys.readouterr().out

    finished = _finished(out)
    assert len(finished) == 1
    log = finished[0]
    assert log["vt.scan.id"] == str(scan_id)
    assert log["vt.scan.status"] == ScanStatus.SCANNED_CLEAN.value
    assert "vt.error.code" not in log
    assert {k for k in log if k.startswith("vt.")} == {"vt.scan.id", "vt.scan.status"}
    run = _run_span(captured_spans())
    assert log["trace_id"] == _id_hex(run.get_span_context().trace_id, 32)
    assert log["span_id"] != "0" * 16


def test_rerun_of_a_finished_scan_logs_nothing(factory, capsys) -> None:  # type: ignore[no-untyped-def]
    aid = make_asset(factory)
    scan_id = _enqueue(factory, aid)
    run_scan(factory, FakeReader({"uv.lock": UV}), scan_id, CleanOsv())
    capsys.readouterr()
    run_scan(factory, FakeReader({"uv.lock": UV}), scan_id, CleanOsv())
    assert _finished(capsys.readouterr().out) == []


def test_missing_scan_logs_nothing(factory, capsys) -> None:  # type: ignore[no-untyped-def]
    capsys.readouterr()
    run_scan(factory, FakeReader({"uv.lock": UV}), 9999, CleanOsv())
    assert _finished(capsys.readouterr().out) == []

# test_scan_with_missing_asset_logs_nothing is in test_scan_orphaned_scan.py: it
# needs SQLite's PRAGMA, so it is unit-only (not run by the Postgres job).
