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

Who does each item: `_docs/cloud-tasklist.md` lists the verification runs a
Claude Code cloud session can do (CC IDs, with the human step each needs), and
`_docs/human-tasklist.md` lists what only the human can do (AWS, approvals,
decisions, merges). This file is the detailed per-issue checklist both link to;
the cloud-session queue below is superseded by the cloud list, which is the
source for order and dependencies.

Last updated: 2026-10-26, later (owner-run items regrouped into one ticket per sitting: #225 close-out sweep, #226 live observability stack, #227 AWS console, #228 unblock cloud sessions, #229 decisions; #223 closed as replaced by #225; the #159 section removed, its issue closed and its last items green). Earlier: 2026-10-26 (QA unverified items for #157, #172, #218 and #219 collected in #223). Earlier: 2026-10-25 (#193: held-delivery signals, Loki leg recorded; #180: #177 folded into #193; #159 alert job: CI job committed; cross-ref to verify-locally.md §7b)

## Cloud-session queue (Docker work to hand to Claude Code cloud sessions)

Added 2026-10-25 at the human's direction: work the local sandbox can't do for
lack of Docker goes to a Claude Code cloud session (`_docs/cloud-sessions.md`;
one session per issue, credit is limited). Each line is a candidate, not a
started job.

- **#181** (T-E6, telemetry backend down): groomed; the human answered PM decisions Q1-Q3 on 2026-10-25 (comment 6396530230: best-effort close, narrow "alerts unaffected", add Collector self-metrics). Author and run it in the cloud.
- **#182** (`I-OWNER-SENDER` MailHog form): follows #160 (task 28).
- **#198** (`internal error` scan reason): look at the failure reason on the dashboard in a running UI. Running migration `0002` on real Postgres is now **#201** (a `postgres_migration` check in the `postgres-integration` job; Docker-only, verified in CI).
- **#199** (US-13 dashboard live Grafana check, split from #195 on 2026-10-25): needs a running Grafana; shares the dashboard with #181, so sequence them. #195 is now the static fix and test, done locally.
- **#172**, **#174** and **#157** (`T-JOURNEY-BE`, the Loki leg, `T-REFUSE`): done in CI (run 40291587781) and closed (2026-10-26). The optional #193 held-job case is in #226.
- **#155** (dashboard and MailHog check) and the **#158** Grafana rule spot checks: one live-stack sitting, #226.
- **#140** (security scan, PR #167): needs network to generate the fixture lockfiles.
- **Human machine, not cloud:** AWS applies and secrets (#141, `human-tasklist.md` §A).

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
- [ ] Grafana `http://localhost:3000` → the "US-13 journey" dashboard shows the three signals (metric, trace, logs) side by side (no environment or version filter: dropped in #199, future work X14).
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

## #177 / #193 — delivery outcome signals on every branch (Loki leg)

Commit: see the Engineer comment on #193. The span/log/counter for all eight
outcomes (`sent`, `failed`, and `held` with `sender_not_verified`,
`header_injection`, `mail_config`, `ownerless`, `owner_email_missing`,
`no_target`) is covered under `make test` (`tests/test_notifications.py`,
SQLite + in-memory exporters): the log and span trace ids equal the job's stored
`traceparent` trace id and the counter increments once. The end-to-end Loki leg
is **best-effort, not a gate** (human decision, 2026-10-25); closing #193 does
not wait on it.

- [ ] (CI telemetry job, or a Codespace / cloud / Docker host) The #172
  `T-JOURNEY-BE` Loki assertion (see #172 above) covers the `sent` log. It also
  remains the only end-to-end proof of #177's `sent` log leg.
- [ ] Held-job Loki case is **not** in `T-JOURNEY-BE`: not added blind. It needs a
  second asset with no owner registered through the container backend (a distinct
  repository URL the `VT_FEEDS=fixtures` mode can scan, which the fixtures do not
  have yet), and `wait_for_trace_with_span("notification.enqueue")` then matches
  either journey's trace, so the test needs a per-asset trace lookup. Neither can
  be checked without Docker. Optional manual check: with the stack up, register an
  ownerless asset whose scan yields a P1 finding, wait one delivery poll (~30s),
  then confirm a Loki `notification.deliver` log with `vt.outcome="held"` and
  `vt.error.code="ownerless"` carries the trace id of that job's
  `notification.enqueue` span in Tempo. Post the result on #193.

## #210 and #211 — Grafana start-up and the US-13 metric panel (observability)

PRs: #211 (stack starts without an override file) and #210 (metric panel plots a
running total). Both merged 2026-10-25; neither was run against a live stack by an
agent (no Docker daemon in the cloud session). Run on a Docker host, **not** in the
clean clone (the app steps use `make`; see `_docs/agent-kit/environments.md`).

- [ ] **#211:** from `observability/`, `docker compose --env-file ../.env up -d --wait` with **no** override file (`.scratch/obs-override.yaml` removed or not passed). All six containers (Collector, Prometheus, Tempo, Loki, Grafana, MailHog) become healthy, and the Grafana log has no "could not find addresses in settings" error. The placeholders went through an override file on the owner's machine on 2026-10-25; the committed defaults are the same values.
- [ ] **#211:** `make test-compose JOB=alert` still passes (the alert test's real `VT_ALERT_HUMAN_EMAIL` / `VT_RESPONDER_WEBHOOK_URL` must override the new defaults; checked statically only).
- [ ] **#210:** after a fresh demo run **with the stack already up** (start the stack, delete `backend/.scratch/vulntriage.db`, then `make demo OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317 SERVICE_VERSION=local`), the US-13 journey dashboard's first panel ("Notifications (metric) ... running total") shows a line that steps up on **Last 1 hour**. The owner saw no improvement on 2026-10-26, so the cause may be the data: check Prometheus (`http://localhost:9090`, query `vt_notifications_total`). No rows means no notification was recorded after the stack came up; a row with a value means the panel query needs another look.
- [ ] If the panel still shows nothing while Prometheus has the series, file an issue; the panel query is in `observability/grafana/dashboards/us13-journey.json` and is checked statically by `tests/test_us13_dashboard.py`.
- [ ] On success: retake `g9-grafana-dashboard.png` (full dashboard, view mode) and `g9-grafana-trace.png` (one `scan.run` trace, single full-width Explore pane), link them in the README, and tick `#155` and `#199` above if the panels also show data there.

---

## Convention

- This file is the **single consolidated checklist** of every open human/CI
  verification action, grouped by issue. For *how to run* the app and the
  Compose test jobs (`make dev`, `make compose-up`, `make test-compose`), see
  the step-by-step guide in `_docs/verify-locally.md` (§6 app, §7 Compose stack,
  §7b the Compose test jobs); this file holds the per-issue items you tick off
  while you run them.
- An item here is the agent saying "I wrote and offline-checked this; it needs a real run I can't do." The agent records the same steps in the issue's session summary; this file is the cross-issue index.
- Prefer the smallest capable environment: CI for anything a workflow already runs; a Codespace/cloud session for Docker/network; the human's machine only for AWS applies and secrets.
- After a run, paste the result on the issue (and tick here). Keep this file to **open** items only.
