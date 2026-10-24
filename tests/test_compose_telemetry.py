"""The telemetry Compose job (#157, task 25): the `T-REFUSE` case.

Runs under ``make test-compose JOB=telemetry`` against the running observability
stack (Collector -> Prometheus/Tempo/Loki). Marked ``compose`` and DESELECTED by
``make test`` / ``make verify`` (the default ``-m "not compose"``), so it never
runs — and never *skips* — in the no-Docker gate. A missing service is a hard
failure here, never a silent skip (``_docs/testing.md`` Telemetry: "A missing
required service fails the job").

Scope (Option C narrowing, human decision 2026-10-24): #157 ships only
``T-REFUSE`` plus the ``make test-compose`` ``JOB`` selector. The
delivery-dependent cases — the MailHog forms of ``I-OWNER-NOAWS`` /
``I-OWNER-SENDER``, ``T-E6``, ``T-DELIVER-TRACE`` and the full ``T-JOURNEY-BE`` —
need the *deployed backend container* to deliver (a host process delivering
would not prove the container has no AWS credential; the ``I-OWNER-SENDER``
refusal must come from the backend's guard). That containerized-backend-delivers
harness is built with prerequisite #172, which carries those cases. See the
``telemetry`` job-table row in ``_docs/testing.md``.

``T-REFUSE`` drives the backend's real span/log helpers through
``tests/compose_driver.py`` (run as a subprocess in the backend venv so its OTLP
export reaches the Collector), then confirms Tempo (and Loki) hold none of the
excluded attribute keys or values.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

# The directory holding compose_driver.py (this file's own directory). The
# driver is run as `python -m compose_driver` in a subprocess, which does not
# inherit pytest's sys.path, so this dir is put on the child's PYTHONPATH.
_TESTS_DIR = str(pathlib.Path(__file__).resolve().parent)

from compose_telemetry import (
    ComposeQueryError,
    loki_lines,
    span_attribute_keys,
    wait_for_trace,
)

pytestmark = pytest.mark.compose

# Attribute values that must never appear in any exported signal (T-REFUSE).
_EXCLUDED_MARKERS = ("secret.example", "Bearer", "private-", "SELECT *")


def _run_driver(command: str) -> dict:
    """Run tests/compose_driver.py <command> and return its result JSON.

    The harness sets the backend venv and OTLP endpoint in the environment; this
    inherits them, and prepends the tests dir to PYTHONPATH so the subprocess
    can import compose_driver (it does not inherit pytest's sys.path). A non-JSON
    or failing run is a hard error (never a skip).
    """
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = _TESTS_DIR + (os.pathsep + existing if existing else "")
    proc = subprocess.run(
        [sys.executable, "-m", "compose_driver", command],
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )
    result = None
    for line in proc.stdout.splitlines():
        if line.startswith("VT_DRIVER_RESULT "):
            result = json.loads(line[len("VT_DRIVER_RESULT ") :])
    if result is None:
        raise ComposeQueryError(
            f"driver {command!r} printed no result (rc={proc.returncode})\n"
            f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    result["_rc"] = proc.returncode
    return result


def test_t_refuse_excluded_attributes_never_leave_the_collector() -> None:
    """Excluded span/log attributes are dropped before export (A32)."""
    result = _run_driver("refuse")
    assert result["_rc"] == 0, result
    trace_id = result["trace_id"]
    marker = result["marker"]
    assert len(trace_id) == 32 and int(trace_id, 16) != 0

    trace = wait_for_trace(trace_id)
    keys = span_attribute_keys(trace)
    # None of the excluded keys survive to Tempo.
    for forbidden in ("owner.email", "authorization", "url.full", "db.statement"):
        assert forbidden not in keys, f"{forbidden} leaked to Tempo: {keys}"
    # The allowlisted vt.scan.id key does survive (the span was exported, so the
    # drop is selective — it did not simply drop the whole span).
    assert any(k in keys for k in ("vt.scan.id", "vt.scan.status")), keys

    # And no excluded *value* appears in any log line for this marker. The LogQL
    # label selector that matches OTLP-ingested logs is VERIFY (it depends on how
    # Loki labels the Collector's OTLP export), so fetch broadly and filter by
    # the marker in Python.
    lines = loki_lines("{}")  # VERIFY: the stream selector for OTLP logs on 3.2.1
    for line in lines:
        if marker in line:
            for banned in _EXCLUDED_MARKERS:
                assert banned not in line, f"excluded value {banned!r} leaked to Loki: {line}"
