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

# The observability stack publishes its ports to localhost (see
# observability/compose.yaml). The backend-side driver (tests/compose_driver.py)
# runs as a host process in the backend venv and exports to the Collector over
# the published gRPC port; the pytest cases query the other services likewise.
COMPOSE=(docker compose -p "$PROJECT" -f observability/compose.yaml)

# OTLP settings the driver reads (observability/settings.py). The T-REFUSE
# driver only emits a span and a log through the Collector; it does not deliver
# mail or open a database, so no MAIL_* / DATABASE_URL is needed here (those
# return with the delivery-dependent cases in #172). GRAFANA_ADMIN_PASSWORD is
# required by the compose file; a throwaway value is fine for the test project.
export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4317"
export OTEL_SERVICE_NAME="vulntriage-backend"
export DEPLOYMENT_ENVIRONMENT="test"
export SERVICE_VERSION="compose-test"
export GRAFANA_ADMIN_PASSWORD="${GRAFANA_ADMIN_PASSWORD:-test-only-not-a-secret}"

cleanup() {
  "${COMPOSE[@]}" down --volumes --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup EXIT

run_telemetry() {
  echo "== starting the observability stack (project $PROJECT) =="
  "${COMPOSE[@]}" up -d --wait || return 1

  mkdir -p .scratch
  echo "== running the telemetry cases (T-REFUSE) =="
  # The compose-marked case queries the stack; -m compose selects only it. -s
  # (no capture) so the driver's VT_DRIVER_RESULT line and the T-REFUSE
  # diagnostic (which excluded keys the helper path sent to the Collector) show
  # in the CI log even on a green run — useful for the negative-check evidence.
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
