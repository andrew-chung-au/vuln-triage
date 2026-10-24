"""Helpers for the `alert` Compose test (task 27, #159).

Used only by the ``compose``-marked cases in ``tests/test_compose_alert.py``,
which run under ``make test-compose JOB=alert`` against the running stack. They
never run under ``make test`` / ``make verify`` (the ``compose`` marker is
deselected there), so they are free to open loopback HTTP connections to the
published service ports and to shell out to ``docker compose``.

What this adds on top of ``compose_telemetry.py`` (which it reuses for the
Prometheus / MailHog / ``_poll`` helpers):

1. A **firing-state seam** runner: the overdue job must live in the containerized
   Postgres (not published to the host), so the seam runs *inside* the backend
   container via ``docker compose run -T --rm backend python -m
   vulntriage.manage alert-* ...`` — exactly as the harness seeds its user. The
   job is thus produced from **stored job state**, and the alert fires through
   the real task-26 Grafana rule, not an in-test simulation (the #172
   Compose-path requirement, recorded on #159).
2. A **stub webhook sink** client: read/reset the record-only sink the override
   runs from the backend image, so a case can assert "0 to the responder" or
   "1 request naming finding X".
3. MailHog helpers scoped to the human-email alert (Grafana sends the mail over
   SMTP, so the test reads MailHog, not the backend's own delivery).

VERIFY (external behaviour, confirmed on the running stack — see the
``VERIFY:`` notes in ``tests/test_compose_alert.py`` and
``observability/grafana/provisioning/alerting/us14-overdue.yaml``): the exact
Grafana 11.3.0 firing latency, ``NoData`` semantics, webhook POST shape, and the
``GF_SMTP_*`` keys MailHog accepts.
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import urllib.error
import urllib.request
from typing import Any

# Reuse the telemetry helpers verbatim (same query/poll shapes, same images).
from compose_telemetry import (  # noqa: F401 (re-exported for the cases)
    ComposeQueryError,
    DEFAULT_TIMEOUT_S,
    _get_json,
    _poll,
    mailhog_messages,
    mailhog_recipients,
    prometheus_query,
    wait_for_metric,
)

# The record-only webhook sink (compose.alert.yaml runs it from the backend
# image). Published to the host for the case to read; the responder contact
# point inside Grafana reaches it by service name on the shared network.
WEBHOOK_SINK_URL = os.environ.get("VT_WEBHOOK_SINK_HOST_URL", "http://localhost:9099")

# The human-email recipient the alert override set VT_ALERT_HUMAN_EMAIL to, so a
# case can confirm the MailHog message is addressed to it.
ALERT_HUMAN_EMAIL = os.environ.get("VT_ALERT_HUMAN_EMAIL", "alert-human@alert.test")

# How the seam is invoked in-container. ci/test-compose.sh exports the compose
# project name and file list so the host-side case can run `docker compose run`
# against the SAME project the stack is up under.
_COMPOSE_PROJECT = os.environ.get("VT_COMPOSE_PROJECT", "vt-alert")
_COMPOSE_FILES = os.environ.get("VT_COMPOSE_FILES", "compose.yaml compose.alert.yaml")
_SEAM_TIMEOUT_S = 120


# -- the firing-state seam (runs manage.py inside the backend container) -----


def _compose_base() -> list[str]:
    files: list[str] = []
    for f in _COMPOSE_FILES.split():
        files += ["-f", f]
    return ["docker", "compose", "-p", _COMPOSE_PROJECT, *files]


def run_seam(args: list[str]) -> dict[str, Any]:
    """Run ``python -m vulntriage.manage <args>`` in a one-off backend container.

    Returns the parsed ``VT_MANAGE_RESULT`` JSON the command prints. A non-zero
    exit or a missing result line is a hard error (never a skip): the seam
    failing means the alert cannot be driven from stored state, which must fail
    the job, not pass it quietly.
    """
    cmd = [
        *_compose_base(),
        "run", "-T", "--rm", "backend",
        "python", "-m", "vulntriage.manage", *args,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=_SEAM_TIMEOUT_S)
    result: dict[str, Any] | None = None
    for line in proc.stdout.splitlines():
        if line.startswith("VT_MANAGE_RESULT "):
            result = json.loads(line[len("VT_MANAGE_RESULT ") :])
    if result is None or proc.returncode != 0:
        raise ComposeQueryError(
            f"seam {shlex.join(args)!r} failed (rc={proc.returncode})\n"
            f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    return result


def seed_overdue_job(
    *,
    state: str = "failed",
    tier: str = "P1",
    finding_tier: str | None = None,
    age_minutes: int | None = None,
    sent_age_hours: float | None = None,
    label: str | None = None,
) -> dict[str, Any]:
    """Create one top-tier job in ``state`` (backdated) and return the result dict.

    ``result["finding_id"]`` is the id the ``{finding_id,tier}`` series and the
    alert instance will carry.
    """
    args = ["alert-seed", "--state", state, "--tier", tier]
    if finding_tier is not None:
        args += ["--finding-tier", finding_tier]
    if age_minutes is not None:
        args += ["--age-minutes", str(age_minutes)]
    if sent_age_hours is not None:
        args += ["--sent-age-hours", str(sent_age_hours)]
    if label is not None:
        args += ["--label", label]
    return run_seam(args)


def set_job_state(finding_id: int, state: str, *, sent_age_hours: float | None = None) -> dict[str, Any]:
    """Drive a finding's top-tier job(s) to ``state`` (A-RESOLVE: to ``sent``)."""
    args = ["alert-set", "--finding-id", str(finding_id), "--state", state]
    if sent_age_hours is not None:
        args += ["--sent-age-hours", str(sent_age_hours)]
    return run_seam(args)


def rescore_finding(finding_id: int, tier: str) -> dict[str, Any]:
    """Re-score a finding's current tier (A-TIER: the recorded job tier must win)."""
    return run_seam(["alert-rescore", "--finding-id", str(finding_id), "--tier", tier])


def clear_seed() -> dict[str, Any]:
    """Delete every row the alert seam created (each A-* case starts from zero)."""
    return run_seam(["alert-clear"])


def stop_service(service: str) -> None:
    """Stop a running Compose service (A-GAP part 2: open a metric gap)."""
    subprocess.run([*_compose_base(), "stop", service], check=True, timeout=_SEAM_TIMEOUT_S)


def start_service(service: str) -> None:
    """Start a previously-stopped Compose service (A-GAP part 2: restore it)."""
    subprocess.run([*_compose_base(), "start", service], check=True, timeout=_SEAM_TIMEOUT_S)


# -- the stub webhook sink (the responder destination) -----------------------


def webhook_recorded() -> list[dict[str, Any]]:
    """Return the requests the stub webhook sink has recorded so far."""
    return _get_json(f"{WEBHOOK_SINK_URL}/__recorded") or []


def webhook_reset() -> None:
    """Clear the sink's recorded requests (call between cases)."""
    try:
        with urllib.request.urlopen(f"{WEBHOOK_SINK_URL}/__reset", timeout=10):  # noqa: S310 (loopback)
            return
    except (urllib.error.URLError, OSError) as exc:
        raise ComposeQueryError(f"webhook sink reset failed: {exc}") from exc


def wait_for_webhook_health(timeout_s: float = DEFAULT_TIMEOUT_S) -> bool:
    """Wait until the stub webhook sink answers /__health."""

    def _ok() -> bool:
        try:
            with urllib.request.urlopen(f"{WEBHOOK_SINK_URL}/__health", timeout=5):  # noqa: S310
                return True
        except (urllib.error.URLError, OSError):
            return False

    return _poll(lambda: _ok() or False, timeout_s)


def wait_for_webhook_requests(count: int = 1, timeout_s: float = DEFAULT_TIMEOUT_S) -> list[dict[str, Any]]:
    """Wait until the sink has recorded at least ``count`` requests; return them."""

    def _enough() -> list[dict[str, Any]] | bool:
        got = webhook_recorded()
        return got if len(got) >= count else False

    return _poll(_enough, timeout_s)


def webhook_finding_ids(recorded: list[dict[str, Any]]) -> set[str]:
    """Collect every ``finding_id`` label present in the sink's recorded payloads.

    VERIFY: Grafana 11.3.0's webhook POST shape. The common shape is
    ``{"alerts": [{"labels": {"finding_id": "...", "tier": "..."}, ...}]}``; this
    reads that, and falls back to scanning the raw JSON for a ``finding_id`` key
    so a shape difference shows up as a diagnostic, not a silent empty set.
    """
    ids: set[str] = set()
    for req in recorded:
        payload = req.get("json")
        ids |= _finding_ids_in(payload)
    return ids


def _finding_ids_in(payload: Any) -> set[str]:
    out: set[str] = set()
    if isinstance(payload, dict):
        for alert in payload.get("alerts", []) or []:
            labels = (alert.get("labels") or {}) if isinstance(alert, dict) else {}
            fid = labels.get("finding_id")
            if fid:
                out.add(str(fid))
        # Fallback: any nested finding_id anywhere in the body.
        if not out:
            out |= _scan_for_key(payload, "finding_id")
    return out


def _scan_for_key(obj: Any, key: str) -> set[str]:
    found: set[str] = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key and v:
                found.add(str(v))
            else:
                found |= _scan_for_key(v, key)
    elif isinstance(obj, list):
        for item in obj:
            found |= _scan_for_key(item, key)
    return found


# -- the overdue metric and the human-email sink -----------------------------


def overdue_series(finding_id: int | None = None) -> list[dict[str, Any]]:
    """The ``vt_top_tier_notification_overdue`` series, optionally one finding's.

    Uses an instant query; when ``finding_id`` is given it filters to that
    label so a case can poll for that finding's value reaching 1 or 0.
    """
    if finding_id is None:
        return prometheus_query("vt_top_tier_notification_overdue")
    return prometheus_query(f'vt_top_tier_notification_overdue{{finding_id="{finding_id}"}}')


def wait_for_overdue_value(finding_id: int, value: int, timeout_s: float = DEFAULT_TIMEOUT_S) -> None:
    """Wait until the finding's overdue series reads exactly ``value`` (0 or 1)."""

    def _match() -> bool:
        for s in overdue_series(finding_id):
            val = s.get("value")
            if val and str(val[1]) == str(value):
                return True
        return False

    _poll(lambda: _match() or False, timeout_s)


def mailhog_alert_messages(to: str | None = None) -> list[dict[str, Any]]:
    """MailHog messages, optionally only those addressed to ``to``."""
    msgs = mailhog_messages()
    if to is None:
        return msgs
    out = []
    for msg in msgs:
        for addr in msg.get("To", []) or []:
            mailbox, domain = addr.get("Mailbox"), addr.get("Domain")
            if mailbox and domain and f"{mailbox}@{domain}" == to:
                out.append(msg)
                break
    return out


def wait_for_alert_email(to: str, count: int = 1, timeout_s: float = DEFAULT_TIMEOUT_S) -> list[dict[str, Any]]:
    """Wait until MailHog holds at least ``count`` messages addressed to ``to``."""

    def _enough() -> list[dict[str, Any]] | bool:
        msgs = mailhog_alert_messages(to)
        return msgs if len(msgs) >= count else False

    return _poll(_enough, timeout_s)
