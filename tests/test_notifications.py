"""I-OWNER-*, S-NOTIFY: the backend owner-notification delivery worker (task 37).

SQLite-integration cases with an in-process fake mail sink (RecordingTransport),
no Docker, no AWS and no network. They seed a P1 finding (so the enqueue path
creates one ``top tier`` job), run the DeliveryWorker, and assert the send, the
hold, the once-only and the verified-sender behaviour, plus the US-13
``notification.deliver`` span as a child of the stored enqueue ``traceparent``.

The MailHog variants of ``I-OWNER-NOAWS`` / ``I-OWNER-SENDER`` run under
``make test-compose``; here the same assertions run against the in-process sink.
"""

from __future__ import annotations

import datetime as dt

import pytest
from collections.abc import Callable, Iterator, Sequence

from opentelemetry import trace
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from github_stub import FixtureTransport
from osv_stub import OsvFixtureTransport
from signals_stub import EpssFixtureTransport, KevFixtureTransport
from vulntriage.db.enums import NotificationState, ScanTrigger
from vulntriage.db.models import Advisory, Asset, Base, Finding, Lifecycle, NotificationJob
from vulntriage.ingest.github import GitHubReader
from vulntriage.ingest.osv import OsvClient
from vulntriage.ingest.scan import enqueue_scan, run_pending_scans
from vulntriage.ingest.signals import EpssClient, KevClient
from vulntriage.mail.delivery import DeliveryWorker
from vulntriage.mail.transport import RecordingTransport

pytestmark = pytest.mark.sqlite_integration

VERIFIED_SENDER = "vulntriage@sender.example"


@pytest.fixture()
def factory(sqlite_engine) -> sessionmaker[Session]:  # type: ignore[no-untyped-def]
    Base.metadata.create_all(sqlite_engine)
    return sessionmaker(sqlite_engine, expire_on_commit=False)


@pytest.fixture()
def captured_spans() -> Iterator[Callable[[], Sequence[ReadableSpan]]]:
    """Capture finished spans for one test via an in-memory exporter.

    The backend installs one global SDK ``TracerProvider`` with no exporter
    (A40: export is a no-op, span contexts are always real). Rather than swap
    the global (it can be set only once), this attaches an extra
    ``SimpleSpanProcessor``/``InMemorySpanExporter`` to the live provider, so
    spans this test produces are exported into memory as they end. It calls
    ``setup_tracing`` first so a real SDK provider is in place, and returns a
    getter for the finished spans.
    """
    from vulntriage.observability.tracing import setup_tracing

    setup_tracing()
    provider = trace.get_tracer_provider()
    exporter = InMemorySpanExporter()
    # The SDK TracerProvider accepts added processors at any time; the API's
    # no-op ProxyTracerProvider does not, but setup_tracing guarantees the SDK.
    provider.add_span_processor(SimpleSpanProcessor(exporter))  # type: ignore[attr-defined]
    try:
        yield exporter.get_finished_spans
    finally:
        exporter.clear()


def _stub_clients():  # type: ignore[no-untyped-def]
    return (
        GitHubReader(FixtureTransport().client(), token_provider=lambda: None),
        OsvClient(OsvFixtureTransport().client()),
        KevClient(KevFixtureTransport().client()),
        EpssClient(EpssFixtureTransport().client()),
    )


def _seed_p1_asset(
    factory: sessionmaker[Session],
    *,
    owner_name: str | None = "Owner",
    owner_email: str | None = "owner@team.example",
) -> int:
    """Register an exposed pygoat asset and scan it: one KEV-listed P1 finding.

    The scan's enqueue path creates exactly one ``top tier`` NotificationJob for
    the P1 finding's lifecycle. Owner fields are parameters so the hold cases can
    seed an ownerless or name-only-owner asset.
    """
    with factory() as session:
        asset = Asset(
            name="pygoat", owner_name=owner_name, owner_email=owner_email,
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


def _job_count(factory: sessionmaker[Session]) -> int:
    with factory() as session:
        return session.scalar(select(func.count()).select_from(NotificationJob))


def _only_job(factory: sessionmaker[Session]) -> NotificationJob:
    with factory() as session:
        job = session.scalar(select(NotificationJob))
        assert job is not None, "expected exactly one top-tier job from the seed"
        return job


def _worker(factory, transport) -> DeliveryWorker:  # type: ignore[no-untyped-def]
    return DeliveryWorker(factory, transport=transport)


# -- I-OWNER-SEND -----------------------------------------------------------


def test_i_owner_send_one_message_and_sent_state(factory) -> None:  # type: ignore[no-untyped-def]
    _seed_p1_asset(factory)
    assert _job_count(factory) == 1

    sink = RecordingTransport(VERIFIED_SENDER)
    sent = _worker(factory, sink).deliver_pending()

    assert sent == 1
    assert len(sink.sent) == 1  # exactly one plain-text message to the owner
    message = sink.sent[0]
    assert message.sender == VERIFIED_SENDER
    assert message.recipient == "owner@team.example"
    assert message.as_email_message().get_content_type() == "text/plain"

    job = _only_job(factory)
    assert job.state == NotificationState.SENT.value
    assert job.sent_at is not None

    # The lifecycle is stamped so a re-enqueue sends no second email.
    with factory() as session:
        lifecycle = session.get(Lifecycle, job.lifecycle_id)
        assert lifecycle is not None and lifecycle.owner_notified_at is not None


def test_i_owner_send_deliver_span_is_child_of_stored_traceparent(
    factory, captured_spans
) -> None:  # type: ignore[no-untyped-def]
    """notification.deliver joins the stored enqueue trace (US-13, A40)."""
    _seed_p1_asset(factory)
    job = _only_job(factory)
    stored = job.traceparent
    # The stored traceparent is a valid non-zero W3C value even with no Collector.
    assert stored.startswith("00-")
    trace_id_hex = stored.split("-")[1]
    assert int(trace_id_hex, 16) != 0

    _worker(factory, RecordingTransport(VERIFIED_SENDER)).deliver_pending()

    deliver_spans = [s for s in captured_spans() if s.name == "notification.deliver"]
    assert len(deliver_spans) == 1
    deliver = deliver_spans[0]
    # Same trace id as the stored enqueue traceparent -> the journey is one trace.
    assert trace.format_trace_id(deliver.context.trace_id) == trace_id_hex
    # The deliver span's parent is the stored enqueue span id.
    assert deliver.parent is not None
    assert trace.format_span_id(deliver.parent.span_id) == stored.split("-")[2]


# -- I-OWNER-NOAWS ----------------------------------------------------------


def test_i_owner_noaws_message_reaches_sink_without_aws(factory) -> None:  # type: ignore[no-untyped-def]
    """No AWS credential is used: the message reaches the in-process sink."""
    _seed_p1_asset(factory)
    sink = RecordingTransport(VERIFIED_SENDER)
    _worker(factory, sink).deliver_pending()
    assert [m.recipient for m in sink.sent] == ["owner@team.example"]


# -- I-OWNER-SENDER ---------------------------------------------------------


def test_i_owner_sender_refused_when_not_verified(factory) -> None:  # type: ignore[no-untyped-def]
    """A send from any address other than the verified sender delivers nothing."""
    _seed_p1_asset(factory)
    # The transport's verified sender differs from what the worker will build
    # from... no: the worker always builds From = transport.verified_sender, so
    # to exercise the refusal we give the transport a verified sender but the
    # message's From is forced wrong by a transport whose check rejects it.
    # Here we assert the transport-level guard directly against a crafted send.
    from vulntriage.mail.message import build_message
    from vulntriage.mail.transport import SenderNotVerifiedError

    sink = RecordingTransport(VERIFIED_SENDER)
    wrong = build_message(
        sender="attacker@evil.example", recipient="owner@team.example",
        finding_id="1", tier="P1",
    )
    with pytest.raises(SenderNotVerifiedError):
        sink.send(wrong)
    assert sink.sent == []  # nothing delivered


def test_i_owner_sender_worker_holds_on_refusal(factory) -> None:  # type: ignore[no-untyped-def]
    """When the transport refuses the sender, the job is held, not sent."""
    _seed_p1_asset(factory)

    class RefusingTransport:
        verified_sender = VERIFIED_SENDER

        def send(self, message):  # type: ignore[no-untyped-def]
            from vulntriage.mail.transport import SenderNotVerifiedError

            raise SenderNotVerifiedError("refused")

    _worker(factory, RefusingTransport()).deliver_pending()
    job = _only_job(factory)
    assert job.state == NotificationState.HELD_CONFIGURATION_ERROR.value
    assert job.last_error_code == "sender_not_verified"


# -- I-OWNER-ONCE -----------------------------------------------------------


def test_i_owner_once_second_deliver_sends_nothing(factory) -> None:  # type: ignore[no-untyped-def]
    _seed_p1_asset(factory)
    sink = RecordingTransport(VERIFIED_SENDER)
    worker = _worker(factory, sink)

    assert worker.deliver_pending() == 1
    # A second poll selects no pending job (the first is `sent`).
    assert worker.deliver_pending() == 0
    assert len(sink.sent) == 1
    assert _job_count(factory) == 1


def test_i_owner_once_failed_retries_then_sends_one(factory) -> None:  # type: ignore[no-untyped-def]
    """A transient failure retries on the next poll and sends exactly one email."""
    _seed_p1_asset(factory)

    class FlakyTransport:
        verified_sender = VERIFIED_SENDER

        def __init__(self) -> None:
            self.calls = 0
            self.sent: list = []

        def send(self, message):  # type: ignore[no-untyped-def]
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("smtp down")
            self.sent.append(message)

    flaky = FlakyTransport()
    worker = _worker(factory, flaky)

    assert worker.deliver_pending() == 0  # first attempt fails
    job = _only_job(factory)
    assert job.state == NotificationState.FAILED.value
    assert job.attempts == 1

    # The worker re-selects a `failed` job on the next poll (the acceptance
    # criterion "a failed job retries on the next poll"); the retry sends one.
    assert worker.deliver_pending() == 1
    assert len(flaky.sent) == 1
    with factory() as session:
        j = session.get(NotificationJob, job.id)
        assert j.state == NotificationState.SENT.value
        assert j.attempts == 2  # the failed attempt plus the successful one


# -- I-OWNER-HOLD -----------------------------------------------------------


def test_i_owner_hold_ownerless_sends_nothing(factory) -> None:  # type: ignore[no-untyped-def]
    """E2: an ownerless asset's notification is held and nothing is sent."""
    _seed_p1_asset(factory, owner_name=None, owner_email=None)
    sink = RecordingTransport(VERIFIED_SENDER)
    sent = _worker(factory, sink).deliver_pending()
    assert sent == 0
    assert sink.sent == []
    job = _only_job(factory)
    assert job.state == NotificationState.HELD_OWNERLESS.value


def test_i_owner_hold_name_only_owner_sends_nothing(factory) -> None:  # type: ignore[no-untyped-def]
    """A21: an owner with a name but no email is held (owner email missing)."""
    _seed_p1_asset(factory, owner_name="No Email", owner_email=None)
    sink = RecordingTransport(VERIFIED_SENDER)
    sent = _worker(factory, sink).deliver_pending()
    assert sent == 0
    assert sink.sent == []
    job = _only_job(factory)
    assert job.state == NotificationState.HELD_OWNER_EMAIL_MISSING.value


# -- S-NOTIFY (advisory defang in the delivered body) -----------------------


def test_s_notify_advisory_url_is_defanged_in_sent_body(factory) -> None:  # type: ignore[no-untyped-def]
    """The delivered body carries defanged advisory text (no live URL)."""
    _seed_p1_asset(factory)
    # Edit the advisory of the exact finding the pending job points to, so the
    # delivered body is the one we seeded regardless of row order (the SQLite
    # and Postgres harnesses return findings in different orders).
    job = _only_job(factory)
    with factory() as session:
        lifecycle = session.get(Lifecycle, job.lifecycle_id)
        finding = session.get(Finding, lifecycle.finding_id)
        # A vulnerability may carry more than one advisory (merged aliases, E9),
        # and the worker reads one with no fixed order, so edit every advisory
        # of this vulnerability. Then whichever one the worker picks carries the
        # seeded URL, regardless of SQLite/Postgres row order.
        advisories = list(
            session.scalars(
                select(Advisory).where(Advisory.vulnerability_id == finding.vulnerability_id)
            )
        )
        assert advisories, "expected at least one advisory for the delivered finding"
        for advisory in advisories:
            advisory.summary = "Exploit at https://evil.example/x and www.evil.example"
        session.commit()

    sink = RecordingTransport(VERIFIED_SENDER)
    _worker(factory, sink).deliver_pending()
    body = sink.sent[0].body
    assert "https://" not in body
    assert "hxxps[:]//evil[.]example/x" in body
    assert "www[.]evil[.]example" in body


# -- S-NOTIFY-LOG (#177): the delivery log carries the job's journey trace id ---


@pytest.fixture()
def captured_logs():  # type: ignore[no-untyped-def]
    """Capture emitted OTLP log records for one test via an in-memory exporter.

    Attaches an InMemoryLogRecordExporter (on a SimpleLogRecordProcessor, so it
    is synchronous — no flush timing) to the dedicated telemetry logger that
    log_event emits on, mirroring the #174 pattern. Returns a getter for the
    finished log records.
    """
    import logging as _logging

    from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
    from opentelemetry.sdk._logs.export import (
        InMemoryLogRecordExporter,
        SimpleLogRecordProcessor,
    )

    from vulntriage.observability import logs as logs_mod

    logs_mod.setup_logging()
    exporter = InMemoryLogRecordExporter()
    provider = LoggerProvider()
    provider.add_log_record_processor(SimpleLogRecordProcessor(exporter))
    handler = LoggingHandler(level=_logging.NOTSET, logger_provider=provider)
    logs_mod._otel_logger.addHandler(handler)
    try:
        yield exporter.get_finished_logs
    finally:
        logs_mod._otel_logger.removeHandler(handler)
        provider.shutdown()


def test_s_notify_log_delivery_log_shares_the_jobs_traceparent_trace_id(
    factory, captured_logs
) -> None:  # type: ignore[no-untyped-def]
    """#177: the delivery outcome is logged with the job's journey trace id.

    Not merely "a log was written" — the log record's trace id must equal the
    trace id in the job's stored notification.enqueue traceparent (the journey
    trace), because it is emitted inside the notification.deliver span (a child
    of that traceparent). A log with any trace id is how this gap survived QA.
    """
    _seed_p1_asset(factory)
    job = _only_job(factory)
    # The journey trace id is the middle field of the stored W3C traceparent.
    expected_trace_id = job.traceparent.split("-")[1]
    assert len(expected_trace_id) == 32 and int(expected_trace_id, 16) != 0

    sent = _worker(factory, RecordingTransport(VERIFIED_SENDER)).deliver_pending()
    assert sent == 1

    deliver_logs = [
        lr.log_record
        for lr in captured_logs()
        if (lr.log_record.body == "notification.deliver"
            or (lr.log_record.attributes or {}).get("vt.event") == "notification.deliver")
    ]
    assert len(deliver_logs) == 1, f"expected one delivery log, got {len(deliver_logs)}"
    record = deliver_logs[0]
    attrs = dict(record.attributes or {})
    assert attrs.get("vt.outcome") == "sent", attrs
    assert attrs.get("vt.finding.id"), attrs
    # No excluded data leaked onto the log.
    for forbidden in ("owner.email", "authorization", "url.full", "db.statement"):
        assert forbidden not in attrs
    # The journey join: the log's trace id equals the job's stored traceparent.
    assert trace.format_trace_id(record.trace_id) == expected_trace_id


def test_s_notify_log_failed_outcome_is_logged(factory) -> None:  # type: ignore[no-untyped-def]
    """A failed delivery is logged too (the US-15 responder reads this from Loki)."""
    import logging as _logging

    from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
    from opentelemetry.sdk._logs.export import (
        InMemoryLogRecordExporter,
        SimpleLogRecordProcessor,
    )

    from vulntriage.observability import logs as logs_mod

    _seed_p1_asset(factory)

    class FailingTransport:
        verified_sender = VERIFIED_SENDER

        def send(self, message):  # type: ignore[no-untyped-def]
            raise RuntimeError("smtp down")

    logs_mod.setup_logging()
    exporter = InMemoryLogRecordExporter()
    provider = LoggerProvider()
    provider.add_log_record_processor(SimpleLogRecordProcessor(exporter))
    handler = LoggingHandler(level=_logging.NOTSET, logger_provider=provider)
    logs_mod._otel_logger.addHandler(handler)
    try:
        _worker(factory, FailingTransport()).deliver_pending()
        records = [
            lr.log_record for lr in exporter.get_finished_logs()
            if lr.log_record.body == "notification.deliver"
            or (lr.log_record.attributes or {}).get("vt.event") == "notification.deliver"
        ]
    finally:
        logs_mod._otel_logger.removeHandler(handler)
        provider.shutdown()

    assert records, "a failed delivery emitted no notification.deliver log"
    attrs = dict(records[-1].attributes or {})
    assert attrs.get("vt.outcome") == "failed", attrs
    assert attrs.get("vt.error.code") == "send_failed", attrs


# -- #193: every outcome emits the span, the log and one counter increment ------

_LEAK_OWNER_NAME = "Leaky Ownername"
_LEAK_OWNER_EMAIL = "leaky.owner@team.example"
_LEAK_ADVISORY = "SECRETADVISORYTEXT https://evil.example/leak"


@pytest.fixture()
def captured_counter(monkeypatch):  # type: ignore[no-untyped-def]
    """Route ``vt_notifications_total`` to a local in-memory reader.

    The global MeterProvider can be installed once per process, so a throwaway
    provider's counter replaces the module-level instrument for one test.
    Returns a getter for ``(attributes, value)`` points.
    """
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import InMemoryMetricReader

    from vulntriage.observability import metrics as metrics_mod

    metrics_mod.setup_metrics()
    reader = InMemoryMetricReader()
    provider = MeterProvider(metric_readers=[reader])
    counter = provider.get_meter("vulntriage-test").create_counter("vt_notifications_total")
    monkeypatch.setattr(metrics_mod, "notifications_total", counter)

    def points() -> list[tuple[dict, float]]:
        out: list[tuple[dict, float]] = []
        data = reader.get_metrics_data()
        if data is None:
            return out
        for rm in data.resource_metrics:
            for sm in rm.scope_metrics:
                for metric in sm.metrics:
                    if metric.name == "vt_notifications_total":
                        for dp in metric.data.data_points:
                            out.append((dict(dp.attributes), dp.value))
        return out

    try:
        yield points
    finally:
        provider.shutdown()


class _RaisingTransport:
    verified_sender = VERIFIED_SENDER

    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    def send(self, message):  # type: ignore[no-untyped-def]
        raise self._exc


def _taint_advisory(factory: sessionmaker[Session]) -> None:
    job = _only_job(factory)
    with factory() as session:
        lifecycle = session.get(Lifecycle, job.lifecycle_id)
        finding = session.get(Finding, lifecycle.finding_id)
        for advisory in session.scalars(
            select(Advisory).where(Advisory.vulnerability_id == finding.vulnerability_id)
        ):
            advisory.summary = _LEAK_ADVISORY
        session.commit()


def _deliver_case(factory, monkeypatch, case: str) -> DeliveryWorker:  # type: ignore[no-untyped-def]
    """Seed a job that will end in ``case`` and return the worker to poll."""
    from vulntriage.mail import delivery as delivery_mod
    from vulntriage.mail.message import HeaderInjectionError
    from vulntriage.mail.transport import MailConfigurationError, SenderNotVerifiedError

    owner = {"owner_name": _LEAK_OWNER_NAME, "owner_email": _LEAK_OWNER_EMAIL}
    if case == "ownerless":
        owner = {"owner_name": None, "owner_email": None}
    elif case == "owner_email_missing":
        owner = {"owner_name": _LEAK_OWNER_NAME, "owner_email": None}
    _seed_p1_asset(factory, **owner)
    _taint_advisory(factory)

    transport: object = RecordingTransport(VERIFIED_SENDER)
    if case == "no_target":
        with factory() as session:
            job = session.scalar(select(NotificationJob))
            job.lifecycle_id = None
            session.commit()
    elif case == "sender_not_verified":
        transport = _RaisingTransport(SenderNotVerifiedError("refused"))
    elif case == "header_injection":
        transport = _RaisingTransport(HeaderInjectionError("crlf"))
    elif case == "failed":
        transport = _RaisingTransport(RuntimeError("smtp down"))
    elif case == "mail_config":
        def _boom() -> object:
            raise MailConfigurationError("MAIL_SENDER is not set")

        monkeypatch.setattr(delivery_mod, "build_transport", _boom)
        return DeliveryWorker(factory, transport=None)
    return DeliveryWorker(factory, transport=transport)  # type: ignore[arg-type]


def _deliver_logs(records) -> list:  # type: ignore[no-untyped-def]
    return [
        lr.log_record
        for lr in records
        if (lr.log_record.attributes or {}).get("vt.event") == "notification.deliver"
        or lr.log_record.body == "notification.deliver"
    ]


_OUTCOME_CASES = [
    # (case, vt.outcome, vt.error.code, has a finding id)
    ("sent", "sent", None, True),
    ("failed", "failed", "send_failed", True),
    ("sender_not_verified", "held", "sender_not_verified", True),
    ("header_injection", "held", "header_injection", True),
    ("mail_config", "held", "mail_config", True),
    ("ownerless", "held", "ownerless", True),
    ("owner_email_missing", "held", "owner_email_missing", True),
    ("no_target", "held", "no_target", False),
]


@pytest.mark.parametrize("case,outcome,code,has_finding", _OUTCOME_CASES)
def test_every_outcome_emits_span_log_and_one_counter_in_the_job_trace(
    factory, monkeypatch, captured_spans, captured_logs, captured_counter,
    case, outcome, code, has_finding,
) -> None:  # type: ignore[no-untyped-def]
    worker = _deliver_case(factory, monkeypatch, case)
    job = _only_job(factory)
    expected_trace_id = job.traceparent.split("-")[1]
    stored_state, stored_code = None, None

    worker.deliver_pending()

    spans = [s for s in captured_spans() if s.name == "notification.deliver"]
    assert len(spans) == 1, f"{case}: expected one span, got {len(spans)}"
    span = spans[0]
    assert trace.format_trace_id(span.context.trace_id) == expected_trace_id
    assert span.parent is not None
    assert trace.format_span_id(span.parent.span_id) == job.traceparent.split("-")[2]
    assert span.attributes.get("vt.outcome") == outcome
    assert span.attributes.get("vt.error.code") == code
    assert ("vt.finding.id" in span.attributes) is has_finding

    logs = _deliver_logs(captured_logs())
    assert len(logs) == 1, f"{case}: expected one log, got {len(logs)}"
    record = logs[0]
    attrs = dict(record.attributes or {})
    assert attrs.get("vt.outcome") == outcome, attrs
    assert attrs.get("vt.error.code") == code, attrs
    assert ("vt.finding.id" in attrs) is has_finding, attrs
    assert attrs.get("vt.tier") == job.tier and attrs.get("vt.notification.kind") == job.kind
    # The journey join: equality with the stored traceparent's trace id.
    assert trace.format_trace_id(record.trace_id) == expected_trace_id

    assert captured_counter() == [
        ({"vt.notification.kind": job.kind, "vt.outcome": outcome}, 1)
    ], f"{case}: counter must increment once with kind and outcome labels only"

    # Allowlist leak check: no owner name/email, advisory text or URL anywhere.
    blob = repr((dict(span.attributes), attrs, captured_counter()))
    for secret in (_LEAK_OWNER_NAME, _LEAK_OWNER_EMAIL, "SECRETADVISORYTEXT", "evil.example"):
        assert secret not in blob, f"{case}: {secret} leaked into telemetry"

    # Job state and last_error_code are unchanged by telemetry (existing codes).
    with factory() as session:
        row = session.get(NotificationJob, job.id)
        stored_state, stored_code = row.state, row.last_error_code
    expected_state = {
        "sent": NotificationState.SENT.value,
        "failed": NotificationState.FAILED.value,
        "ownerless": NotificationState.HELD_OWNERLESS.value,
        "owner_email_missing": NotificationState.HELD_OWNER_EMAIL_MISSING.value,
    }.get(case, NotificationState.HELD_CONFIGURATION_ERROR.value)
    assert stored_state == expected_state
    expected_stored_code = {
        "sent": None,
        "failed": "send_failed",
        "ownerless": "held: ownerless",
        "owner_email_missing": "held: owner email missing",
    }.get(case, case)
    assert stored_code == expected_stored_code


@pytest.mark.parametrize("case", ["ownerless", "owner_email_missing", "no_target"])
def test_held_job_second_poll_emits_nothing_more(
    factory, monkeypatch, captured_spans, captured_logs, captured_counter, case
) -> None:  # type: ignore[no-untyped-def]
    worker = _deliver_case(factory, monkeypatch, case)
    worker.deliver_pending()
    first = (
        len([s for s in captured_spans() if s.name == "notification.deliver"]),
        len(_deliver_logs(captured_logs())),
        captured_counter(),
    )
    assert first[0] == 1 and first[1] == 1

    worker.deliver_pending()

    assert len([s for s in captured_spans() if s.name == "notification.deliver"]) == 1
    assert len(_deliver_logs(captured_logs())) == 1
    assert captured_counter() == first[2]


def test_pre_send_hold_with_empty_traceparent_emits_local_trace_and_does_not_raise(
    factory, monkeypatch, captured_spans, captured_logs, captured_counter
) -> None:  # type: ignore[no-untyped-def]
    worker = _deliver_case(factory, monkeypatch, "ownerless")
    with factory() as session:
        job = session.scalar(select(NotificationJob))
        job.traceparent = ""
        session.commit()

    worker.deliver_pending()

    spans = [s for s in captured_spans() if s.name == "notification.deliver"]
    assert len(spans) == 1
    assert spans[0].context.trace_id != 0
    assert spans[0].parent is None  # a fresh local root, not a crash
    logs = _deliver_logs(captured_logs())
    assert len(logs) == 1
    assert logs[0].trace_id == spans[0].context.trace_id
    assert [v for _, v in captured_counter()] == [1]


# -- #218: VT_DEMO_DEFECT=notify_no_fix (the deliberate US-15 bug) --------------


def _set_fixed_version(factory: sessionmaker[Session], value: str | None) -> None:
    with factory() as session:
        for finding in session.scalars(select(Finding)):
            finding.fixed_version = value
        session.commit()


def test_demo_defect_no_fix_finding_still_delivers_with_defect_on(
    factory, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    _seed_p1_asset(factory)
    _set_fixed_version(factory, None)
    monkeypatch.setenv("VT_DEMO_DEFECT", "notify_no_fix")
    monkeypatch.setenv("DEPLOYMENT_ENVIRONMENT", "dev")

    sink = RecordingTransport(VERIFIED_SENDER)
    assert _worker(factory, sink).deliver_pending() == 1
    assert "Fixed version: none" in sink.sent[0].body
    assert _only_job(factory).state == NotificationState.SENT.value


def test_demo_defect_finding_with_fixed_version_still_delivers(
    factory, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    _seed_p1_asset(factory)
    _set_fixed_version(factory, "9.9.9")
    monkeypatch.setenv("VT_DEMO_DEFECT", "notify_no_fix")
    monkeypatch.setenv("DEPLOYMENT_ENVIRONMENT", "dev")

    sink = RecordingTransport(VERIFIED_SENDER)
    assert _worker(factory, sink).deliver_pending() == 1
    assert len(sink.sent) == 1
    assert _only_job(factory).state == NotificationState.SENT.value


def test_demo_defect_unset_no_fix_finding_still_delivers(
    factory, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    """The tests that miss the bug: a no-fix finding with the variable unset."""
    _seed_p1_asset(factory)
    _set_fixed_version(factory, None)
    monkeypatch.delenv("VT_DEMO_DEFECT", raising=False)

    sink = RecordingTransport(VERIFIED_SENDER)
    assert _worker(factory, sink).deliver_pending() == 1
    assert "Fixed version: none" in sink.sent[0].body
    assert _only_job(factory).state == NotificationState.SENT.value
