# Observability stack (task 24 / #155)

A **separate** Docker Compose project from the application stack
(`compose.yaml` at the repo root). It collects the US-13 telemetry the backend
emits (task 23) and shows the trace, metric and logs side by side in Grafana.

For submission this runs in **local Compose only**; deploying it on AWS is
future-development item X3 (`_docs/roadmap-showcase.md`). Needs Docker — run it in a
GitHub Codespace, a Claude Code cloud session, CI, or any Docker host, not the
agent sandbox.

## Services

| Service | Role | Port (host) |
|---|---|---|
| `otel-collector` | OTLP in; enforces the A32 allowlist; fans out | 4317 (gRPC), 4318 (HTTP) |
| `prometheus` | metrics store | 9090 |
| `tempo` | trace store | 3200 |
| `loki` | log store | 3100 |
| `grafana` | dashboards (behind auth) | 3000 |
| `mailhog` | mail catcher for the owner notification (task 37) | 1025 (SMTP), 8025 (UI) |

## Run it

```sh
cp .env.example .env                # from the repo root; set GRAFANA_ADMIN_PASSWORD
cd observability
docker compose --env-file ../.env up -d --wait
```

Compose reads `.env` from the folder you run it in, so pass the root file with
`--env-file ../.env` (without it Compose reports `GRAFANA_ADMIN_PASSWORD` missing).
Use the same flag for `down`.

The alert rule's placeholder recipient and responder webhook
(`VT_ALERT_HUMAN_EMAIL`, `VT_RESPONDER_WEBHOOK_URL`, `VT_RESPONDER_WEBHOOK_TOKEN`)
default to values that go nowhere, so the plain stack starts without them. Export
real ones in your shell first to change them. Without these defaults Grafana exits
at start-up with "could not find addresses in settings".

Grafana: `http://localhost:3000` (user `admin`, password `GRAFANA_ADMIN_PASSWORD`).
The **US-13 journey** dashboard (folder "VulnTriage") has three panels — a
Prometheus metric pane, a Tempo trace pane and a Loki logs pane — with an
environment and version filter.

## Point the backend at the Collector

The backend exports OTLP only when `OTEL_EXPORTER_OTLP_ENDPOINT` is set (A40). To
feed this stack, run the backend with:

```sh
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317 \
DEPLOYMENT_ENVIRONMENT=dev SERVICE_VERSION=local \
make dev
```

(Inside a Compose network the endpoint is `http://otel-collector:4317`.) Then
trigger a scan (register an asset, or re-scan) and watch the three signals
appear in the dashboard.

## The allowlist (no-leak guarantee)

`otel-collector.yaml`'s `transform/allowlist` processor keeps only the A32 keys
and drops the rest — owner contact, advisory text, repository URLs, lockfile
content, credentials, and the auto-instrumented `url.*` / `db.statement`
attributes (the latter from the SQLAlchemy instrumentation). This is the
second line of defence; the backend already filters in code (task 23). Task 25
adds the `T-REFUSE` Compose test that proves an injected `owner.email` never
leaves the Collector.

## Stop it

```sh
docker compose down            # keep the trace/log volumes
docker compose down --volumes  # fresh slate
```

## VERIFY (settled when first run)

- The pinned image tags resolve (`otel/opentelemetry-collector-contrib:0.111.0`, `prom/prometheus:v2.54.1`, `grafana/tempo:2.6.1`, `grafana/loki:3.2.1`, `grafana/grafana:11.3.0`, `mailhog/mailhog:v1.0.1`).
- The contrib `transform` processor's `keep_keys` works as written on 0.111.0 (else the `attributes` processor with explicit deletes).
- Loki's OTLP ingest at `/otlp` and the `tracesToLogsV2` Grafana link shape on the pinned versions.
- Tempo single-binary OTLP ingest on 2.6.1.
