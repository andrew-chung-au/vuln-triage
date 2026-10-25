"""The telemetry Compose job (#157, task 25): the `T-REFUSE` case.

Runs under ``make test-compose JOB=telemetry`` against the running observability
stack (Collector -> Prometheus/Tempo/Loki). Marked ``compose`` and DESELECTED by
``make test`` / ``make verify`` (the default ``-m "not compose"``), so it never
runs — and never *skips* — in the no-Docker gate. A missing service is a hard
failure here, never a silent skip (``_docs/testing.md`` Telemetry: "A missing
required service fails the job").

Cases (built across #157 and #172):
- ``T-REFUSE`` (#157): a host-side driver emits an app-helper span/log AND a
  raw-OpenTelemetry span through the Collector; the test confirms the Collector
  drops the excluded attributes (keys absent in Tempo, values absent in Loki)
  while an allowlisted key survives — so a broken Collector config fails it.
- ``T-JOURNEY-BE`` (#172 PR 2): drive one scan→notification journey through the
  *deployed backend container* (login + ``POST /assets`` over the published
  port, ``VT_FEEDS=fixtures``). Assert the submission span list shares one trace
  id in Tempo, the ``vt_notifications_total`` metric and the JSON log carry that
  id, and the owner email reaches MailHog.
- ``I-OWNER-NOAWS`` / ``I-OWNER-SENDER`` MailHog forms (#172 PR 2): the container
  delivers to MailHog with no AWS credential; a verified-sender mismatch is
  refused by the backend's own guard and nothing is delivered.

All are marked ``compose`` and DESELECTED by ``make test`` / ``make verify``
(the default ``-m "not compose"``), so they never run — and never *skip* — in
the no-Docker gate. A missing service is a hard failure here, never a silent
skip. The harness (``ci/test-compose.sh``) brings up the app + observability
stacks under one project and seeds the login-able security-lead user inside the
backend container (task 9's ``create-user``, #176).
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
    backend_login,
    backend_register_asset,
    mailhog_messages,
    mailhog_recipients,
    span_attribute_keys,
    span_names,
    wait_for_backend_health,
    wait_for_log_entry,
    wait_for_mail,
    wait_for_metric,
    wait_for_trace,
    wait_for_trace_spans,
    wait_for_trace_with_span,
)

# The security-lead user the harness seeded in-container, and the pygoat asset
# whose KEV-listed dependency ranks P1 (exposed: internetFacing + high).
_USERNAME = os.environ.get("VT_TEST_USERNAME", "telemetry-lead")
_PASSWORD = os.environ.get("VT_TEST_PASSWORD", "telemetry-not-a-secret")
_PYGOAT_ASSET = {
    "name": "pygoat",
    "ownerName": "Owner",
    "ownerEmail": "owner@team.example",
    "criticality": "high",
    "internetFacing": True,
    "repositoryUrl": "https://github.com/adeyosemanputra/pygoat",
}
# The submission backend span list for T-JOURNEY-BE (brief.generate is future development,
# not asserted).
_JOURNEY_SPANS = {
    "scan.run", "repository.read", "osv.query", "signals.enrich",
    "prioritise", "notification.enqueue", "notification.deliver",
}

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
    # Visible in the CI log: which excluded keys the helper path actually sent to
    # the Collector (empty normally; non-empty if the code allowlist is widened).
    # Makes a green result read as "the Collector stripped it", not "never sent".
    print(f"T-REFUSE: helper path sent excluded keys to Collector: "
          f"{result.get('helper_sent_excluded_keys')}")

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


# -- T-JOURNEY-BE (the full scan->notification journey, one trace id) ----------


def test_t_journey_be_one_trace_across_metric_trace_log_and_mailhog() -> None:
    """US-13: one scan->notification journey, one trace id in metric/trace/log.

    Drives the real backend container (login + POST /assets, VT_FEEDS=fixtures),
    then asserts: the submission span list shares one trace id in Tempo; the
    vt_notifications_total metric exists; a JSON log carries that trace id; and
    the owner email reached MailHog.
    """
    assert wait_for_backend_health(), "backend container did not become healthy"
    mail_before = len(mailhog_messages())

    cookie = backend_login(_USERNAME, _PASSWORD)
    asset = backend_register_asset(cookie, _PYGOAT_ASSET)
    print(f"T-JOURNEY-BE: registered asset {asset.get('id')!r}; driving the journey")

    # The scan runs in the container; find the JOURNEY trace by a span unique to
    # it — notification.enqueue (the T-REFUSE driver also emits a scan.run, so
    # searching scan.run can match the wrong trace). notification.enqueue is
    # produced only by create_top_tier_jobs for a real P1 finding.
    trace_id = wait_for_trace_with_span("notification.enqueue")
    assert len(trace_id) == 32 and int(trace_id, 16) != 0
    print(f"T-JOURNEY-BE: journey trace id {trace_id}")

    # Tempo: wait until the trace carries the full submission backend span list
    # (notification.deliver lands when the DeliveryWorker next polls, ~30s).
    trace = wait_for_trace_spans(trace_id, _JOURNEY_SPANS)
    names = span_names(trace)
    # The only identifying labels on the deliver span are finding id and tier.
    keys = span_attribute_keys(trace)
    assert "vt.finding.id" in keys and "vt.tier" in keys, keys

    # Metric: a sent top-tier notification is counted (same journey).
    wait_for_metric('vt_notifications_total{vt_outcome="sent"}')

    # Log: a JSON log line carries the same trace id (the journey join).
    lines = wait_for_log_entry('{service_name="vulntriage-backend"}', trace_id)
    assert lines, "no Loki log entry carried the journey trace id"

    # Delivery: the owner email reached MailHog (the container delivered it).
    messages = wait_for_mail(mail_before + 1)
    assert "owner@team.example" in mailhog_recipients(messages), mailhog_recipients(messages)


# -- I-OWNER-NOAWS (MailHog form): the container delivers with no AWS cred ------


def test_i_owner_noaws_container_delivers_to_mailhog() -> None:
    """The deployed container (no AWS credential) delivers the owner email.

    Reuses the journey: if T-JOURNEY-BE's registration already delivered, this
    confirms MailHog holds a message addressed to the owner. The container runs
    with MAIL_TRANSPORT=mailhog and no AWS credential in its environment, so a
    delivered message proves the no-AWS path.
    """
    assert wait_for_backend_health(), "backend container did not become healthy"
    # Ensure a journey has run (idempotent: a second POST /assets for the same
    # asset is rejected, so rely on the delivered mail being present).
    messages = wait_for_mail(1)
    assert "owner@team.example" in mailhog_recipients(messages), (
        f"no owner email at MailHog: {mailhog_recipients(messages)}"
    )


# -- I-OWNER-SENDER (MailHog form) is NOT here --------------------------------
# The honest container-level form requires the backend to attempt a send whose
# From is not the configured verified sender — but the backend always sends
# From = MAIL_SENDER, so there is no product path to trigger the mismatch at
# container level, and a test-constructed wrong-From send would test the
# transport class in isolation, not the deployed guard (the same hollowness
# #157 avoided). The verified-sender refusal is covered by the unit case
# tests/test_notifications.py::test_i_owner_sender_* (the backend's own guard,
# under make test). The MailHog form is deferred to PR 3 / #159, where the demo
# defect (task 28) gives a real in-container path that exercises a held/refused
# delivery. Recorded in _docs/testing.md.