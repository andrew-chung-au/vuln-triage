"""P-DEMO-BE (task 28c-C, #233): the full stub loop in Compose, run twice.

Runs under ``make test-compose JOB=responder`` (``ci/test-compose.sh`` brings up the
app + observability + alert + responder stack under the ``vt-responder`` project and
runs this file after ``tests/test_compose_responder.py``). Marked ``compose`` and
DESELECTED by ``make test`` / ``make verify``.

THIS CASE WAS WRITTEN WITHOUT BEING RUN. The session that wrote it has the Docker CLI
but no Docker daemon, so none of it has been observed passing. Every external detail it
depends on is marked ``VERIFY:``. The owner runs it on a Docker host and records the
result and the measured duration in the PR.

WHAT THIS PROVES, PLAINLY: the STUB responder proves the WIRING only (real Grafana
alert -> real responder -> stub run -> logged events). It does not prove that an agent
fixed anything. There is no Git in this loop: the fix is applied BY THE HARNESS, which
unsets ``VT_DEMO_DEFECT`` and recreates the backend container.

The loop (take 1, each step read from a real sink, in order, each a bounded poll):
  1. the backend runs with ``VT_DEMO_DEFECT=notify_no_fix`` (``VT_FEEDS=fixtures``);
  2. registering ``fixture-owner/pip-app`` scans it; its flask 2.3.3 finding has no fixed
     version (the project-authored fixture added for #233) and ranks P1;
  3. the owner mail cannot be formatted, the job goes ``failed``, and
     ``vt_top_tier_notification_overdue`` reads 1 in Prometheus for that finding;
  4. exactly one human alert email reaches MailHog;
  5. the responder logs exactly one ``run_started`` for the alert's fingerprint and one
     ``pull_request_opened`` (the stub event) in ``docker compose logs responder``;
  6. a duplicate firing for the same fingerprint, with the right bearer, is ignored as a
     ``repeat`` and starts no second run (the refused case);
  7. the harness applies the fix: ``VT_DEMO_DEFECT`` unset, then
     ``up -d --force-recreate --no-deps backend`` (``docker compose restart`` does not
     re-read the environment);
  8. the delivery worker retries the job and the OWNER mail reaches MailHog;
  9. the metric reads 0, Grafana resolves the alert, and the ``resolved`` notification is
     observed at the responder as ``alert_ignored`` (outcome ``resolved``), with no new run.

Take 2 repeats it on the SAME finding id (same alert fingerprint). A second scan cannot
fail again (``owner_notified_at`` is stamped and the finding is unchanged), so the
harness turns the defect back on, then flips the finding's job back to ``failed`` through
the #159 seam (``manage.py alert-set``, ``compose_alert.set_job_state``). The delivery
worker retries any ``failed`` job without looking at ``owner_notified_at``
(``deliver_pending``), so the retry is picked up. Take 2 must start exactly one NEW run.
The guard record is read from the container to show the fingerprint was released
between the takes.

VERIFY (reported by the case, not assumed): that Grafana 11.3.0's webhook contact point
sends the ``resolved`` notification. ``us14-overdue.yaml`` does not set
``disableResolveMessage``, so the default (send) should apply. If no ``resolved`` arrives
the case FAILS and says so; the guard fix would then need the documented state-file-reset
fallback (#220, comment 6410222531).
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

import pytest

from compose_alert import (
    ALERT_HUMAN_EMAIL,
    clear_seed,
    mailhog_alert_messages,
    mailhog_reset,
    overdue_series,
    set_job_state,
    wait_for_webhook_health,
    webhook_recorded,
    webhook_reset,
)
from compose_responder import (
    WEBHOOK_TOKEN,
    backend_demo_defect,
    events,
    firing_body,
    guard_record,
    message_subject,
    post_webhook,
    recreate_backend,
    responder_log,
)
from compose_telemetry import (
    ComposeQueryError,
    _backend_request,
    _poll,
    backend_login,
    backend_register_asset,
    wait_for_backend_health,
)

pytestmark = pytest.mark.compose

# -- named timeouts (seconds). Each step is a bounded poll with its own name. --------
# Scan + the delivery worker's 30 s poll + the 60 s metric export + Prometheus scrape.
_T_FAIL_AND_METRIC = float(os.environ.get("VT_DEMO_FAIL_TIMEOUT", "300"))
# >= one 1-minute rule evaluation + the notification flush after the metric reads 1.
_T_ALERT_DELIVERED = float(os.environ.get("VT_DEMO_ALERT_TIMEOUT", "300"))
# Recreate, health, the worker's next 30 s poll, then the send to MailHog.
_T_OWNER_MAIL = float(os.environ.get("VT_DEMO_OWNER_MAIL_TIMEOUT", "240"))
# The metric export (60 s) + the rule evaluation (1 m) + the policy's group_interval (1 m),
# plus headroom. This is the longest wait of a take.
_T_RESOLVED = float(os.environ.get("VT_DEMO_RESOLVED_TIMEOUT", "480"))
_T_FINDING = 120.0
_SETTLE_S = 20.0  # bounded quiet period used to show "exactly one", not "at least one"

_USERNAME = os.environ.get("VT_TEST_USERNAME", "telemetry-lead")
_PASSWORD = os.environ.get("VT_TEST_PASSWORD", "telemetry-not-a-secret")
_OWNER_EMAIL = "pip-owner@team.example"
# fixture-owner/pip-app pins flask 2.3.3, which the #233 fixture advisory covers with an
# open-ended range, so the finding has no fixed version. Internet-facing: KEV listed and
# exposed ranks P1.
_PIP_APP_ASSET = {
    "name": "pip-app",
    "ownerName": "Owner",
    "ownerEmail": _OWNER_EMAIL,
    "criticality": "high",
    "internetFacing": True,
    "repositoryUrl": "https://github.com/fixture-owner/pip-app",
}
_BEARER = {"Authorization": f"Bearer {WEBHOOK_TOKEN}"}


def _wait(step: str, predicate, timeout_s: float):  # type: ignore[no-untyped-def]
    """A bounded poll that names the step and its timeout in the failure."""
    try:
        return _poll(predicate, timeout_s)
    except ComposeQueryError as exc:
        raise AssertionError(f"[{step}] {exc} (named timeout {timeout_s:.0f}s)") from exc


def _say(message: str) -> None:
    print(f"[P-DEMO-BE] {message}", flush=True)


def _since(baseline: int, name: str, **match: Any) -> list[dict[str, Any]]:
    """Responder log events named ``name`` after the first ``baseline`` log records."""
    records = responder_log()[baseline:]
    return [r for r in events(name, records) if all(r.get(k) == v for k, v in match.items())]


def _metric_is(finding_id: str, value: int) -> bool:
    """True when the finding's overdue series exist and ALL read exactly ``value``."""
    values = [str(s["value"][1]) for s in overdue_series(int(finding_id)) if s.get("value")]
    return bool(values) and all(float(v) == value for v in values)


def _human_firing_emails() -> list[dict[str, Any]]:
    """Human alert emails that are FIRING notices (a late [RESOLVED] mail is not one).

    VERIFY: Grafana 11.3.0's default email subject starts ``[FIRING:n]`` / ``[RESOLVED]``.
    """
    return [m for m in mailhog_alert_messages(ALERT_HUMAN_EMAIL) if "FIRING" in message_subject(m).upper()]


def _human_subjects() -> list[str]:
    return [message_subject(m) for m in mailhog_alert_messages(ALERT_HUMAN_EMAIL)]


def _owner_emails() -> list[dict[str, Any]]:
    return mailhog_alert_messages(_OWNER_EMAIL)


@pytest.fixture
def demo_stack():  # type: ignore[no-untyped-def]
    """Zero seeded jobs, an empty webhook sink and an empty MailHog; defect off afterwards."""
    assert WEBHOOK_TOKEN, "VT_RESPONDER_WEBHOOK_TOKEN is not exported (ci/test-compose.sh sets it)"
    assert wait_for_webhook_health(), "stub webhook sink did not become healthy"
    clear_seed()
    webhook_reset()
    mailhog_reset()
    yield
    try:
        recreate_backend(None)  # leave the backend as the other cases expect it
    except ComposeQueryError as exc:  # pragma: no cover (diagnostic only)
        _say(f"teardown: could not restore the backend with the defect off: {exc}")
    clear_seed()


def _register_and_find(cookie: str) -> dict[str, Any]:
    asset = backend_register_asset(cookie, _PIP_APP_ASSET)

    def _finding() -> dict[str, Any] | bool:
        status, _headers, body = _backend_request("GET", "/findings", cookie=cookie)
        if status != 200:
            raise ComposeQueryError(f"GET /findings returned {status}")
        for finding in json.loads(body):
            if str(finding.get("assetId")) == str(asset["id"]) and finding.get("package") == "flask":
                return finding
        return False

    return _wait("scan: the pip-app flask finding exists", _finding, _T_FINDING)


def _start_backend(defect: str | None) -> None:
    recreate_backend(defect)
    assert backend_demo_defect() == (defect or ""), (
        f"the backend container's VT_DEMO_DEFECT is {backend_demo_defect()!r}, expected {defect or ''!r}"
    )
    assert wait_for_backend_health(), "backend container did not become healthy after the recreate"


def _firing_phase(take: int, finding_id: str, baseline: int, expected_fp: str | None) -> str:
    """Steps 3 to 5 (and the settle check). Returns the alert fingerprint."""
    tag = f"take {take}"
    _wait(f"{tag}: job failed, overdue metric = 1 in Prometheus", lambda: _metric_is(finding_id, 1), _T_FAIL_AND_METRIC)
    _say(f"{tag}: vt_top_tier_notification_overdue{{finding_id={finding_id}}} = 1")

    _wait(f"{tag}: one human alert email (FIRING) at MailHog", lambda: _human_firing_emails() or False, _T_ALERT_DELIVERED)
    started = _wait(
        f"{tag}: responder run_started for the finding",
        lambda: next(iter(_since(baseline, "run_started", finding_id=finding_id)), False),
        _T_ALERT_DELIVERED,
    )
    fingerprint = started.get("fingerprint")
    assert isinstance(fingerprint, str) and fingerprint, f"{tag}: run_started carried no fingerprint: {started}"
    if expected_fp is not None:
        assert fingerprint == expected_fp, (
            f"{tag}: the fingerprint changed between takes ({expected_fp!r} then {fingerprint!r}); "
            "the case needs the SAME fingerprint"
        )
    _wait(
        f"{tag}: responder pull_request_opened (stub event) for the fingerprint",
        lambda: next(iter(_since(baseline, "pull_request_opened", fingerprint=fingerprint)), False),
        _T_ALERT_DELIVERED,
    )
    reads = _since(baseline, "api_read", fingerprint=fingerprint)
    assert reads and "failed" in (reads[-1].get("job_states") or []), (
        f"{tag}: the responder did not read a failed job through the API: {reads}"
    )
    assert fingerprint in guard_record(), f"{tag}: the guard record does not hold the fingerprint during the run"
    _say(f"{tag}: responder run_started + pull_request_opened (stub) for fingerprint {fingerprint}")
    return fingerprint


def _assert_exactly_one_before_fix(take: int, fingerprint: str, baseline: int) -> None:
    """After a bounded quiet period: exactly one human mail, one run, one stub PR."""
    time.sleep(_SETTLE_S)
    tag = f"take {take}"
    firing = _human_firing_emails()
    assert len(firing) == 1, f"{tag}: expected exactly one human alert email, got {_human_subjects()}"
    assert len(_since(baseline, "run_started", fingerprint=fingerprint)) == 1, f"{tag}: not exactly one run_started"
    assert len(_since(baseline, "pull_request_opened", fingerprint=fingerprint)) == 1, (
        f"{tag}: not exactly one pull_request_opened"
    )
    assert _owner_emails() == [], f"{tag}: an owner mail arrived while the defect was on"
    assert webhook_recorded() == [], f"{tag}: the webhook sink recorded a request (the alert must go to the responder)"
    _say(f"{tag}: exactly one human email, one run_started, one pull_request_opened; no owner mail yet")


def _assert_duplicate_firing_is_ignored(finding_id: str, fingerprint: str, baseline: int) -> None:
    """The refused case: a repeat firing for the same fingerprint, right bearer, starts no run."""
    runs_before = len(_since(baseline, "run_started", fingerprint=fingerprint))
    repeats_before = len(_since(baseline, "alert_ignored", fingerprint=fingerprint, outcome="repeat"))
    status, body = post_webhook(firing_body(fingerprint, finding_id), _BEARER)
    assert status == 200, f"the duplicate firing got {status}: {body[:300]!r}"
    _wait(
        "refused case: alert_ignored repeat logged",
        lambda: len(_since(baseline, "alert_ignored", fingerprint=fingerprint, outcome="repeat")) > repeats_before or False,
        60.0,
    )
    assert len(_since(baseline, "run_started", fingerprint=fingerprint)) == runs_before, (
        "refused case: the duplicate firing started a second run"
    )
    _say("refused case: the duplicate firing was ignored as a repeat and started no second run")


def _fix_phase(take: int, finding_id: str, fingerprint: str, baseline: int) -> None:
    """Steps 7 to 9: the harness applies the fix; owner mail, metric 0, alert resolved."""
    tag = f"take {take}"
    _start_backend(None)  # VT_DEMO_DEFECT unset + force-recreate (restart would keep the old env)
    _say(f"{tag}: fix applied by the harness (VT_DEMO_DEFECT unset, backend recreated; no Git, no agent)")

    _wait(f"{tag}: owner mail at MailHog", lambda: _owner_emails() or False, _T_OWNER_MAIL)
    _say(f"{tag}: owner mail delivered to {_OWNER_EMAIL}")
    _wait(f"{tag}: overdue metric = 0 in Prometheus", lambda: _metric_is(finding_id, 0), _T_FAIL_AND_METRIC)
    _say(f"{tag}: vt_top_tier_notification_overdue{{finding_id={finding_id}}} = 0")

    try:
        resolved = _wait(
            f"{tag}: the resolved notification reaches the responder (alert_ignored, outcome resolved)",
            lambda: next(iter(_since(baseline, "alert_ignored", fingerprint=fingerprint, outcome="resolved")), False),
            _T_RESOLVED,
        )
    except AssertionError as exc:
        raise AssertionError(
            f"{exc}. VERIFY failed: the Grafana 11.3.0 webhook contact point did NOT send a 'resolved' "
            "notification (or it did not reach the responder). The guard fix then needs the documented "
            "state-file-reset fallback (#220, comment 6410222531)."
        ) from exc
    _say(
        f"{tag}: VERIFY result: the Grafana contact point DID send 'resolved' "
        f"(responder logged alert_ignored/resolved for {fingerprint}: {resolved})"
    )

    time.sleep(_SETTLE_S)
    assert len(_owner_emails()) == 1, f"{tag}: expected exactly one owner mail, got {len(_owner_emails())}"
    assert len(_since(baseline, "run_started", fingerprint=fingerprint)) == 1, (
        f"{tag}: the resolved notification started a new run (or the run count changed)"
    )
    assert fingerprint not in guard_record(), (
        f"{tag}: the guard record still holds {fingerprint} after resolved (it must be released)"
    )
    _say(f"{tag}: resolved started no new run; the guard record released {fingerprint}")


def test_p_demo_be_full_stub_loop_runs_twice_on_one_finding(demo_stack) -> None:  # type: ignore[no-untyped-def]
    """The stub proves WIRING only; the fix is applied by the harness (no Git, no agent)."""
    _say("the stub responder proves wiring only; it does not fix anything; the harness applies the fix")
    started_at = time.monotonic()

    # -- take 1 --------------------------------------------------------------------
    _start_backend("notify_no_fix")
    _say("backend recreated with VT_DEMO_DEFECT=notify_no_fix (VT_FEEDS=fixtures)")
    cookie = backend_login(_USERNAME, _PASSWORD)
    baseline_1 = len(responder_log())
    finding = _register_and_find(cookie)
    finding_id = str(finding["id"])
    assert finding["fixedVersion"] is None, f"the fixture finding has a fixed version: {finding}"
    assert finding["tier"] == "P1", f"the fixture finding is not top tier: {finding}"
    _say(f"take 1: registered pip-app; finding {finding_id} is P1 with no fixed version")

    fingerprint = _firing_phase(1, finding_id, baseline_1, None)
    _assert_duplicate_firing_is_ignored(finding_id, fingerprint, baseline_1)
    _assert_exactly_one_before_fix(1, fingerprint, baseline_1)
    _fix_phase(1, finding_id, fingerprint, baseline_1)
    _say(f"take 1 done in {time.monotonic() - started_at:.0f}s")

    # -- between takes: the guard released the fingerprint ---------------------------
    record = guard_record()
    assert fingerprint not in record, f"between takes the guard record still holds the fingerprint: {record}"
    _say(f"between takes: guard record read from the container = {record} (fingerprint released)")

    # -- take 2: the same finding id --------------------------------------------------
    take_2_at = time.monotonic()
    mailhog_reset()
    webhook_reset()
    baseline_2 = len(responder_log())
    _start_backend("notify_no_fix")  # defect back on BEFORE the job fails, so a retry cannot succeed
    result = set_job_state(finding_id, "failed")
    assert result.get("updated") == 1, f"alert-set did not re-fail exactly one job for finding {finding_id}: {result}"
    _say(f"take 2: finding {finding_id} job re-failed through the #159 seam (alert-set); defect back on")

    fingerprint_2 = _firing_phase(2, finding_id, baseline_2, fingerprint)
    assert fingerprint_2 == fingerprint
    _assert_exactly_one_before_fix(2, fingerprint, baseline_2)
    _fix_phase(2, finding_id, fingerprint, baseline_2)
    _say(
        f"take 2 done in {time.monotonic() - take_2_at:.0f}s; both takes {time.monotonic() - started_at:.0f}s "
        "(record these in the PR for #161)"
    )
