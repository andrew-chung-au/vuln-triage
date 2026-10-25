#!/usr/bin/env bash
# Shared server-side deploy for one environment (dev or prod). Delivered and run
# on the server by the deploy workflow via SSM Run Command (AWS-RunShellScript);
# it is NOT run in CI directly. The workflow base64-encodes this file and the
# committed compose.yaml, sends them to the running instance, and this script
# decodes compose.yaml, writes the <env> project files and brings the <env>
# Compose project up on the given image tag.
#
# Both environments run on the ONE server (A36): two Compose projects (`dev`,
# `prod`) behind ONE reverse proxy (Caddy) on the two hostnames
# dev.<eip>.sslip.io and app.<eip>.sslip.io. Only one container can bind
# :80/:443, so this script runs a single shared Caddy (`vt-caddy`, project
# `vt-edge`) and (re)builds its Caddyfile from a per-env snippet each deploy
# writes, so dev and prod coexist. Deploying one environment never disturbs the
# other's running containers.
#
# It runs the published GHCR images by tag (public, no registry credential;
# aws-setup.md step 6.3) instead of building, and names the frontend container
# `<env>-frontend` on the shared `vt-edge` network so the shared Caddy can reach
# it. user-data.sh delivers no project files, so this script writes them all.
#
# Inputs (environment, set by the SSM command the workflow sends):
#   DEPLOY_ENV        `dev` or `prod` — the project/environment to deploy
#   IMAGE_TAG         the course image tag YYYYMMDD-HHMMSS-shortsha to deploy
#   GHCR_REPO         ghcr.io/<owner>/<repo> (the image name prefix)
#   EIP_DASHED        the Elastic IP with dots turned to dashes (for the hostname)
#   APP_COMPOSE_B64   base64 of the committed compose.yaml
#   ACME_EMAIL        the Let's Encrypt contact email (optional)
#   AWS_REGION        the region holding the Secrets Manager secret (optional;
#                     falls back to the instance's region)
#
# Secrets (the database password, the repository read token) are read HERE from
# the AWS Secrets Manager secret `vuln-triage/<env>` using the server's instance
# role — NOT passed from the workflow (the deploy OIDC role has no secrets
# access; architecture.md Security boundaries, aws-setup.md step 8). The secret
# is one JSON object, e.g. {"POSTGRES_PASSWORD":"…","GITHUB_READ_TOKEN":"…"}.
# For dev, if the secret is absent the script falls back to throwaway values so
# the dev environment still stands up; for prod the secret (with at least
# POSTGRES_PASSWORD) is required.
#
# A failed `pull`/`up` leaves the running containers in place (architecture.md
# Rollback): the script exits non-zero and does not tear the stack down, so a
# bad tag does not take the environment down — the previous deploy keeps serving.
set -euo pipefail

: "${DEPLOY_ENV:?DEPLOY_ENV is required (dev or prod)}"
: "${IMAGE_TAG:?IMAGE_TAG is required}"
: "${GHCR_REPO:?GHCR_REPO is required}"
: "${EIP_DASHED:?EIP_DASHED is required}"
: "${APP_COMPOSE_B64:?APP_COMPOSE_B64 is required}"
ACME_EMAIL="${ACME_EMAIL:-admin@example.com}"

case "$DEPLOY_ENV" in
  dev)  HOST_PREFIX=dev ;;   # dev.<eip>.sslip.io
  prod) HOST_PREFIX=app ;;   # app.<eip>.sslip.io
  *) echo "DEPLOY_ENV must be 'dev' or 'prod', got '$DEPLOY_ENV'" >&2; exit 2 ;;
esac

# --- Secrets from Secrets Manager (via the instance role) -------------------
# Read vuln-triage/<env> and pull the keys we need. The secret is a JSON object;
# jq is used if present, else a small python fallback. AWS CLI and python3 ship
# on AL2023; jq may not, so do not hard-require it.
SECRET_ID="vuln-triage/${DEPLOY_ENV}"
secret_json=""
if secret_json="$(aws secretsmanager get-secret-value \
      --secret-id "$SECRET_ID" \
      ${AWS_REGION:+--region "$AWS_REGION"} \
      --query SecretString --output text 2>/dev/null)"; then
  echo "Read secret $SECRET_ID from Secrets Manager."
else
  secret_json=""
  echo "No Secrets Manager secret $SECRET_ID (or no access); using fallbacks where allowed."
fi

secret_get() { # secret_get KEY -> value (empty if absent)
  [ -z "$secret_json" ] && return 0
  printf '%s' "$secret_json" | python3 -c '
import json,sys
try:
    d=json.load(sys.stdin)
except Exception:
    sys.exit(0)
v=d.get(sys.argv[1])
if v is not None:
    print(v)
' "$1"
}

POSTGRES_PASSWORD="$(secret_get POSTGRES_PASSWORD)"
GITHUB_READ_TOKEN="$(secret_get GITHUB_READ_TOKEN)"
RESPONDER_API_TOKEN="$(secret_get RESPONDER_API_TOKEN)"
MAIL_TRANSPORT="$(secret_get MAIL_TRANSPORT)"
MAIL_SENDER="$(secret_get MAIL_SENDER)"

# The database password is required for prod (from the prod secret); dev may
# fall back to a throwaway value so it still comes up before secrets exist.
if [ -z "$POSTGRES_PASSWORD" ]; then
  if [ "$DEPLOY_ENV" = "prod" ]; then
    echo "POSTGRES_PASSWORD missing from Secrets Manager secret $SECRET_ID." >&2
    echo "Create the production secret before promoting (aws-setup.md step 8)." >&2
    exit 2
  fi
  POSTGRES_PASSWORD="devpw"
fi

BASE_DIR=/opt/vuln-triage
APP_DIR="$BASE_DIR/app"
ENV_DIR="$BASE_DIR/$DEPLOY_ENV"
EDGE_DIR="$BASE_DIR/edge"
mkdir -p "$APP_DIR" "$ENV_DIR" "$EDGE_DIR/caddy/sites"

# The committed application Compose file the override merges onto.
printf '%s' "$APP_COMPOSE_B64" | base64 -d > "$APP_DIR/compose.yaml"

# Project .env: the tag to run and the per-environment settings. The database
# password and tokens come from Secrets Manager (above); optional values are
# only written when present. The file is written with restrictive permissions
# because it holds the database password and any tokens.
umask 077
{
  echo "IMAGE_TAG=${IMAGE_TAG}"
  echo "GHCR_REPO=${GHCR_REPO}"
  echo "DEPLOYMENT_ENVIRONMENT=${DEPLOY_ENV}"
  echo "POSTGRES_PASSWORD=${POSTGRES_PASSWORD}"
  echo "LLM_MODE=stub"
  echo "RESPONDER_MODE=stub"
  [ -n "$GITHUB_READ_TOKEN" ]   && echo "GITHUB_READ_TOKEN=${GITHUB_READ_TOKEN}"
  [ -n "$RESPONDER_API_TOKEN" ] && echo "RESPONDER_API_TOKEN=${RESPONDER_API_TOKEN}"
  [ -n "$MAIL_TRANSPORT" ]      && echo "MAIL_TRANSPORT=${MAIL_TRANSPORT}"
  [ -n "$MAIL_SENDER" ]         && echo "MAIL_SENDER=${MAIL_SENDER}"
} > "$ENV_DIR/.env"

# Image-pinned override: run the published images by tag instead of building,
# and put the frontend on the shared vt-edge network as <env>-frontend so the
# shared Caddy reaches it. `!reset` clears the build/ports from compose.yaml.
# DEPLOYMENT_ENVIRONMENT=prod makes the backend's VT_FEEDS=fixtures and
# VT_DEMO_DEFECT refusals fail closed (A42/A35, architecture.md Environment
# signal).
cat > "$ENV_DIR/compose.deploy.yaml" <<COMPOSE
services:
  migrations:
    image: \${GHCR_REPO}/backend:\${IMAGE_TAG}
    build: !reset null
  backend:
    image: \${GHCR_REPO}/backend:\${IMAGE_TAG}
    build: !reset null
    environment:
      DEPLOYMENT_ENVIRONMENT: \${DEPLOYMENT_ENVIRONMENT}
  frontend:
    image: \${GHCR_REPO}/frontend:\${IMAGE_TAG}
    build: !reset null
    container_name: ${DEPLOY_ENV}-frontend
    ports: !reset []
    networks:
      - default
      - vt-edge
networks:
  vt-edge:
    external: true
COMPOSE

# This environment's Caddy site snippet. The shared Caddyfile is rebuilt from
# all present snippets so dev and prod are both served by the one Caddy.
cat > "$EDGE_DIR/caddy/sites/${DEPLOY_ENV}.caddy" <<SITE
${HOST_PREFIX}.${EIP_DASHED}.sslip.io {
	reverse_proxy ${DEPLOY_ENV}-frontend:8080
}
SITE

# Assemble the shared Caddyfile: the global block, then every site snippet.
{
  echo "{"
  echo "	email ${ACME_EMAIL}"
  echo "}"
  echo
  cat "$EDGE_DIR"/caddy/sites/*.caddy
} > "$EDGE_DIR/caddy/Caddyfile"

# The single shared Caddy (project vt-edge). Written once; `up` is idempotent
# and a later deploy of the other environment re-runs it with the updated
# Caddyfile (Caddy reloads on file change via the mount + restart).
cat > "$EDGE_DIR/compose.caddy.yaml" <<'CADDYC'
services:
  caddy:
    image: caddy:2
    restart: unless-stopped
    container_name: vt-caddy
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./caddy/Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    networks:
      - vt-edge
volumes:
  caddy_data:
  caddy_config:
networks:
  vt-edge:
    external: true
CADDYC

# Deploy the <env> project by image tag. A failed pull leaves the running
# containers in place (set -e exits before `up`).
cd "$ENV_DIR"
docker compose -f "$APP_DIR/compose.yaml" -f compose.deploy.yaml \
  --project-name "$DEPLOY_ENV" --env-file .env pull
docker compose -f "$APP_DIR/compose.yaml" -f compose.deploy.yaml \
  --project-name "$DEPLOY_ENV" --env-file .env up -d --wait

# Start or refresh the single shared Caddy edge with the rebuilt Caddyfile.
# Recreate so Caddy picks up the new site list; it serves whichever projects
# are up and keeps the other environment serving.
docker compose -f "$EDGE_DIR/compose.caddy.yaml" --project-name vt-edge up -d --force-recreate

echo "${DEPLOY_ENV} deploy complete: ${GHCR_REPO}:${IMAGE_TAG} (${HOST_PREFIX}.${EIP_DASHED}.sslip.io)"
