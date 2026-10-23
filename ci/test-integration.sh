#!/usr/bin/env bash
# Real-Postgres integration run (issue #138, task 16).
#
# Brings up only the `db` service from the project compose.yaml under a
# test-owned project name (`vt-test`), runs the integration-marked backend
# cases against it with VT_TEST_DATABASE_URL set, then tears the project down
# (including its volume, so each run starts clean). Needs Docker + Docker
# Compose; runs in CI (the postgres-integration job) or on the human's host,
# never in the agent sandbox.
#
# Isolation: conftest.py builds the schema once with Alembic and wraps each
# test in a transaction that is rolled back (E-GUARD refuses any non-test DB).

set -euo pipefail

PROJECT="vt-test"
# The app compose.yaml plus a test override that publishes the db port to the
# host (the pytest process runs outside Compose and reaches localhost:5432).
COMPOSE_FILES=(-f compose.yaml -f compose.test.yaml)
# A throwaway password for the test database only; never a real secret.
TEST_DB_PASSWORD="vt"
export VT_TEST_DATABASE_URL="postgresql+psycopg://vt:${TEST_DB_PASSWORD}@localhost:5432/vt"

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$repo_root"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is not available; make test-integration runs in CI or on the host, not the sandbox" >&2
  exit 1
fi

cleanup() {
  docker compose -p "$PROJECT" "${COMPOSE_FILES[@]}" down --volumes --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "== starting the vt-test Postgres service =="
# Only the db service is started (not the app services).
POSTGRES_PASSWORD="$TEST_DB_PASSWORD" \
  docker compose -p "$PROJECT" "${COMPOSE_FILES[@]}" up -d --wait db

echo "== running the integration cases against Postgres =="
# The integration layer is marked `sqlite_integration` (the integration-harness
# cases); here they run against Postgres via VT_TEST_DATABASE_URL.
backend/.venv/bin/pytest -c backend/pyproject.toml -m sqlite_integration tests

echo "== integration run OK =="
