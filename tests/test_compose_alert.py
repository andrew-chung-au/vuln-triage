"""The `alert` Compose job (task 27, #159): the US-14 `A-*` alert cases.

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

Cases (one checkable criterion each, from the #159 acceptance list):
- ``A-FIRE`` — one overdue top-tier job fires exactly one alert at BOTH sinks,
  naming the finding (finding_id + tier only; no advisory/owner/url/credential).
- ``A-FIRE`` negative — with the rule absent (harness toggle), the same job
  fires at NEITHER sink.
- ``A-HELD`` — a held: ownerless job never sets the metric and never fires.
- ``A-TIER`` — the recorded ``NotificationJob.tier`` wins over a later re-score.
- ``A-GAP`` part 1 — an empty system fires nothing at either sink.
- ``A-GAP`` part 2 — a metric gap sends one human email (NoData, no finding_id)
  and nothing to the responder.
- ``A-RESOLVE`` — driving the job to ``sent`` resolves the alert; it is one
  firing + at most one resolved, never a second alert (D1 option 1).

VERIFY (external Grafana/alerting behaviour — confirmed on the running stack, NOT
asserted blind; see also ``observability/grafana/provisioning/alerting/
us14-overdue.yaml`` and ``_docs/pending-verification.md`` #159):
- Firing latency end-to-end (gauge scrape + >= one 1-minute rule evaluation +
  notification). ``VT_COMPOSE_POLL_TIMEOUT`` is set with headroom over 1 minute.
- ``NoData`` semantics on 11.3.0: that stopping the Collector long enough makes
  ``noDataState: Alerting`` fire ONE instance with no ``finding_id``, routed to
  the human email only (the ``finding_id =~ ".+"`` matcher excludes it).
- The webhook POST shape and that the recorded body carries ``finding_id`` /
  ``tier`` labels (not advisory text) — ``compose_alert.webhook_finding_ids``.
- ``GF_SMTP_*`` keys on grafana/grafana:11.3.0 and that MailHog accepts Grafana's
  SMTP with no auth.
- ``repeat_interval: 8760h`` does not re-send within a run; the resolved message
  is not counted as a second alert.
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
    overdue_series,
    rescore_finding,
    seed_overdue_job,
    set_job_state,
    start_service,
    stop_service,
    wait_for_alert_email,
    wait_for_no_finding_series,
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
# VERIFY: the exact Grafana 11.3.0 standard label set on first green run — adjust
# _ALLOWED_LABEL_KEYS if 11.3.0 adds another non-identifying routing key.
_ALLOWED_LABEL_KEYS = frozenset({"finding_id", "tier", "alertname", "grafana_folder"})

# Substrings that must NEVER appear in an alert LABEL key or value (owner
# contact, advisory text, URL, credential). These are checked against the per-
# alert label set only, not the envelope.
_FORBIDDEN_IN_LABELS = ("owner", "@", "http", "bearer", "secret", "advisory")

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
def _clean_between_cases():  # type: ignore[no-untyped-def]
    """Each case starts from zero seeded jobs, an empty webhook sink and an empty MailHog.

    Keeps "exactly one" / "nothing" assertions honest: no case inherits another
    case's firing job, recorded request, or delivered email.

    Clearing MailHog (mailhog_reset) removes cross-case email contamination: a
    human-email alert delivered by a PRIOR case (A-FIRE's firing email, or
    A-GAP part 2's legitimate NoData email) would otherwise linger in MailHog's
    in-memory store and make a later case's ``mailhog_alert_messages(...) == []``
    assertion see another case's mail. This is a test-correctness fix, NOT a
    weakening: each case still proves exactly what its criterion says, now
    against a sink that holds only its own mail. The reset runs in SETUP (so
    each case starts clean) AND in teardown (so a case that legitimately leaves
    mail — A-GAP part 2's NoData email — does not bleed into the next case).
    """
    assert wait_for_webhook_health(), "stub webhook sink did not become healthy"
    clear_seed()
    webhook_reset()
    mailhog_reset()
    yield
    clear_seed()
    mailhog_reset()
    # The OTLP→Prometheus exporter keeps the last-observed finding series for a
    # scrape window after clear_seed() drops the DB row, so a later case could
    # otherwise inherit a stale finding_id series. Wait for the empty state to
    # actually be visible before the next case starts (a hard failure if it
    # never clears — never a weakening of any "empty system" assertion).
    wait_for_no_finding_series()


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
    # advisory/credential marker.
    label_sets = webhook_alert_labels(webhook)
    assert label_sets, f"no per-alert labels in the responder payload: {webhook}"
    for labels in label_sets:
        assert "finding_id" in labels, f"alert labels do not name the finding: {labels}"
        extra = set(labels) - _ALLOWED_LABEL_KEYS
        assert not extra, f"responder alert carried unexpected label keys {extra}: {labels}"
        for key, value in labels.items():
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


# -- A-HELD: held jobs are exempt (A39) ---------------------------------------


@pytest.mark.skipif(_RULE_ABSENT, reason="runs only in the rule-present pass")
def test_a_held_ownerless_never_fires() -> None:
    """A-HELD: a held: ownerless top-tier job never sets the metric and never fires."""
    result = seed_overdue_job(state="held: ownerless", tier="P1")
    finding_id = result["finding_id"]

    # The series carries no finding_id for a held job (A39): it reads 0 for this
    # finding throughout. Confirm it never becomes 1.
    with pytest.raises(ComposeQueryError):
        wait_for_overdue_value(finding_id, 1, timeout_s=75)
    assert overdue_series(finding_id) == [], f"held job set a series: {overdue_series(finding_id)}"

    # Nothing reaches either sink for it.
    assert webhook_recorded() == [], "held job reached the responder sink"
    assert mailhog_alert_messages(ALERT_HUMAN_EMAIL) == [], "held job produced a human email"


# -- A-TIER: the recorded tier wins over a later re-score ---------------------


@pytest.mark.skipif(_RULE_ABSENT, reason="runs only in the rule-present pass")
def test_a_tier_recorded_tier_wins_over_rescore() -> None:
    """A-TIER: the series/alert show the job's recorded tier, not the finding's new tier."""
    result = _seed_firing_job()
    finding_id = result["finding_id"]
    wait_for_overdue_value(finding_id, 1)

    # Re-score the finding to a lower tier; the job's recorded tier is unchanged.
    rescore_finding(finding_id, "P3")

    # The overdue series for this finding still carries tier P1 (the recorded
    # NotificationJob.tier), not P3.
    series = overdue_series(finding_id)
    assert series, f"no series for finding {finding_id} after re-score"
    tiers = {s.get("metric", {}).get("tier") for s in series}
    assert tiers == {"P1"}, f"recorded tier did not win over the re-score: {tiers}"


# -- A-GAP part 1: empty system fires nothing ---------------------------------


@pytest.mark.skipif(_RULE_ABSENT, reason="runs only in the rule-present pass")
def test_a_gap_part1_empty_system_fires_nothing() -> None:
    """A-GAP part 1: with no jobs, the rule does not fire and neither sink receives anything."""
    # _clean_between_cases already cleared all seeded jobs, but the OTLP→
    # Prometheus exporter can keep a stale finding series for a scrape window
    # after the DB row is gone (an eventual-consistency gap, not a product
    # defect). Wait for the empty state to be visible before asserting it — a
    # hard failure if it never clears (this still proves an empty system shows
    # no finding series; it just does not race the staleness window).
    wait_for_no_finding_series()

    full = overdue_series()
    # Every series present is the label-less heartbeat (no finding_id) reading 0.
    for s in full:
        metric = s.get("metric", {})
        assert "finding_id" not in metric, f"a finding series exists in an empty system: {metric}"

    # Neither sink receives anything within a firing window.
    with pytest.raises(ComposeQueryError):
        wait_for_webhook_requests(1, timeout_s=75)
    assert mailhog_alert_messages(ALERT_HUMAN_EMAIL) == [], "an empty system produced a human email"


# -- A-GAP part 2: metric gap → human-only NoData -----------------------------


@pytest.mark.skipif(_RULE_ABSENT, reason="runs only in the rule-present pass")
def test_a_gap_part2_metric_gap_sends_human_only_nodata() -> None:
    """A-GAP part 2: a metric gap fires one human email (NoData) and nothing to the responder.

    Drive one firing finding, then open a metric gap by stopping the Collector
    for longer than one evaluation interval so the series goes absent and the
    rule evaluates NoData (``noDataState: Alerting``). The NoData instance has no
    finding_id, so it routes to the human email only; the responder sink receives
    nothing new from the gap.

    VERIFY: Grafana 11.3.0 NoData timing on the running stack — how many missing
    evaluations trigger it and that the NoData instance routes human-only.
    """
    result = _seed_firing_job()
    finding_id = result["finding_id"]
    wait_for_overdue_value(finding_id, 1)
    wait_for_webhook_requests(1)  # the finding's own firing reached the responder once
    responder_before = len(webhook_recorded())
    human_before = len(mailhog_alert_messages(ALERT_HUMAN_EMAIL))

    # Open the gap: stop the Collector so the gauge stops being scraped.
    stop_service("otel-collector")
    try:
        # One more human email arrives (the NoData instance). The responder sink
        # does NOT gain a new request (NoData has no finding_id → human-only).
        wait_for_alert_email(ALERT_HUMAN_EMAIL, human_before + 1, timeout_s=180)
    finally:
        start_service("otel-collector")

    assert len(webhook_recorded()) == responder_before, (
        "the responder sink received a request from the NoData gap (it must not)"
    )


# -- A-RESOLVE: resolution is not a second alert ------------------------------


@pytest.mark.skipif(_RULE_ABSENT, reason="runs only in the rule-present pass")
def test_a_resolve_resolution_is_not_a_second_alert() -> None:
    """A-RESOLVE: driving the job to sent resolves the alert; it is not a second alert (D1 option 1)."""
    result = _seed_firing_job()
    finding_id = result["finding_id"]
    wait_for_overdue_value(finding_id, 1)
    firing = wait_for_webhook_requests(1)
    assert len([r for r in firing if str(finding_id) in webhook_finding_ids([r])]) >= 1

    # Drive the job to sent: the series goes to 0 and the alert resolves.
    set_job_state(finding_id, "sent")
    wait_for_overdue_value(finding_id, 0)

    # Exactly one FIRING notification for this instance; a resolved message (if
    # the webhook receives one at all) is a resolution, not a second alert. We
    # assert the count of distinct firing requests naming this finding stays 1.
    recorded = webhook_recorded()
    firing_requests = [r for r in recorded if _is_firing(r) and str(finding_id) in webhook_finding_ids([r])]
    assert len(firing_requests) == 1, (
        f"expected exactly one firing notification; got {len(firing_requests)}: {firing_requests}"
    )


def _is_firing(request: dict) -> bool:
    """True if a recorded webhook request is a FIRING alert (not a resolution).

    VERIFY: Grafana 11.3.0's webhook body marks state as ``status: firing`` /
    ``status: resolved`` at the top level (and per-alert ``status``). This reads
    the top-level status and treats anything not explicitly ``resolved`` as a
    firing, so a resolved message is never miscounted as a second alert.

    Reviewed for QA risk 1 (the envelope carrying ``http``/``summary``): this is
    already status-based — it keys off the top-level ``status`` field, and its
    only body fallback looks for the literal word ``resolved``, never for the
    ambiguous envelope substrings — so it is left as-is.
    """
    payload = request.get("json")
    if isinstance(payload, dict):
        status = str(payload.get("status", "")).lower()
        if status:
            return status != "resolved"
    # No parseable status: fall back to the raw body not naming "resolved".
    return "resolved" not in (request.get("body") or "").lower()
