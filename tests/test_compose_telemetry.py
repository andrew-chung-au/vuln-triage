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

``T-REFUSE`` drives ``tests/compose_driver.py`` (a subprocess in the backend
venv so its OTLP export reaches the Collector). The driver emits, in one trace,
both an app-helper span/log (the code-level allowlist drops excluded attributes
before export) AND a raw-OpenTelemetry-API span that bypasses the helper so the
excluded attributes actually reach the Collector — which must strip them. The
test then confirms Tempo holds none of the excluded keys (so a broken Collector
config fails it, not just the code path) and Loki holds none of the excluded
values, while the allowlisted ``vt.scan.id`` survives.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

# The driver runs as `python -m compose_driver` in a subprocess, which does not
# inherit pytest's sys.path. It needs two dirs on PYTHONPATH:
#   tests/   — to import compose_driver itself (this file's own directory);
#   backend/ — to import vulntriage (the backend is not pip-installed;
#              `package = false`, so pytest resolves it via `pythonpath = ["."]`
#              relative to backend/, which the child does not inherit).
_TESTS_DIR = pathlib.Path(__file__).resolve().parent
_REPO_ROOT = _TESTS_DIR.parent
_DRIVER_PATH_DIRS = [str(_TESTS_DIR), str(_REPO_ROOT / "backend")]

from compose_telemetry import (
    ComposeQueryError,
    span_attribute_keys,
    wait_for_log_entry,
    wait_for_trace,
)

# Loki labels OTLP-ingested logs with the service name (service.name resource
# attribute -> service_name label on Loki 3.x). The harness sets
# OTEL_SERVICE_NAME=vulntriage-backend, so this selects the backend's logs.
# VERIFY: the service_name label mapping on the pinned Loki 3.2.1 image.
_LOKI_SELECTOR = '{service_name="vulntriage-backend"}'

pytestmark = pytest.mark.compose

# Attribute values that must never appear in any exported signal (T-REFUSE).
_EXCLUDED_MARKERS = ("secret.example", "Bearer", "private-", "SELECT *")


def _run_driver(command: str) -> dict:
    """Run tests/compose_driver.py <command> and return its result JSON.

    The harness sets the backend venv and OTLP endpoint in the environment; this
    inherits them, and prepends the tests dir and backend dir to PYTHONPATH so
    the subprocess can import compose_driver and vulntriage (it does not inherit
    pytest's sys.path). A non-JSON or failing run is a hard error (never a skip).
    """
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    parts = [*_DRIVER_PATH_DIRS, existing] if existing else list(_DRIVER_PATH_DIRS)
    env["PYTHONPATH"] = os.pathsep.join(parts)
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
    # None of the excluded keys survive to Tempo. This covers BOTH spans the
    # driver emits in this trace: the app-helper span (code-level allowlist) and
    # the raw-API span whose excluded attributes are dropped only by the
    # Collector — so a broken Collector config would fail this assertion.
    for forbidden in ("owner.email", "authorization", "url.full", "db.statement"):
        assert forbidden not in keys, f"{forbidden} leaked to Tempo: {keys}"
    # The allowlisted vt.scan.id key does survive (the spans were exported, so
    # the drop is selective — the Collector did not simply drop whole spans).
    assert any(k in keys for k in ("vt.scan.id", "vt.scan.status")), keys

    # Logs: poll until this run's log entry reaches Loki (the raw log record the
    # driver emits carries the marker as vt.scan.id in structured metadata; the
    # body is the event name only). Polling means slow ingestion cannot let the
    # check pass without inspecting anything. Then assert no excluded VALUE
    # appears in any entry's line or metadata — the Collector must have stripped
    # the excluded attributes from the raw log record, so a broken Collector log
    # config leaks them here.
    entries = wait_for_log_entry(_LOKI_SELECTOR, marker)
    assert entries, "no Loki log entry carried this run's marker"
    for line, meta in entries:
        haystack = line + " " + " ".join(f"{k}={v}" for k, v in meta.items())
        for banned in _EXCLUDED_MARKERS:
            assert banned not in haystack, f"excluded value {banned!r} leaked to Loki: {line} / {meta}"
    # The excluded attribute KEYS must also be absent from the metadata (the
    # Collector's keep_keys drop on the log pipeline).
    all_meta_keys = {k for _line, meta in entries for k in meta}
    for forbidden_key in ("owner.email", "authorization", "url.full", "db.statement"):
        assert forbidden_key not in all_meta_keys, f"{forbidden_key} leaked to Loki metadata: {all_meta_keys}"
