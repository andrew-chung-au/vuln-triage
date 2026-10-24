"""Tracing: the SDK provider, the project tracer, a span helper that enforces
the allowlist, and the W3C traceparent of the current span.

A40: the SDK is always on and always creates real, valid span contexts. An OTLP
exporter is attached only when a Collector endpoint is configured; otherwise
export is a no-op but span contexts are still valid, so a job's stored
``traceparent`` is a valid non-zero W3C value in every configuration,
``make test`` included.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from typing import Any

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Span

from vulntriage.observability.allowlist import filter_attributes
from vulntriage.observability import settings

_INSTRUMENTATION_SCOPE = "vulntriage"
_provider_installed = False


def build_resource() -> Resource:
    """The telemetry resource: service name, version and environment (A32 keys)."""
    return Resource.create(
        {
            "service.name": settings.get_service_name(),
            "service.version": settings.get_service_version(),
            "deployment.environment": settings.get_deployment_environment(),
        }
    )


def setup_tracing() -> None:
    """Install the global TracerProvider once.

    Attaches an OTLP span exporter only when a Collector endpoint is set; with
    no endpoint the provider has no exporter (export is a no-op), but it still
    creates real span contexts (A40). Idempotent.
    """
    global _provider_installed
    if _provider_installed:
        return

    provider = TracerProvider(resource=build_resource())
    endpoint = settings.get_otlp_endpoint()
    if endpoint is not None:
        # Imported lazily so the no-Collector path (tests, local dev) never
        # needs the gRPC exporter at import time.
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )

        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))

    trace.set_tracer_provider(provider)
    _provider_installed = True


def get_tracer() -> trace.Tracer:
    # Ensure a real SDK provider is installed even when the app factory did not
    # run (e.g. ingest tests that call run_scan directly), so spans always have
    # real, non-zero contexts (A40) rather than the API's no-op default.
    if not _provider_installed:
        setup_tracing()
    return trace.get_tracer(_INSTRUMENTATION_SCOPE)


@contextmanager
def span(name: str, attributes: Mapping[str, Any] | None = None) -> Iterator[Span]:
    """Start a span whose attributes are filtered through the allowlist.

    Use this instead of the raw tracer so no un-allowlisted attribute can be set
    at span start. Add later attributes with :func:`set_span_attributes`.
    """
    attrs = filter_attributes(attributes or {})
    with get_tracer().start_as_current_span(name, attributes=attrs) as current:
        yield current


@contextmanager
def span_from_traceparent(
    name: str, traceparent: str, attributes: Mapping[str, Any] | None = None
) -> Iterator[Span]:
    """Start ``name`` as a child of a stored W3C ``traceparent`` (task 37).

    The backend's ``notification.deliver`` span must join the trace of the
    ``notification.enqueue`` span whose ``traceparent`` was stored on the job
    (task 23), so the US-13 journey shares one trace id across the enqueue and
    the later delivery. Extracts a remote parent context from the stored string
    with the W3C trace-context propagator, then starts the span inside it.

    Attributes are filtered through the allowlist, exactly like :func:`span`, so
    no owner contact detail, advisory text or URL can be set on the span. The
    context manager also makes it the current span for its scope.
    """
    # Imported here (not at module import) to keep the propagator out of the
    # import graph of modules that never cross a stored traceparent.
    from opentelemetry.context import attach, detach
    from opentelemetry.trace.propagation.tracecontext import (
        TraceContextTextMapPropagator,
    )

    parent = TraceContextTextMapPropagator().extract({"traceparent": traceparent})
    attrs = filter_attributes(attributes or {})
    token = attach(parent)
    try:
        with get_tracer().start_as_current_span(name, attributes=attrs) as current:
            yield current
    finally:
        detach(token)


def set_span_attributes(current: Span, attributes: Mapping[str, Any]) -> None:
    """Set attributes on ``current``, dropping any not on the allowlist."""
    for key, value in filter_attributes(attributes).items():
        current.set_attribute(key, value)


def current_traceparent() -> str:
    """The W3C ``traceparent`` of the current span context.

    Format ``00-<32hex trace>-<16hex span>-<2hex flags>``. Valid and non-zero
    whenever called inside a span (A40), so it can be stored on a NotificationJob
    as the ``notification.enqueue`` context.
    """
    ctx = trace.get_current_span().get_span_context()
    flags = "01" if ctx.trace_flags.sampled else "00"
    return f"00-{trace.format_trace_id(ctx.trace_id)}-{trace.format_span_id(ctx.span_id)}-{flags}"


def current_trace_id_hex() -> str:
    """The 32-hex trace id of the current span context (for the Scan.trace_id column)."""
    ctx = trace.get_current_span().get_span_context()
    return trace.format_trace_id(ctx.trace_id)
