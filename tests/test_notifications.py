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
        advisory = session.scalar(
            select(Advisory).where(Advisory.vulnerability_id == finding.vulnerability_id)
        )
        assert advisory is not None
        advisory.summary = "Exploit at https://evil.example/x and www.evil.example"
        session.commit()

    sink = RecordingTransport(VERIFIED_SENDER)
    _worker(factory, sink).deliver_pending()
    body = sink.sent[0].body
    assert "https://" not in body
    assert "hxxps[:]//evil[.]example/x" in body
    assert "www[.]evil[.]example" in body
