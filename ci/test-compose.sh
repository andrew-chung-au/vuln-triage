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
#   JOB=alert      task 27 / #159 (not implemented here; selector only)
#   JOB=responder  task 28 / #160 (not implemented here; selector only)
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
PROJECT="vt-telemetry"

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

run_not_implemented() {
  # The selector is complete (task 25) but these jobs' cases are later tasks.
  echo "make test-compose JOB=$1: the $1 cases are task ${2} (not implemented in #157)." >&2
  echo "The selector exists so the CI $1 job can be wired when that task lands." >&2
  return 3
}

case "$JOB" in
  telemetry) run_telemetry ;;
  alert)     run_not_implemented alert 27 ;;
  responder) run_not_implemented responder 28 ;;
  "")
    # No JOB: run all three in turn (the human's host). alert/responder are not
    # implemented yet, so this reports them and fails overall until they land.
    rc=0
    run_telemetry || rc=$?
    run_not_implemented alert 27 || true
    run_not_implemented responder 28 || true
    echo "note: only the telemetry job is implemented in #157; alert/responder are tasks 27/28." >&2
    exit "$rc"
    ;;
  *)
    echo "JOB must be one of: telemetry, alert, responder (got '$JOB')" >&2
    exit 2
    ;;
esac
