#!/usr/bin/env bash
# Compose telemetry/alert/responder test runner (issue #157, task 25).
#
# Brings up the observability stack (observability/compose.yaml: Collector,
# Prometheus, Tempo, Loki, Grafana, MailHog) under a test-owned project name,
# runs the selected JOB's cases against it with the backend exporting OTLP to
# the Collector, then tears the project down. Needs Docker + Docker Compose;
# runs in CI (the telemetry/alert/responder jobs) or on the human's host, never
# in the agent sandbox.
#
# Usage (via the Makefile): make test-compose JOB=<telemetry|alert|responder>
#   JOB=telemetry  the cases #157 ships (see below)
#   JOB=alert      task 27 / #159 (the US-14 A-* alert cases)
#   JOB=responder  task 28c / #220 (the responder in Compose, wiring cases)
#   no JOB         runs all three in turn (for the human's host)
#
# The telemetry cases #157 ships: T-REFUSE only (the backend's excluded
# attributes never leave the Collector). The delivery-dependent cases — the
# MailHog forms of I-OWNER-NOAWS / I-OWNER-SENDER, T-E6, T-DELIVER-TRACE and the
# full T-JOURNEY-BE — need the *deployed backend container* to deliver, so they
# move to prerequisite #172 (which builds that containerized-backend harness).
#
# VERIFY (settled by the human on the running stack, pinned images in
# observability/compose.yaml): that a host pytest process exports OTLP to the
# published Collector port and reaches Prometheus/Tempo/Loki/MailHog on their
# published localhost ports; the Collector gRPC endpoint URL from the host.

set -uo pipefail

JOB="${JOB:-}"

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$repo_root"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is not available; make test-compose runs in CI or on the host, not the sandbox" >&2
  exit 1
fi
if [ ! -x backend/.venv/bin/pytest ]; then
  echo "backend/.venv is missing: run make install first" >&2
  exit 1
fi

# The telemetry job runs the app stack (db, migrations, backend) AND the
# observability stack together under ONE project via compose.telemetry.yaml
# (which `include`s both), so the backend reaches the Collector/MailHog/Postgres
# by service name on the shared network, with the fixtures mode, fixtures mount
# and OTLP/mail wiring applied. The pytest cases drive the backend over its
# published port (127.0.0.1:8000) and query Prometheus/Tempo/Loki/MailHog on
# their published localhost ports. T-REFUSE still runs its host-side driver
# against the same Collector.
# compose.yaml + the telemetry override are a -f merge (so the backend override
# applies); the override `include`s observability/compose.yaml (so its bind
# mounts resolve against observability/). See compose.telemetry.yaml's header.
# The `alert` job adds compose.alert.yaml as a third -f override (Grafana SMTP,
# the stub webhook sink, the alert env) under its own project name; run_alert
# sets PROJECT and COMPOSE below. The telemetry job keeps vt-telemetry.
PROJECT="vt-telemetry"
COMPOSE=(docker compose -p "$PROJECT" -f compose.yaml -f compose.telemetry.yaml)

# Env the host-side T-REFUSE driver reads (observability/settings.py). The
# containerized journey reads its env from compose.telemetry.yaml, not here.
export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4317"
export OTEL_SERVICE_NAME="vulntriage-backend"
export DEPLOYMENT_ENVIRONMENT="test"
export SERVICE_VERSION="compose-test"
# Required by the compose files; throwaway values for the test project only.
export GRAFANA_ADMIN_PASSWORD="${GRAFANA_ADMIN_PASSWORD:-test-only-not-a-secret}"
export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-vt-test-not-a-secret}"

# The security-lead user the journey logs in as (seeded inside the container, so
# the password is piped on stdin and never on a command line). The test reads
# these too (to log in over HTTP).
export VT_TEST_USERNAME="telemetry-lead"
export VT_TEST_PASSWORD="telemetry-not-a-secret"
export VT_BACKEND_URL="http://localhost:8000"
# The journey's notification.deliver span/metric/mail appear only after the
# DeliveryWorker's next poll (~30s) plus the batch-export flush, so give the
# pollers more than the 60s default.
export VT_COMPOSE_POLL_TIMEOUT="${VT_COMPOSE_POLL_TIMEOUT:-150}"

cleanup() {
  "${COMPOSE[@]}" down --volumes --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup EXIT

seed_user() {
  # Create the login-able security-lead user INSIDE the backend container
  # (task 9's create-user command, #176), password piped on stdin via
  # `run -T` so it is never a command-line argument. The migrations service has
  # already built the schema in Postgres, which this shares.
  echo "== seeding the security-lead user (in-container) =="
  printf '%s\n' "$VT_TEST_PASSWORD" | "${COMPOSE[@]}" run -T --rm backend \
    python -m vulntriage.manage create-user \
    --username "$VT_TEST_USERNAME" --display-name "Telemetry Lead" \
    --email "lead@telemetry.test" --role "security lead"
}

run_telemetry() {
  echo "== starting the app + observability stack (project $PROJECT) =="
  # Bring up only the services the journey needs (not the frontend). --wait
  # blocks until each is healthy; migrations runs to completion first.
  "${COMPOSE[@]}" up -d --wait db migrations otel-collector prometheus tempo loki mailhog backend || return 1

  seed_user || return 1

  mkdir -p .scratch
  echo "== running the telemetry cases (T-REFUSE + T-JOURNEY-BE + I-OWNER-* MailHog) =="
  # -m compose selects the compose-marked cases; -s so the driver/journey
  # diagnostics show in the CI log even on a green run.
  backend/.venv/bin/pytest -c backend/pyproject.toml -s -m compose tests/test_compose_telemetry.py
}

wait_for_heartbeat() {
  # Bounded wait (60 x 5s) until Prometheus returns at least one
  # vt_top_tier_notification_overdue series (the label-less 0 heartbeat).
  local url="http://localhost:9090/api/v1/query?query=vt_top_tier_notification_overdue"
  local i
  echo "== [alert] waiting for the overdue-gauge heartbeat in Prometheus =="
  for i in $(seq 1 60); do
    if curl -fsS "$url" 2>/dev/null | grep -q '"result":\[{'; then
      return 0
    fi
    sleep 5
  done
  echo "the overdue-gauge heartbeat never reached Prometheus within 300s" >&2
  return 1
}

# -- alert job (task 27, #159): the US-14 A-* cases ---------------------------
#
# Layers compose.alert.yaml (Grafana SMTP -> MailHog, the stub webhook sink, the
# alert env) on the telemetry stack under its own project. The seam
# (manage.py alert-*) runs in-container and writes the overdue job to the same
# Postgres the gauge reads, so the alert fires from STORED job state. The
# A-FIRE negative is a harness toggle: a second up/run with the task-26 rule
# file removed from a provisioning COPY (the committed tree is never touched).
run_alert() {
  PROJECT="vt-alert"
  COMPOSE=(docker compose -p "$PROJECT" -f compose.yaml -f compose.telemetry.yaml -f compose.alert.yaml)

  # Alert env, all throwaway test-only values (never committed, never from .env).
  # The host-side cases read VT_ALERT_HUMAN_EMAIL / VT_WEBHOOK_SINK_HOST_URL; the
  # provisioning (us14-overdue.yaml) interpolates the VT_* values inside Grafana;
  # ci exports the compose project + file list so the cases' seam runner can
  # `docker compose run` against this same project.
  export VT_ALERT_HUMAN_EMAIL="${VT_ALERT_HUMAN_EMAIL:-alert-human@alert.test}"
  export VT_RESPONDER_WEBHOOK_URL="${VT_RESPONDER_WEBHOOK_URL:-http://webhook-sink:9099/responder}"
  export VT_RESPONDER_WEBHOOK_TOKEN="${VT_RESPONDER_WEBHOOK_TOKEN:-alert-not-a-secret}"
  export VT_WEBHOOK_SINK_HOST_URL="http://localhost:9099"
  export VT_COMPOSE_PROJECT="$PROJECT"
  export VT_COMPOSE_FILES="compose.yaml compose.telemetry.yaml compose.alert.yaml"
  # The alert needs a gauge scrape + >= one 1-minute rule evaluation + delivery,
  # so give the pollers real headroom over the telemetry default. The top-level
  # default above already SET VT_COMPOSE_POLL_TIMEOUT to 150, so a
  # `:-240`-style default on the same variable would never apply (the alert job
  # would silently run at the too-tight 150s and time out the firing waits).
  # Force 300s here regardless of that top-level default, but keep it
  # overridable via a DEDICATED knob (VT_ALERT_POLL_TIMEOUT) so the human can
  # still tune the alert job without disturbing the telemetry default.
  export VT_COMPOSE_POLL_TIMEOUT="${VT_ALERT_POLL_TIMEOUT:-300}"

  mkdir -p .scratch

  echo "== [alert] starting the app + observability + webhook-sink stack (project $PROJECT) =="
  # Grafana starts LAST, once the gauge's heartbeat is in Prometheus. Started
  # together, Grafana evaluated the rule before the backend's first metric
  # export (60s), so the metric was absent: NoData fired a human email at
  # start-up, and its [RESOLVED] email came ~6 min later (the default route's
  # 5m group_interval), landing in a later case's "no human email" check
  # (A-HELD in the CI run at d7027ad).
  "${COMPOSE[@]}" up -d --wait \
    db migrations otel-collector prometheus tempo loki mailhog webhook-sink backend || return 1
  wait_for_heartbeat || return 1
  "${COMPOSE[@]}" up -d --wait grafana || return 1

  echo "== [alert] running the positive A-* cases (rule present) =="
  # The seam clears any prior seeded state between cases (test fixture); -s so the
  # per-case diagnostics show in the CI log even on a green run.
  VT_ALERT_RULE_ABSENT=0 \
    backend/.venv/bin/pytest -c backend/pyproject.toml -s -m compose tests/test_compose_alert.py || return 1

  # -- A-FIRE negative: bring Grafana back up with the rule file removed -------
  echo "== [alert] A-FIRE negative: provisioning the rule-absent copy =="
  prov_copy=".scratch/alert-provisioning-no-rule"
  rm -rf "$prov_copy"
  cp -R observability/grafana/provisioning "$prov_copy"
  rm -f "$prov_copy/alerting/us14-overdue.yaml"
  export VT_ALERT_PROVISIONING="./$prov_copy"
  # Recreate only Grafana so it reloads the rule-absent provisioning; the metric
  # path (backend/Collector/Prometheus) and the sinks keep running.
  "${COMPOSE[@]}" up -d --force-recreate --no-deps grafana || return 1

  echo "== [alert] running the A-FIRE negative (rule absent) =="
  VT_ALERT_RULE_ABSENT=1 \
    backend/.venv/bin/pytest -c backend/pyproject.toml -s -m compose tests/test_compose_alert.py || return 1
}

# -- responder job (task 28c, #220): the responder wired into the alert path --
#
# Layers compose.responder.yaml (the stub-mode responder built from ./backend,
# the backend's VT_DEMO_DEFECT passthrough) on the alert stack under its own
# project. Grafana's webhook contact point is pointed at the responder, so the
# real Grafana alert reaches it; compose.alert.yaml still makes Grafana depend
# on the webhook-sink, so the sink starts too and a case asserts it saw 0
# requests. The responder's logs are stdout JSON lines (the Collector ingests
# OTLP only), so the cases read `docker compose logs responder`.
#
# Cases: tests/test_compose_responder.py (P-PROD-REFUSAL, the Grafana body shape,
# the Grafana test notification, the 401 cases, the env check). #233 adds
# P-DEMO-BE; #161 adds the verify.yml job.
run_responder() {
  PROJECT="vt-responder"
  COMPOSE=(docker compose -p "$PROJECT" -f compose.yaml -f compose.telemetry.yaml -f compose.alert.yaml -f compose.responder.yaml)

  # Throwaway test-only values (never committed, never from .env). The webhook
  # token is Grafana's VT_RESPONDER_WEBHOOK_TOKEN; compose.responder.yaml gives
  # the SAME value to the responder as its webhook secret. The API token is
  # shared by the backend and the responder and must be non-empty (compose.yaml
  # defaults it to empty, which would give the responder 401s from the backend).
  export VT_ALERT_HUMAN_EMAIL="${VT_ALERT_HUMAN_EMAIL:-alert-human@alert.test}"
  export VT_RESPONDER_WEBHOOK_TOKEN="${VT_RESPONDER_WEBHOOK_TOKEN:-responder-webhook-not-a-secret}"
  export VT_RESPONDER_WEBHOOK_URL="http://responder:9100/webhook/grafana"
  export RESPONDER_API_TOKEN="${RESPONDER_API_TOKEN:-responder-api-not-a-secret}"
  export RESPONDER_MODE="stub"
  export VT_WEBHOOK_SINK_HOST_URL="http://localhost:9099"
  export VT_RESPONDER_HOST_URL="http://localhost:9100"
  export VT_COMPOSE_PROJECT="$PROJECT"
  export VT_COMPOSE_FILES="compose.yaml compose.telemetry.yaml compose.alert.yaml compose.responder.yaml"
  # Firing needs a gauge scrape + >= one 1-minute rule evaluation (as the alert
  # job); a dedicated knob keeps it tunable without touching the other jobs.
  export VT_COMPOSE_POLL_TIMEOUT="${VT_RESPONDER_POLL_TIMEOUT:-300}"

  mkdir -p .scratch

  echo "== [responder] starting the app + observability + responder stack (project $PROJECT) =="
  # Grafana starts last, once the gauge heartbeat is in Prometheus, and after the
  # responder (its webhook destination), for the reasons given in run_alert.
  "${COMPOSE[@]}" up -d --wait \
    db migrations otel-collector prometheus tempo loki mailhog webhook-sink backend responder || return 1
  wait_for_heartbeat || return 1
  "${COMPOSE[@]}" up -d --wait grafana || return 1

  echo "== [responder] running the responder cases =="
  backend/.venv/bin/pytest -c backend/pyproject.toml -s -m compose tests/test_compose_responder.py
}

case "$JOB" in
  telemetry) run_telemetry ;;
  alert)     run_alert ;;
  responder) run_responder ;;
  "")
    # No JOB: run all three in turn (the human's host).
    # Each job tears its own project down first: they publish the same host
    # ports (8000, 3000, ...), so the next job cannot start beside the last.
    rc=0
    run_telemetry || rc=$?
    cleanup
    run_alert || rc=$?
    cleanup
    run_responder || rc=$?
    exit "$rc"
    ;;
  *)
    echo "JOB must be one of: telemetry, alert, responder (got '$JOB')" >&2
    exit 2
    ;;
esac
