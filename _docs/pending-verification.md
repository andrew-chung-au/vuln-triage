# Pending verification (cloud / host steps)

One place for every build step that the **agent sandbox cannot run** — because
it needs Docker, real network, AWS, or a `terraform apply` — and so is left for a
**GitHub Codespace, a Claude Code cloud session, CI, or the human's host**.

Each item says where to run it, the exact commands, and when it is done. Tick
items off as they pass. When an issue's items are all done, close the issue and
remove its section here.

Why this exists: the Kiro Web agent sandbox has no shell network and no Docker
socket (`AGENTS.md` Project gotchas), so Compose stacks, live dependency scans,
and AWS applies are authored by the agent and **verified by the human**. This
file collects those hand-offs so a cloud session has one checklist.

Last updated: 2026-10-24.

---

## #141 — AWS infrastructure + dev environment (task 17)

PR: #151 (merged). Run from the **human's machine** (AWS admin identity) and CI;
full detail in `_docs/aws-setup.md` and `_docs/terraform-verify.md`.

- [ ] Record the 5 decisions in #141 (region, existing OIDC provider y/n, secrets store, verified SES sender, apply-from-your-machine).
- [ ] `terraform fmt -check` / `init -backend=false` / `validate` in each module under `terraform/` (also runnable in the push-check image; `_docs/terraform-verify.md` §1).
- [ ] Apply in order: `bootstrap/` → `deploy-roles/` → `server/`; set the GitHub variables `AWS_DEV_ROLE_ARN` / `AWS_PROD_ROLE_ARN`; record the Elastic IP.
- [ ] First deploy; confirm `https://dev.<eip>.sslip.io` answers the frontend and the deploy log names one image digest.
- [ ] Close #141 when the dev URL is up.

## #140 — light security scan (task 20)

PR: #167. Run in a **Codespace / Claude Code cloud / CI** (needs network for the
advisory services and to generate the fixture lockfiles). Full checklist on the
#140 issue comment; summary:

- [ ] Generate the fixture lockfiles per each `tests/fixtures/security/*/SPEC.md` (`uv lock`, `npm install --package-lock-only`); record each advisory ID/severity. `VERIFY:` the advisory is still reported that day.
- [ ] `make security-scan-selftest` — all five fixtures hit their expected outcome.
- [ ] `make security-scan` — the real tree exits 0 (after #111). Report any high/critical; no ignore list.
- [ ] Commit the generated lockfiles to `feat/140-security-scan`; the `security-scan` CI job then goes green.
- [ ] `make verify` stays green (the scan is not part of it).
- [ ] Close #140 when the CI `security-scan` job is green on the PR.

## #155 — observability stack + US-13 dashboard (task 24)

PR: (this change). Run in a **Codespace / Claude Code cloud / Docker host**
(needs Docker). The stack is `observability/`; full detail in
`observability/README.md`.

- [ ] `cd observability && docker compose up -d --wait` comes up healthy (Collector, Prometheus, Tempo, Loki, Grafana, MailHog); set `GRAFANA_ADMIN_PASSWORD` in `.env` first.
- [ ] Run the backend against it: `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317 DEPLOYMENT_ENVIRONMENT=dev SERVICE_VERSION=local make dev`, then trigger a scan.
- [ ] Grafana `http://localhost:3000` → the "US-13 journey" dashboard shows the three signals (metric, trace, logs) side by side, filterable by environment and version.
- [ ] MailHog answers at `http://localhost:8025` (it receives the owner email in task 37).
- [ ] `VERIFY:` the pinned image tags resolve and the Collector `keep_keys` / Loki OTLP / Tempo OTLP / Grafana trace-to-logs behave as configured (`observability/README.md` VERIFY list). Adjust config if a pinned version differs.
- [ ] Note: the `make test-compose` telemetry cases (`T-JOURNEY-BE`, `T-REFUSE`) that *assert* the allowlist drop are **task 25 (#157)**, not this task; this task's check is the manual dashboard.

## #156 — backend owner notification + delivery (task 37)

PR: (this change). The core `I-OWNER-*` / `S-NOTIFY` cases run under
`make test` (SQLite + the in-process recording sink, no Docker/AWS/network), so
**the human only needs `make verify`** to land this. The items below are the
Compose and AWS variants the sandbox cannot run.

- [ ] (Codespace / cloud / Docker host) With the `observability/` stack up and the backend run with `MAIL_TRANSPORT=mailhog MAIL_SENDER=<a verified-looking address>`, trigger a P1 finding; confirm one owner email lands in MailHog (`http://localhost:8025`, or `GET /api/v2/messages`). This is `I-OWNER-NOAWS` / `I-OWNER-SENDER` under `make test-compose` and feeds `T-JOURNEY-BE` (task 25 / #157).
- [ ] `VERIFY:` MailHog's SMTP port and HTTP read API (1025 / `GET /api/v2/messages` assumed; `observability/compose.yaml`).
- [ ] (Human, AWS step — deferred, task 37 SES) Add `boto3` to `backend/pyproject.toml` and run `make backend-lock`; settle the SES `VERIFY:` items (IAM action `ses:SendEmail`/`ses:SendRawEmail`, verified-identity ARN, `ses:FromAddress` condition, region, sandbox verified-recipient rule, free allowance) and the exact `boto3` SES client call in `mail/transport.py` `SesTransport.send`. The code ships MailHog-proven with the SES path `VERIFY:`-marked until then.
- [ ] Note: the ownerless-release path (`held: ownerless` / `held: owner email missing` → released by setting an owner email) is `I-ASSET-UPDATE`, owned by the asset-update task, not this one.

## #158 — US-14 alert metric + provisioned Grafana rule (task 26)

PR: (this change). The **metric half is fully `make verify`-able** — the new
`tests/test_metrics_overdue.py` cases run under `make test` (SQLite + fake clock
+ an `InMemoryMetricReader`, no Docker/AWS/network), so **the human needs only
`make verify`** to land that half. `backend/uv.lock` should **not** change (no
new dependency). The items below are the **Grafana rule**, which is authored
here and needs a real Grafana to confirm — run in a **Codespace / Claude Code
cloud / Docker host**. The rule is `observability/grafana/provisioning/alerting/us14-overdue.yaml`
(the whole `grafana/provisioning` folder is already mounted into the Grafana
container, so no `observability/compose.yaml` change was needed).

- [ ] With the `observability/` stack up (`cd observability && docker compose up -d --wait`, `GRAFANA_ADMIN_PASSWORD` set), confirm Grafana provisions the rule, both contact points and the notification policy with no load error (Grafana → Alerting; container logs show no provisioning error). Set `VT_ALERT_HUMAN_EMAIL`, `VT_RESPONDER_WEBHOOK_URL`, `VT_RESPONDER_WEBHOOK_TOKEN` in the stack env first (the YAML references them; no real values are committed).
- [ ] Run the backend against the Collector (`OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317 DEPLOYMENT_ENVIRONMENT=dev SERVICE_VERSION=local make dev`). Drive a **failed** top-tier job (task 28's `VT_DEMO_DEFECT=notify_no_fix` is the intended driver once it exists; until then force a job to `failed` / backdate a `pending` job past 30 min) and confirm the rule shows **1** for that finding and the alert fires **one** instance carrying its `finding_id` and `tier`.
- [ ] Confirm a **sent** job shows **0** and the alert for that finding resolves (and that its series is gone 24h after `sent_at`).
- [ ] Confirm a system with **no jobs** fires **no** alert and sends **no** responder message (only the label-less `0` heartbeat series exists).
- [ ] Confirm the `NoData` path: stop the backend/metric so the metric goes absent, and confirm the rule's `noDataState: Alerting` fires **one** instance with **no** `finding_id`, routed to the **human email only** (never the responder webhook).
- [ ] Confirm a finding alert reaches **both** the responder webhook and the human email (via the `finding-alert` contact point's two receivers), and that the annotations carry the dashboard link, environment and version.
- [ ] `VERIFY:` the Grafana-11.3.0 details marked in `us14-overdue.yaml`: the file-provisioning schema loads clean; the `threshold`/`eq 1` condition fires one instance per `{finding_id,tier}` series; a single contact point with two receivers delivers to both; the `finding_id =~ ".+"` matcher excludes the NoData instance so it falls through to the human-only default; the webhook bearer-auth header shape; `repeat_interval: 8760h` as the no-repeat stand-in; the `/d/<uid>/<slug>` dashboard URL; and how the Collector's Prometheus export surfaces `deployment.environment` / `service.version` as metric labels for the environment/version annotations (else set them from the stack env).
- [ ] Note: the `alert` Compose test and the `A-*` cases are **task 27 (#159)**; the responder webhook **receiver** is **task 28 (#160)** — both out of scope here.
- [ ] Close #158 when the metric half is green under `make verify` and the Grafana rule behaviour above is confirmed on the running stack.

---

## Convention

- An item here is the agent saying "I wrote and offline-checked this; it needs a real run I can't do." The agent records the same steps in the issue's session summary; this file is the cross-issue index.
- Prefer the smallest capable environment: CI for anything a workflow already runs; a Codespace/cloud session for Docker/network; the human's machine only for AWS applies and secrets.
- After a run, paste the result on the issue (and tick here). Keep this file to **open** items only.
