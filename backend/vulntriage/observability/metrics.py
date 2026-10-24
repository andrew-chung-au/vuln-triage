"""The US-13 metrics (task 23).

A MeterProvider parallel to the tracer: an OTLP metric exporter only when a
Collector endpoint is set (A40), else no reader. The three metrics:

- ``vt_notifications_total{kind,outcome}`` — counter, delivery outcomes.
- ``vt_notification_delivery_seconds`` — histogram, delivery latency.
- ``vt_top_tier_notification_overdue{finding_id,tier}`` — gauge, 0/1, set from
  stored job state; plus a constant global ``0`` heartbeat series with no
  ``finding_id``/``tier`` so the metric exists on a fresh system (US-14 rule).

The gauge's per-finding values and the alert rule itself are task 26; this
module defines the instruments and the heartbeat so task 23's metrics "exist".
"""

from __future__ import annotations

from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

from vulntriage.observability import settings
from vulntriage.observability.tracing import build_resource

_METER_SCOPE = "vulntriage"
_provider_installed = False

notifications_total = None
notification_delivery_seconds = None
_overdue_gauge = None


def setup_metrics() -> None:
    """Install the global MeterProvider and create the instruments once."""
    global _provider_installed, notifications_total, notification_delivery_seconds, _overdue_gauge
    if _provider_installed:
        return

    readers = []
    endpoint = settings.get_otlp_endpoint()
    if endpoint is not None:
        from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
            OTLPMetricExporter,
        )

        readers.append(PeriodicExportingMetricReader(OTLPMetricExporter(endpoint=endpoint)))

    provider = MeterProvider(resource=build_resource(), metric_readers=readers)
    metrics.set_meter_provider(provider)
    meter = metrics.get_meter(_METER_SCOPE)

    notifications_total = meter.create_counter(
        "vt_notifications_total",
        description="Owner-notification delivery outcomes by kind and outcome.",
    )
    notification_delivery_seconds = meter.create_histogram(
        "vt_notification_delivery_seconds",
        unit="s",
        description="Owner-notification delivery latency in seconds.",
    )

    # The overdue gauge is observable (read from stored job state in task 26).
    # Here it emits only the constant global 0 heartbeat so the metric exists on
    # a fresh system with no jobs (the US-14 NoData rule depends on this).
    def _observe_overdue(options):  # type: ignore[no-untyped-def]
        from opentelemetry.metrics import Observation

        return [Observation(0)]

    _overdue_gauge = meter.create_observable_gauge(
        "vt_top_tier_notification_overdue",
        callbacks=[_observe_overdue],
        description="1 while a top-tier owner notification is overdue; 0 otherwise. "
        "The label-less series is a constant 0 heartbeat.",
    )
    _provider_installed = True
