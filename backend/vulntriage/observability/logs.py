"""JSON-lines structured logging + OTLP log export (task 23 / #174).

``log_event`` does two things with one call:

1. Writes one JSON line to stdout: ``{event, trace_id, span_id, ...allowlisted}``
   (unchanged; the container's stdout stays human- and grep-friendly).
2. Emits an OpenTelemetry **log record** so the log reaches the Collector over
   OTLP and then Loki, joining the US-13 journey by trace id. This is the leg
   task 23 intended (``_docs/architecture.md`` § Observability: the Collector
   "Receives OTLP from the backend"; `_docs/tasks.md` task 23: one trace, metric
   and log with a shared trace ID) but that the original implementation left out
   — it only wrote stdout, so nothing reached Loki (#174).

Log bodies are event names only, and every extra field is passed through the
allowlist first, so advisory text, owner details, URLs, SQL or credentials can
never be written — on either the stdout line or the exported record.

A40: the OTLP log exporter is attached only when a Collector endpoint is set;
with no endpoint the log provider has no exporter (export is a no-op), exactly
like tracing/metrics, so ``make test`` needs no Collector. The export uses the
OTel ``LoggingHandler`` bridge on a dedicated stdlib logger, which reads the
current span context for trace correlation automatically.
"""

from __future__ import annotations

import json
import logging
import sys
from collections.abc import Mapping
from typing import Any, TextIO

from opentelemetry import trace

from vulntriage.observability import settings
from vulntriage.observability.allowlist import filter_attributes
from vulntriage.observability.tracing import build_resource

# A dedicated stdlib logger that carries the OTel export handler. It does not
# propagate to the root logger, so it never doubles up with app logging config.
_OTEL_LOGGER_NAME = "vulntriage.telemetry"
_otel_logger = logging.getLogger(_OTEL_LOGGER_NAME)
_otel_logger.setLevel(logging.INFO)
_otel_logger.propagate = False

_logging_installed = False
_logger_provider = None


def setup_logging() -> None:
    """Install the OTLP log pipeline once (A40 no-op without a Collector).

    Mirrors ``setup_tracing``/``setup_metrics``: builds a ``LoggerProvider`` on
    the shared resource, attaches an OTLP log exporter only when a Collector
    endpoint is configured, and bridges the dedicated stdlib logger to it with
    the OTel ``LoggingHandler``. Idempotent and safe to call when no endpoint is
    set (the provider simply has no exporter, so emitting is a no-op export).
    """
    global _logging_installed, _logger_provider
    if _logging_installed:
        return

    from opentelemetry._logs import set_logger_provider
    from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
    from opentelemetry.sdk._logs.export import BatchLogRecordProcessor

    provider = LoggerProvider(resource=build_resource())
    endpoint = settings.get_otlp_endpoint()
    if endpoint is not None:
        # Imported lazily so the no-Collector path (tests, local dev) never
        # needs the gRPC exporter at import time, exactly like the span exporter.
        from opentelemetry.exporter.otlp.proto.grpc._log_exporter import (
            OTLPLogExporter,
        )

        provider.add_log_record_processor(
            BatchLogRecordProcessor(OTLPLogExporter(endpoint=endpoint))
        )

    set_logger_provider(provider)
    handler = LoggingHandler(level=logging.NOTSET, logger_provider=provider)
    _otel_logger.addHandler(handler)
    _logger_provider = provider
    _logging_installed = True


def log_event(event: str, attributes: Mapping[str, Any] | None = None, *, stream: TextIO | None = None) -> None:
    """Write one JSON line and emit one OTLP log record: ``{event, trace_id, span_id, ...allowlisted}``.

    ``event`` is a short machine name (e.g. ``"scan.finished"``). ``attributes``
    are filtered through the allowlist, so a caller cannot leak a non-allowlisted
    field on either output. ``trace_id``/``span_id`` come from the current span
    context, joining the log to the trace; the OTLP record's trace correlation is
    set by the ``LoggingHandler`` from the same active span.
    """
    allowed = filter_attributes(attributes or {})
    ctx = trace.get_current_span().get_span_context()
    record: dict[str, Any] = {
        "event": event,
        "trace_id": trace.format_trace_id(ctx.trace_id),
        "span_id": trace.format_span_id(ctx.span_id),
    }
    record.update(allowed)
    out = stream if stream is not None else sys.stdout
    out.write(json.dumps(record, separators=(",", ":"), sort_keys=True) + "\n")

    # Emit the OTLP log record too (A40: a no-op export when no Collector). The
    # handler reads the active span for trace correlation; the body is the event
    # name and the extra fields are the already-allowlisted attributes.
    if not _logging_installed:
        setup_logging()
    _otel_logger.info(event, extra={"vt.event": event, **allowed})
