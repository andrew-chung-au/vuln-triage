"""The `alert` Compose job (task 27, #159): the US-14 end-to-end alert cases.

Runs under ``make test-compose JOB=alert`` against the running stack (the app
stack + the observability stack + a stub webhook sink), brought up by
``ci/test-compose.sh``. Marked ``compose`` and DESELECTED by ``make test`` /
``make verify`` (the default ``-m "not compose"``), so it never runs — and never
*skips* — in the no-Docker gate (the seam's own logic is unit-tested there, in
``tests/test_manage.py``). A missing required service is a hard failure here,
never a silent skip (``_docs/testing.md`` § CI jobs).

The firing is observed from **stored ``NotificationJob`` state** (the in-container
``manage.py alert-*`` seam writes the job into Postgres; the backend's overdue
gauge reads it at collection time; the task-26 Grafana rule evaluates the metric
and routes the alert) — never simulated in this test process (the #172
Compose-path requirement, recorded on #159). The test asserts only what actually
arrived at a sink: the overdue series in Prometheus, the human email in MailHog,
and the responder request in the stub webhook sink.

Cases (the human trimmed the job to these on 2026-10-25, see #159):
- ``A-FIRE`` — one overdue top-tier job fires exactly one alert at BOTH sinks,
  naming the finding (finding_id + tier only; no advisory/owner/url/credential).
- ``A-FIRE`` negative — with the rule absent (harness toggle), the same job
  fires at NEITHER sink.

Each harness pass runs ONE case, so no case can see another case's late
Grafana notification (resolutions arrive minutes after a series goes). The
gauge rules the other A-* cases checked (held jobs never emit, the recorded
tier, the empty system's heartbeat, sent -> 0) are covered in seconds by
``tests/test_metrics_overdue.py``; the NoData gap (A-GAP part 2) is a manual
check (``_docs/verify-locally.md`` §7b).

VERIFY (external Grafana/alerting behaviour — confirmed on the running stack, NOT
asserted blind; see also ``observability/grafana/provisioning/alerting/
us14-overdue.yaml`` and ``_docs/pending-verification.md`` #159):
- Firing latency end-to-end (gauge scrape + >= one 1-minute rule evaluation +
  notification). ``VT_COMPOSE_POLL_TIMEOUT`` is set with headroom over 1 minute.
- The webhook POST shape and that the recorded body carries ``finding_id`` /
  ``tier`` labels (not advisory text) — ``compose_alert.webhook_finding_ids``.
- ``GF_SMTP_*`` keys on grafana/grafana:11.3.0 and that MailHog accepts Grafana's
  SMTP with no auth.
"""

from __future__ import annotations

import os

import pytest

from compose_alert import (
    ALERT_HUMAN_EMAIL,
    ComposeQueryError,
    clear_seed,
    mailhog_alert_messages,
    mailhog_reset,
    seed_overdue_job,
    wait_for_alert_email,
    wait_for_overdue_value,
    wait_for_webhook_health,
    wait_for_webhook_requests,
    webhook_alert_labels,
    webhook_finding_ids,
    webhook_recorded,
    webhook_reset,
)

pytestmark = pytest.mark.compose

# The provisioning-rule-absent run (A-FIRE negative) is a harness toggle, not a
# manual edit: ci/test-compose.sh brings the stack up a second time with the
# rule file removed from a provisioning copy and sets this env so this module
# runs ONLY the negative assertion in that configuration (and skips it in the
# normal, rule-present run). See run_alert() in ci/test-compose.sh.
_RULE_ABSENT = os.environ.get("VT_ALERT_RULE_ABSENT") == "1"

# The per-alert LABELS the responder is allowed to see: the finding's own
# finding_id/tier plus Grafana's standard routing labels. The no-leak guarantee
# (US-14 carries finding id + tier only; architecture § Security boundaries) is
# about this label set, NOT the raw webhook envelope — Grafana's body
# legitimately carries externalURL/generatorURL/annotations.summary/dashboard_url
# (i.e. "http"/"summary"/"@"), so substring-scanning the whole body for those is
# a false positive (QA risk 1). We assert the per-alert labels carry only the
# allowed keys and none of the forbidden markers.
_ALLOWED_LABEL_KEYS = frozenset({"finding_id", "tier", "alertname", "grafana_folder"})

# Substrings that must NEVER appear in an alert LABEL key or value (owner
# contact, advisory text, URL, credential). These are checked against the per-
# alert label set only, not the envelope.
_FORBIDDEN_IN_LABELS = ("owner", "@", "http", "bearer", "secret", "advisory")

# Grafana's routing labels are fixed strings from the task-26 rule file (the
# rule `title` and its `folder`), not job data, so they are pinned exactly
# rather than substring-scanned: the title "Top-tier owner notification
# overdue" legitimately contains "owner" (confirmed in the alert CI job).
_FIXED_LABELS = {
    "alertname": "Top-tier owner notification overdue",
    "grafana_folder": "VulnTriage",
}

# How long past creation the firing job is backdated: just past the backend's
# 30-minute W, so a `claimed` job reads 1 (A33; _OVERDUE_WINDOW is unchanged).
_PAST_W_MINUTES = 31


def _seed_firing_job() -> dict:
    """Seed one overdue top-tier job that stays overdue for the whole case.

    The job is `claimed` and backdated past W, not `failed`: the backend's
    DeliveryWorker polls every 30s and retries `failed` jobs, so a seeded
    `failed` job was delivered to MailHog and flipped to `sent` (gauge 0)
    before the 60s metric export usually saw it as 1. The worker never selects
    a `claimed` job, so it stays overdue until the case changes it. The #159
    A-FIRE criterion allows either form ("failed, or pending/claimed backdated
    past the 30-min window W").
    """
    return seed_overdue_job(state="claimed", tier="P1", age_minutes=_PAST_W_MINUTES)


@pytest.fixture(autouse=True)
def _clean_case():  # type: ignore[no-untyped-def]
    """The case starts from zero seeded jobs, an empty webhook sink and an empty MailHog.

    Keeps the "exactly one" / "nothing" assertions honest. Each harness pass
    runs one case, so the teardown only removes the seeded rows.
    """
    assert wait_for_webhook_health(), "stub webhook sink did not become healthy"
    clear_seed()
    webhook_reset()
    mailhog_reset()
    yield
    clear_seed()


# -- A-FIRE: fires once, names the finding, both sinks ------------------------


@pytest.mark.skipif(_RULE_ABSENT, reason="positive A-FIRE runs only with the rule present")
def test_a_fire_one_overdue_job_fires_once_at_both_sinks() -> None:
    """A-FIRE: one overdue top-tier job → exactly one alert at BOTH sinks."""
    result = _seed_firing_job()
    finding_id = result["finding_id"]

    # The gauge reads the stored job state: the series goes to 1 for this finding.
    wait_for_overdue_value(finding_id, 1)

    # Both sinks receive exactly one alert instance naming the finding.
    webhook = wait_for_webhook_requests(1)
    ids = webhook_finding_ids(webhook)
    assert str(finding_id) in ids, f"responder payload did not name finding {finding_id}: {webhook}"

    emails = wait_for_alert_email(ALERT_HUMAN_EMAIL, 1)
    assert emails, "no human-email alert reached MailHog"

    # No-leak check, narrowed to the per-alert LABEL set (the responder-visible
    # identity of the alert) rather than the raw Grafana envelope, which
    # legitimately carries externalURL/generatorURL/annotations.summary. Each
    # alert's labels must name the finding (finding_id + tier) plus only
    # Grafana's own standard routing keys, and must carry no owner/email/url/
    # advisory/credential marker. The fixed routing labels must equal the rule
    # file's values exactly; every other label is scanned for forbidden markers.
    label_sets = webhook_alert_labels(webhook)
    assert label_sets, f"no per-alert labels in the responder payload: {webhook}"
    for labels in label_sets:
        assert "finding_id" in labels, f"alert labels do not name the finding: {labels}"
        extra = set(labels) - _ALLOWED_LABEL_KEYS
        assert not extra, f"responder alert carried unexpected label keys {extra}: {labels}"
        for key, expected in _FIXED_LABELS.items():
            assert labels.get(key) == expected, f"alert label {key!r} is not {expected!r}: {labels}"
        for key, value in labels.items():
            if key in _FIXED_LABELS:
                continue
            blob = f"{key}={value}".lower()
            for banned in _FORBIDDEN_IN_LABELS:
                assert banned not in blob, f"responder alert label leaked {banned!r}: {labels}"


# -- A-FIRE negative: rule removed → no firing at either sink -----------------


@pytest.mark.skipif(not _RULE_ABSENT, reason="negative A-FIRE runs only in the rule-absent harness pass")
def test_a_fire_negative_no_rule_no_firing() -> None:
    """A-FIRE negative: with the provisioned rule absent, the same job fires at neither sink.

    This is the configuration ``ci/test-compose.sh`` brings up with the rule file
    removed from the provisioning copy (VT_ALERT_RULE_ABSENT=1). The overdue
    series still reads 1 (the backend metric is unchanged), but with no rule to
    evaluate it, nothing is sent. If a future change re-added firing without the
    rule, this assertion would fail — which is the point.
    """
    result = _seed_firing_job()
    finding_id = result["finding_id"]
    wait_for_overdue_value(finding_id, 1)

    # Give the stack the same firing window the positive case uses, then assert
    # neither sink received anything.
    with pytest.raises(ComposeQueryError):
        wait_for_webhook_requests(1, timeout_s=90)
    assert webhook_recorded() == [], "responder received an alert with the rule absent"
    assert mailhog_alert_messages(ALERT_HUMAN_EMAIL) == [], "human email sent with the rule absent"
