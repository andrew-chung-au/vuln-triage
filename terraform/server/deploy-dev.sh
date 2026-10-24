#!/usr/bin/env bash
# Server-side dev deploy (task 21 / #142). Delivered and run on the server by
# the deploy workflow via SSM Run Command (AWS-RunShellScript). It is NOT run in
# CI directly: the workflow base64-encodes this file and the committed
# compose.yaml, sends them to the running instance, and this script decodes
# compose.yaml, writes the dev project files and brings the `dev` Compose
# project up on the pushed image tag.
#
# It runs the published GHCR images by tag (public, no registry credential;
# aws-setup.md step 6.3) instead of building, names the dev frontend
# `dev-frontend` on the shared `vt-edge` network (created in user-data.sh) so
# the Caddy reverse proxy can reach it, and starts Caddy for the dev hostname.
# user-data.sh delivers no project files, so this script writes them all.
#
# Inputs (environment, set by the SSM command the workflow sends):
#   IMAGE_TAG     the course image tag YYYYMMDD-HHMMSS-shortsha to deploy
#   GHCR_REPO     ghcr.io/<owner>/<repo> (the image name prefix)
#   EIP_DASHED    the Elastic IP with dots turned to dashes (for the hostname)
#   ACME_EMAIL    the Let's Encrypt contact email (optional)
#   APP_COMPOSE_B64  base64 of the committed compose.yaml
#
# A failed `pull`/`up` leaves the running containers in place (architecture.md
# Rollback): the script exits non-zero and does not tear the stack down.
set -euo pipefail

: "${IMAGE_TAG:?IMAGE_TAG is required}"
: "${GHCR_REPO:?GHCR_REPO is required}"
: "${EIP_DASHED:?EIP_DASHED is required}"
: "${APP_COMPOSE_B64:?APP_COMPOSE_B64 is required}"
ACME_EMAIL="${ACME_EMAIL:-admin@example.com}"

APP_DIR=/opt/vuln-triage/app
DEV_DIR=/opt/vuln-triage/dev
mkdir -p "$APP_DIR" "$DEV_DIR/caddy"

# The committed application Compose file the override merges onto.
printf '%s' "$APP_COMPOSE_B64" | base64 -d > "$APP_DIR/compose.yaml"

# dev project .env: the tag to run and the dev-only settings. The database
# password is a throwaway for the dev project; real secrets move to Secrets
# Manager via the instance role in a later task.
cat > "$DEV_DIR/.env" <<ENV
IMAGE_TAG=${IMAGE_TAG}
GHCR_REPO=${GHCR_REPO}
DEPLOYMENT_ENVIRONMENT=dev
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-devpw}
LLM_MODE=stub
RESPONDER_MODE=stub
ENV

# Image-pinned override: run the published images by tag instead of building,
# and put the dev frontend on the shared vt-edge network as dev-frontend so
# Caddy reaches it. `!reset` clears the build/ports from the base compose.yaml.
cat > "$DEV_DIR/compose.deploy.yaml" <<'COMPOSE'
services:
  migrations:
    image: ${GHCR_REPO}/backend:${IMAGE_TAG}
    build: !reset null
  backend:
    image: ${GHCR_REPO}/backend:${IMAGE_TAG}
    build: !reset null
    environment:
      DEPLOYMENT_ENVIRONMENT: ${DEPLOYMENT_ENVIRONMENT}
  frontend:
    image: ${GHCR_REPO}/frontend:${IMAGE_TAG}
    build: !reset null
    container_name: dev-frontend
    ports: !reset []
    networks:
      - default
      - vt-edge
networks:
  vt-edge:
    external: true
COMPOSE

# Caddy reverse proxy for the dev hostname (automatic Let's Encrypt).
cat > "$DEV_DIR/caddy/Caddyfile" <<CADDY
{
	email ${ACME_EMAIL}
}
dev.${EIP_DASHED}.sslip.io {
	reverse_proxy dev-frontend:8080
}
CADDY

cat > "$DEV_DIR/compose.caddy.yaml" <<'CADDYC'
services:
  caddy:
    image: caddy:2
    restart: unless-stopped
    container_name: dev-caddy
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

# Deploy the dev project by image tag. A failed pull leaves the running
# containers in place (set -e exits before `up`).
cd "$DEV_DIR"
docker compose -f "$APP_DIR/compose.yaml" -f compose.deploy.yaml \
  --project-name dev --env-file .env pull
docker compose -f "$APP_DIR/compose.yaml" -f compose.deploy.yaml \
  --project-name dev --env-file .env up -d --wait

# Start (or refresh) the dev Caddy edge.
docker compose -f compose.caddy.yaml --project-name dev-edge --env-file .env up -d

echo "dev deploy complete: ${GHCR_REPO}:${IMAGE_TAG}"
