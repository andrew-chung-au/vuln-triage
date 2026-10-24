"""Drive the backend telemetry exclusion path for the telemetry Compose job (#157).

Run as a module from ``ci/test-compose.sh`` *inside the backend venv* with the
OTLP endpoint pointing at the running Collector, so the backend's real tracing
and logging helpers export a span and a log through the Collector. ``T-REFUSE``
then confirms the Collector drops the excluded attributes.

Scope (Option C narrowing, human decision 2026-10-24): #157 ships only the
``refuse`` command. The delivery-dependent cases (the MailHog forms of
``I-OWNER-NOAWS`` / ``I-OWNER-SENDER``, ``T-E6``, ``T-DELIVER-TRACE`` and the
full ``T-JOURNEY-BE``) require the *deployed backend container* to deliver — a
host process delivering would not prove the container has no AWS credential, and
the ``I-OWNER-SENDER`` refusal must come from the backend's own guard, not a
direct ``transport.send`` in the test. That containerized-backend-delivers
harness is built with prerequisite #172, which carries those cases.

This module imports the backend observability helpers only (no test stubs, no
delivery), so it has no feed/DB dependency. It is NOT a pytest module (no
``test_`` functions), so ``make test`` never collects it; it is support code for
the compose harness.

VERIFY (settled by the human on the running stack): that OTLP export over the
published Collector port (localhost:4317 gRPC) works from a host process.
"""

from __future__ import annotations

import datetime as dt
import json
import sys

from opentelemetry import trace

from vulntriage.observability.logs import log_event
from vulntriage.observability.metrics import setup_metrics
from vulntriage.observability.tracing import (
    current_trace_id_hex,
    set_span_attributes,
    setup_tracing,
    span,
)


def _result(data: dict) -> None:
    """Print one JSON line the pytest cases parse from stdout."""
    sys.stdout.write("VT_DRIVER_RESULT " + json.dumps(data, sort_keys=True) + "\n")
    sys.stdout.flush()


def cmd_refuse() -> int:
    """Emit spans and a log carrying excluded attributes, for T-REFUSE.

    Two drops are exercised, in one trace:

    1. The *code-level* allowlist: the app's ``span``/``log_event`` helpers run
       ``filter_attributes`` before export, so a helper span/log never carries
       an excluded attribute in the first place.
    2. The *Collector* drop (the second line of defence): a span set through the
       RAW OpenTelemetry API bypasses the helper, so the excluded attributes DO
       leave the SDK and reach the Collector, which must strip them before
       Tempo. Without this raw span a broken Collector config would still pass,
       because the helper would have dropped everything in code first.

    Both spans carry the allowlisted ``vt.scan.id`` (the marker) so the test can
    confirm the spans were exported at all (the drop is selective, not total).
    The providers are force-flushed so the signals reach the Collector before
    the test queries Tempo/Loki.
    """
    setup_tracing()
    setup_metrics()
    marker = "vt-refuse-" + dt.datetime.now(dt.UTC).strftime("%Y%m%d%H%M%S%f")
    excluded = {
        "owner.email": f"{marker}@secret.example",
        "authorization": f"Bearer {marker}-token",
        "url.full": f"https://github.com/acme/private-{marker}/contents/uv.lock",
        "db.statement": f"SELECT * FROM findings -- {marker}",
    }
    tracer = trace.get_tracer("vulntriage-compose-test")
    # Root span via the app helper (code-level allowlist path).
    with span("scan.run", {"vt.scan.id": marker}) as current:
        set_span_attributes(current, excluded)  # filtered in code -> dropped
        trace_id = current_trace_id_hex()
        # A CHILD span set through the raw API: the excluded attributes bypass
        # the code allowlist and go to the Collector, which must strip them.
        with tracer.start_as_current_span("scan.refuse.raw") as raw:
            raw.set_attribute("vt.scan.id", marker)  # allowlisted, should survive
            for key, value in excluded.items():
                raw.set_attribute(key, value)  # excluded, Collector must drop
        # The log helper filters in code; pass excluded keys to prove the drop.
        log_event("scan.run", {**excluded, "vt.scan.id": marker})
    _flush_providers()
    _result({"cmd": "refuse", "marker": marker, "trace_id": trace_id})
    return 0


def _flush_providers() -> None:
    """Force-flush the tracer and meter providers so exports reach the Collector.

    The subprocess also flushes on exit, but an explicit flush makes the signals
    available before the test's Tempo/Loki polls start (bounded, not relied on).
    """
    tracer_provider = trace.get_tracer_provider()
    force_flush = getattr(tracer_provider, "force_flush", None)
    if callable(force_flush):
        force_flush()
    from opentelemetry import metrics

    meter_provider = metrics.get_meter_provider()
    mp_flush = getattr(meter_provider, "force_flush", None)
    if callable(mp_flush):
        mp_flush()


_COMMANDS = {"refuse": cmd_refuse}


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in _COMMANDS:
        sys.stderr.write(f"usage: python -m compose_driver <{'|'.join(_COMMANDS)}>\n")
        return 2
    return _COMMANDS[argv[1]]()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
