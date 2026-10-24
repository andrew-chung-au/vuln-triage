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
    """Emit one span and one log carrying excluded attributes, for T-REFUSE.

    The in-code allowlist already drops them; this exercises the Collector's
    second-line drop. The excluded values are passed through the real span/log
    helpers so the exported signals can be checked to contain none of them. The
    span also carries one allowlisted key (``vt.scan.id``) so the test can
    confirm the span was exported at all (the drop is selective, not total).
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
    with span("scan.run", {"vt.scan.id": marker}) as current:
        set_span_attributes(current, excluded)
        trace_id = current_trace_id_hex()
        # The log helper filters in code; pass excluded keys to prove the drop.
        log_event("scan.run", {**excluded, "vt.scan.id": marker})
    _result({"cmd": "refuse", "marker": marker, "trace_id": trace_id})
    return 0


_COMMANDS = {"refuse": cmd_refuse}


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in _COMMANDS:
        sys.stderr.write(f"usage: python -m compose_driver <{'|'.join(_COMMANDS)}>\n")
        return 2
    return _COMMANDS[argv[1]]()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
