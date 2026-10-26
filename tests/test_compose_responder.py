"""The responder Compose job (task 28 / #160; wiring in task 28c / #220).

Runs under ``make test-compose JOB=responder`` (``ci/test-compose.sh`` brings up
the app + observability + alert + responder stack under the ``vt-responder``
project). Marked ``compose`` and DESELECTED by ``make test`` / ``make verify``.

THESE CASES WERE WRITTEN WITHOUT BEING RUN. The cloud session that wrote them has
no working Docker build (and no ghcr.io access), so none of them is verified
until CI or a Docker host runs ``make test-compose JOB=responder``. The static
checks of ``compose.responder.yaml`` and of the script are different: they run
in ``make verify`` (``tests/test_compose_responder_static.py``).

Cases:
- ``P-PROD-REFUSAL`` (container form, #218): the backend image with the
  production configuration and ``VT_DEMO_DEFECT=notify_no_fix`` exits non-zero
  and logs ``DemoDefectConfigurationError``; the dev control exits 0.
- The real Grafana 11.3.0 body shape reaches the responder (the right bearer is
  accepted, the responder answers 2xx), and the webhook-sink saw nothing.
- A Grafana test notification ends ``no_change`` with an explanation and no
  ``pull_request_opened``; the case records whether 11.3.0 sent a fingerprint.
- A wrong, missing or malformed bearer gets 401, starts no run, reads no API and
  leaves the guard record unchanged.
- The container holds no GitHub/Anthropic/AWS key and runs in stub mode; a
  responder started in ``real`` mode (or with the mode empty) exits non-zero.

The responder log is stdout JSON lines (``docker compose logs responder``), not
Loki. ``P-DEMO-BE`` (the full loop) is #233, not here.
"""

from __future__ import annotations

import os
import subprocess

import pytest

from compose_alert import (
    clear_seed,
    mailhog_reset,
    seed_overdue_job,
    wait_for_overdue_value,
    wait_for_webhook_health,
    webhook_recorded,
    webhook_reset,
)
from compose_responder import (
    WEBHOOK_TOKEN,
    container_env_keys,
    events,
    firing_body,
    guard_record,
    post_webhook,
    responder_log,
    run_responder_once,
    send_grafana_test_notification,
    wait_for_event,
)
from compose_telemetry import _poll

pytestmark = pytest.mark.compose

_PROJECT = os.environ.get("VT_COMPOSE_PROJECT", "vt-responder")

# How long past creation the firing job is backdated: just past the backend's
# 30-minute W (as tests/test_compose_alert.py), and `claimed` so the delivery
# worker never picks it up and flips it to `sent` before the gauge reads 1.
_PAST_W_MINUTES = 31


# -- P-PROD-REFUSAL (container form, #218) ------------------------------------


def _run_backend(deployment_environment: str) -> subprocess.CompletedProcess[str]:
    """Run the backend image once with the defect set; return the finished process.

    ``--no-deps`` keeps the db out of it (the refusal happens at import, before
    any database use); ``-e`` overrides are per-run so no compose file changes.
    ``--build`` rebuilds the image first so a stale one is not tested. The command
    imports the app exactly as uvicorn does.

    VERIFY: ``docker compose run --build`` is accepted by the Compose version in
    CI (the flag was added to ``run`` in Compose v2; if the version rejects it,
    run ``docker compose build backend`` first instead).
    """
    return subprocess.run(
        [
            "docker", "compose", "-p", _PROJECT, "-f", "compose.yaml",
            "run", "--build", "--rm", "--no-deps",
            "-e", "VT_DEMO_DEFECT=notify_no_fix",
            "-e", f"DEPLOYMENT_ENVIRONMENT={deployment_environment}",
            "backend", "python", "-c", "import vulntriage.main",
        ],
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )


def test_p_prod_refusal_container_exits_non_zero_and_logs_the_error() -> None:
    result = _run_backend("prod")
    assert result.returncode != 0, result.stdout + result.stderr
    output = result.stdout + result.stderr
    assert "DemoDefectConfigurationError" in output
    assert "VT_DEMO_DEFECT" in output


def test_p_prod_refusal_container_control_dev_starts() -> None:
    """Control: the same image and variable in dev does not hit the refusal."""
    result = _run_backend("dev")
    assert "DemoDefectConfigurationError" not in result.stdout + result.stderr
    assert result.returncode == 0, result.stdout + result.stderr


# -- the wiring cases ---------------------------------------------------------


@pytest.fixture
def stack():  # type: ignore[no-untyped-def]
    """The case starts from zero seeded jobs, an empty webhook sink and an empty MailHog."""
    assert WEBHOOK_TOKEN, "VT_RESPONDER_WEBHOOK_TOKEN is not exported (ci/test-compose.sh sets it)"
    assert wait_for_webhook_health(), "stub webhook sink did not become healthy"
    clear_seed()
    webhook_reset()
    mailhog_reset()
    yield
    clear_seed()


def test_real_grafana_body_reaches_the_responder(stack) -> None:  # type: ignore[no-untyped-def]
    """A real alert (a job seeded through the #159 seam) reaches the responder and is parsed.

    The responder logs ``run_started`` only after it has accepted the bearer and
    parsed a firing top-level ``status``, an alert ``fingerprint`` and a
    ``finding_id`` label, and it logs ``webhook_rejected`` for a 401/400/413. So a
    ``run_started`` for this finding, and no ``webhook_rejected`` line, is the
    evidence that Grafana's real body shape was accepted with a 2xx.

    The job is ``claimed`` and backdated (as A-FIRE), not ``failed``: the delivery
    worker retries ``failed`` jobs and would flip it to ``sent`` before the gauge
    reads 1. A claimed job makes the stub run end ``no_change`` (no failed job to
    fix), which is fine here: this case proves the shape, and #233 proves the loop.
    """
    rejected_before = len(events("webhook_rejected"))
    result = seed_overdue_job(state="claimed", tier="P1", age_minutes=_PAST_W_MINUTES)
    finding_id = str(result["finding_id"])

    wait_for_overdue_value(int(finding_id), 1)
    started = wait_for_event("run_started", lambda r: r.get("finding_id") == finding_id)

    fingerprint = started.get("fingerprint")
    assert isinstance(fingerprint, str) and fingerprint, f"run_started carried no fingerprint: {started}"
    print(f"[responder] Grafana 11.3.0 alert accepted: finding_id={finding_id} fingerprint={fingerprint}")

    records = responder_log()
    assert len(events("webhook_rejected", records)) == rejected_before, (
        "the responder rejected a webhook (a 400 here means Grafana's body shape differs): "
        f"{events('webhook_rejected', records)}"
    )
    failed = [r for r in events("run_failed", records) if r.get("fingerprint") == fingerprint]
    assert not failed, (
        "the run failed (api_get_finding_failed means the shared RESPONDER_API_TOKEN or the "
        f"backend API was not reachable): {failed}"
    )

    # The alert went to the responder, not to the sink.
    assert webhook_recorded() == [], "the webhook sink recorded a request: the alert did not go to the responder"


def test_grafana_test_notification_ends_no_change(stack) -> None:  # type: ignore[no-untyped-def]
    """A Grafana test notification ends ``no_change`` with an explanation and opens no pull request.

    Records whether 11.3.0 sent a ``fingerprint``: with none, the responder logs
    ``no_change`` with a null fingerprint and touches nothing; with one but no
    ``finding_id``, it runs and ends ``no_change`` for the same reason.
    """
    no_change_before = len(events("no_change"))
    rejected_before = len(events("webhook_rejected"))
    pr_before = len(events("pull_request_opened"))

    status, text = send_grafana_test_notification()
    assert 200 <= status < 300, f"Grafana receivers test returned {status}: {text[:500]}"

    def _new_line() -> bool:
        recs = responder_log()
        return len(events("no_change", recs)) > no_change_before or len(events("webhook_rejected", recs)) > rejected_before

    _poll(lambda: _new_line() or False)
    records = responder_log()
    assert len(events("webhook_rejected", records)) == rejected_before, (
        f"the responder rejected the test notification: {events('webhook_rejected', records)[rejected_before:]}"
    )
    new = events("no_change", records)[no_change_before:]
    assert new, "no no_change line was logged for the test notification"
    line = new[-1]
    assert line.get("explanation"), f"no_change carried no explanation: {line}"
    assert len(events("pull_request_opened", records)) == pr_before, "a test notification opened a pull request"
    sent = "a fingerprint" if line.get("fingerprint") else "no fingerprint"
    print(f"[responder] Grafana 11.3.0 test notification carried {sent}; responder logged no_change")


_BAD_AUTH_HEADERS: list[tuple[str, dict[str, str]]] = [
    ("wrong bearer", {"Authorization": "Bearer not-the-secret"}),
    ("missing header", {}),
    ("scheme only", {"Authorization": "Bearer"}),
    ("wrong scheme", {"Authorization": "Basic Zm9vOmJhcg=="}),
    ("token without scheme", {"Authorization": "not-a-scheme-just-a-token"}),
]


def test_bad_bearer_gets_401_and_changes_nothing(stack) -> None:  # type: ignore[no-untyped-def]
    """A wrong, missing or malformed bearer gets 401, starts no run and leaves the guard alone."""
    record_before = guard_record()
    before = responder_log()
    started_before = len(events("run_started", before))
    api_before = len(events("api_read", before))
    rejected_401_before = len([r for r in events("webhook_rejected", before) if r.get("outcome") == "401"])

    for label, headers in _BAD_AUTH_HEADERS:
        status, _ = post_webhook(firing_body("refused-fp-" + label.replace(" ", "-")), headers)
        assert status == 401, f"{label}: expected 401, got {status}"

    after = responder_log()
    assert len(events("run_started", after)) == started_before, "a refused request started a run"
    assert len(events("api_read", after)) == api_before, "a refused request read the API"
    rejected_401_after = len([r for r in events("webhook_rejected", after) if r.get("outcome") == "401"])
    assert rejected_401_after == rejected_401_before + len(_BAD_AUTH_HEADERS)
    assert guard_record() == record_before, "a refused request changed the guard record"


def test_container_env_has_no_credentials_and_runs_in_stub_mode() -> None:
    """Key names only are asserted and logged; values are never printed."""
    env = container_env_keys()
    keys = sorted(env)
    print(f"[responder] container env keys: {keys}")
    forbidden = [k for k in keys if k.startswith(("GITHUB_", "GH_", "ANTHROPIC_", "AWS_"))]
    assert not forbidden, f"the responder container carries credential keys: {forbidden}"
    assert env.get("RESPONDER_MODE") == "stub"


@pytest.mark.parametrize("mode", ["real", None], ids=["real", "empty"])
def test_responder_refuses_to_start_unless_stub(mode: str | None) -> None:
    """A responder started with ``RESPONDER_MODE=real`` (or empty) exits non-zero at startup."""
    result = run_responder_once(mode)
    assert result.returncode != 0, result.stdout + result.stderr
    assert "RESPONDER_MODE" in result.stdout + result.stderr
