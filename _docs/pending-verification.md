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

See `_docs/human-tasklist.md` for the prioritised roll-up of **all** human
action (this file + the AWS setup, merges and sweeps); this file is the detailed
per-issue checklist it links to for the verification runs.

Last updated: 2026-10-25 (#193: held-delivery signals, Loki leg recorded; #180: #177 folded into #193; #159 alert job: CI job committed; cross-ref to verify-locally.md §7b)

## Cloud-session queue (Docker work to hand to Claude Code cloud sessions)

Added 2026-10-25 at the human's direction: work the local sandbox can't do for
lack of Docker goes to a Claude Code cloud session (`_docs/cloud-sessions.md`;
one session per issue, credit is limited). Each line is a candidate, not a
started job.

- **#181** (T-E6, telemetry backend down): groomed, PM decisions Q1-Q3 still open (see the #181 comments). Author and run it in the cloud.
- **#182** (`I-OWNER-SENDER` MailHog form): follows #160 (task 28).
- **#199** (US-13 dashboard live Grafana check, split from #195 on 2026-10-25): needs a running Grafana; shares the dashboard with #181, so sequence them. #195 is now the static fix and test, done locally.
- **#172 / #174 / #193** (`T-JOURNEY-BE` Loki leg, plus the optional held-job case): run the `telemetry` job and add the held-job case.
- **#157** (`T-REFUSE` run and negative check), **#155** (dashboard and MailHog check), **#158** (Grafana rule run): verification only.
- **#140** (security scan, PR #167): needs network to generate the fixture lockfiles.
- **Human machine, not cloud:** AWS applies and secrets (#141, `human-tasklist.md` §A).

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

## #157 — telemetry Compose test + `make test-compose` selector (task 25)

PR: (this change). #157 ships the `make test-compose` + `JOB` selector (a
protected `Makefile` change) and the single telemetry case **`T-REFUSE`**; the
delivery-dependent cases move to #172 (they need the deployed backend container
to deliver). The `telemetry` job is **Docker-only** — it runs the backend's
span/log helpers against the `observability/` stack (Collector →
Prometheus/Tempo/Loki) — so it is authored here and **verified by the human in a
Codespace / Claude Code cloud / Docker host, or by CI (route 1)**. `make verify`
in the sandbox is unaffected: the case is `compose`-marked and **deselected** by
`make test` / `make verify` (so it never runs and never *skips* in the no-Docker
gate), and `tests/test_marker_hygiene.py` guards against an ordinary test being
silently tagged `compose`. The harness is `ci/test-compose.sh`; the case is
`tests/test_compose_telemetry.py` (helpers in `tests/compose_telemetry.py`,
driver in `tests/compose_driver.py`). **No new dependency; `backend/uv.lock`
should not change.**

- [ ] (CI route 1, or Codespace / cloud / Docker host) `make test-compose JOB=telemetry` is green: it brings up the observability stack under the `vt-telemetry` project, runs the backend driver's `refuse` command against it, and passes `T-REFUSE` (the only telemetry case #157 ships). Wire the CI `telemetry` job (added to `.github/workflows/verify.yml`) and confirm it is green on the PR. Expect the `VERIFY:` query shapes to need a fix on the first real run — that is normal.
- [ ] Confirm `T-REFUSE` fails when `owner.email` is added to the Collector allowlist (`observability/otel-collector.yaml`) — the task-25 acceptance negative check.
- [ ] `VERIFY:` the external query shapes marked in `tests/compose_telemetry.py` on the pinned images: Tempo trace-by-id `/api/traces/{id}` and its span-attribute JSON nesting (2.6.1), and Loki `/loki/api/v1/query_range` with the stream selector for OTLP-ingested logs (3.2.1). Adjust the helpers if a shape differs. (Prometheus/MailHog helpers were trimmed out of #157; they return with the delivery cases in #172.)
- [ ] `VERIFY:` a host pytest/driver process exports OTLP over the published Collector port (`localhost:4317` gRPC) and reaches Tempo/Loki on their published localhost ports. For `T-REFUSE` the driver runs on the host (no containerized delivery needed), so the two Compose projects do not need a shared network here; #172 adds that wiring for the containerized-backend-delivers cases.
- [ ] Note: the delivery-dependent cases — `T-JOURNEY-BE`, the MailHog forms of `I-OWNER-NOAWS`/`I-OWNER-SENDER`, `T-E6` and `T-DELIVER-TRACE` — are **not** in #157; they need the deployed backend container to deliver and are prerequisite **#172**. The `alert` and `responder` jobs are tasks 27 (#159) and 28 (#160); `make test-compose JOB=alert|responder` exits 3 with a "not implemented in #157" message until those land.
- [ ] Also under `make verify` (no Docker): `tests/test_marker_hygiene.py` fails if the `compose` marker appears outside the allowed compose modules — the guard that stops an ordinary backend test being silently dropped from `make test`.
- [ ] Close #157 when `make test-compose JOB=telemetry` (`T-REFUSE`) is green in CI (its acceptance criteria were narrowed to `T-REFUSE` + the selector on 2026-10-24; #172 carries the delivery cases and `T-JOURNEY-BE`).

## #159 — the `alert` Compose test + CI `alert` job (task 27)

Branch: `feat/159-alert-compose-job`. #159 adds the US-14 `alert` job: the
firing-state seam (`backend/vulntriage/manage.py` `alert-*`), a stdlib stub
webhook sink (`tests/alert_webhook_sink.py`), the alert helpers
(`tests/compose_alert.py`), the `compose`-marked A-* cases
(`tests/test_compose_alert.py`), the Compose override (`compose.alert.yaml`), and
the `ci/test-compose.sh` `alert` branch. The job is **Docker-only** — it runs the
app + observability + webhook-sink stack and drives firing from stored job state
through the task-26 Grafana rule — so it is authored here and **verified by the
human/CI under Docker**. `make verify` in the sandbox is unaffected: the cases are
`compose`-marked and deselected, and the seam's own logic is covered under
`make test` (`tests/test_manage.py`). The CI `alert` job in
`.github/workflows/verify.yml` was **human-approved and committed**
(`HUMAN_APPROVED=1`, commit `adf3733`, mirrors the `telemetry` job). **No new
dependency; `backend/uv.lock` unchanged.** How to run the job locally:
`_docs/verify-locally.md` §7b.

Scope change (human decision, 2026-10-25): the Compose job now runs only
`A-FIRE` and its rule-absent negative, nightly and on demand rather than on every
push/PR. `A-HELD`, `A-TIER`, `A-GAP` part 1 and `A-RESOLVE`'s `sent` → 0 are
unit/SQLite cases; `A-GAP` part 2 and `A-RESOLVE`'s Grafana half are manual
checks. See `_docs/testing.md`, "Where each case runs".

- [x] `make test-compose JOB=alert` green in CI with both passes, including the rule-absent negative: run 40160976080 (pull_request, at `79f9f47`), with the full A-* list before the trim.
- [x] `GF_SMTP_*` keys on `grafana/grafana:11.3.0` and MailHog accepting Grafana's SMTP with no auth / no TLS: confirmed (A-FIRE's human email reached MailHog in CI).
- [x] Grafana 11.3.0 webhook POST shape: confirmed. Per-alert `labels` are exactly `alertname`, `finding_id`, `grafana_folder`, `tier`; the top-level `status` is `firing`/`resolved`. A missing series resolves with `grafana_state_reason=MissingSeries` about two evaluations after it leaves Prometheus.
- [x] Overriding the imported `grafana` service from `compose.alert.yaml` as a third `-f` file works on the CI Compose version.
- [x] The A-FIRE-negative toggle: Grafana provisions cleanly with the rule absent and nothing fires (run 40160976080).
- [x] Grafana 11.3.0 `NoData` for a Collector gap: fires one human-only instance with no `finding_id` (A-GAP part 2 passed in CI before the trim; now a manual check, `_docs/verify-locally.md` §7b).
- [ ] Protected-file approval: the `.github/workflows/verify.yml` change that moves the `alert` job to nightly + `workflow_dispatch` (not on push/PR).
- [ ] After merge: run the alert job once from Actions (verify → Run workflow) and confirm it is green with the trimmed cases.
- [ ] Also under `make verify` (no Docker): `tests/test_manage.py` covers the seam (`alert-seed`/`alert-set`/`alert-rescore`/`alert-clear`) against `compute_overdue_series` on SQLite, and `tests/test_marker_hygiene.py` now allows `test_compose_alert.py` to carry `compose` (the two allowed modules).
- [x] Protected-file approval: the `.github/workflows/verify.yml` `alert` job (mirrors `telemetry`) was human-approved and committed (`HUMAN_APPROVED=1`, commit `adf3733`). The `Makefile` already wires `COMPOSE_JOBS=alert` (no Makefile change).
- [ ] Note: `I-OWNER-SENDER` MailHog form and `T-E6` stay follow-ups (Out of scope in #159).
- [ ] Close #159 when the trimmed `alert` job (both passes) is green from a manual or nightly run.

## #172 — feed-client wiring + VT_FEEDS fixture mode (task 40)

PRs: #175, #178 (merged). Run in **CI (telemetry job) or a Codespace / Claude
Code cloud / Docker host** (Docker). This is the containerized-backend-delivers
harness that carries `T-JOURNEY-BE` and the MailHog `I-OWNER-*` forms.

- [ ] `make test-compose JOB=telemetry` green with the containerized backend delivering: `T-JOURNEY-BE` asserts one trace id across the Prometheus metric, the Tempo trace **and the Loki log**, and `I-OWNER-NOAWS` lands the owner email in MailHog.
- [ ] **Also confirms #174 and the log half of #177** (US-13 log leg). `T-JOURNEY-BE`'s Loki assertion is the only end-to-end proof that the backend (a) exports logs over OTLP (#174, `observability/logs.py::setup_logging`, commit `61837cb`) and (b) actually calls `log_event` on the scan/delivery journey (#177, `scan.finished` + `notification.deliver`, commit `970cdbf`; #177 was folded into #193 and closed on 2026-10-25). If this Loki leg does **not** carry the journey trace id, re-open #174 or #193 rather than only #172.
- [ ] Watch for the known flake #185 (Tempo search drops leading zeros → `len(trace_id) == 32` fails ~1/16 runs); normalise the id where it is read from Tempo.
- [ ] Close #172 when the telemetry CI job is green with `T-JOURNEY-BE` + `I-OWNER-NOAWS`.

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
