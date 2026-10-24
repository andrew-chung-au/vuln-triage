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
`make test` (`tests/test_manage.py`). The CI `alert` job for
`.github/workflows/verify.yml` is **uncommitted pending human approval** (exact
diff in the Engineer comment on #159). **No new dependency; `backend/uv.lock`
unchanged.**

- [ ] (CI route 1, or Codespace / cloud / Docker host) `make test-compose JOB=alert` is green: it brings up `compose.yaml` + `compose.telemetry.yaml` + `compose.alert.yaml` under the `vt-alert` project, seeds an overdue top-tier job with the in-container seam, and passes the A-* cases; then the rule-absent negative pass passes. Wire the CI `alert` job (the proposed `.github/workflows/verify.yml` change) once approved and confirm it is green on the PR. Expect the `VERIFY:` shapes to need a fix on the first real run — that is normal.
- [ ] `VERIFY:` the exact `GF_SMTP_*` keys on `grafana/grafana:11.3.0` and that `mailhog/mailhog:v1.0.1` accepts Grafana's SMTP with no auth / no TLS (the human-email alert is delivered by Grafana, not the backend; wired in `compose.alert.yaml`).
- [ ] `VERIFY:` Grafana 11.3.0 `NoData` semantics for A-GAP part 2 — that stopping the Collector long enough makes `noDataState: Alerting` fire ONE instance with no `finding_id`, routed to the human email only (the `finding_id =~ ".+"` matcher excludes it) while the finding's own instance is unchanged; and the exact number of missing evaluations needed. Set `VT_COMPOSE_POLL_TIMEOUT` accordingly (default 240 here).
- [ ] `VERIFY:` Grafana 11.3.0's webhook POST shape to the responder destination — that the body carries the `finding_id`/`tier` labels (and NOT advisory text, owner contact, URL or credential), and the top-level/per-alert `status: firing|resolved`. `compose_alert.webhook_finding_ids` / `test_compose_alert._is_firing` read the common shape and fall back to scanning the raw JSON; adjust if the shape differs.
- [ ] `VERIFY:` end-to-end firing latency on the stack (gauge scrape + ≥ one 1-minute rule evaluation + notification); confirm the poll timeout has headroom, and that `repeat_interval: 8760h` does not re-send within a run (A-RESOLVE: one firing + at most one resolved, the resolved message not counted as a second alert, D1 option 1).
- [ ] `VERIFY:` that overriding the imported `grafana` service (env + the provisioning/dashboards volumes) from `compose.alert.yaml` as a third `-f` file works on the pinned CI Compose version (compose-go PR #559 fixed the old "conflicts with imported resource" bug). If a pinned version still errors, move the Grafana SMTP override into `compose.telemetry.yaml` (it does the `include`), guarded by the `GF_SMTP_*`/`VT_ALERT_*` env being empty for the telemetry job.
- [ ] `VERIFY:` the A-FIRE-negative toggle — that Grafana provisions cleanly with the rule file absent from the `VT_ALERT_PROVISIONING` copy (no rule = no firing, not an error), and that `up -d --force-recreate --no-deps grafana` reloads it mid-run.
- [ ] Also under `make verify` (no Docker): `tests/test_manage.py` covers the seam (`alert-seed`/`alert-set`/`alert-rescore`/`alert-clear`) against `compute_overdue_series` on SQLite, and `tests/test_marker_hygiene.py` now allows `test_compose_alert.py` to carry `compose` (the two allowed modules).
- [ ] Protected-file approval: the `.github/workflows/verify.yml` `alert` job (mirrors `telemetry`) is proposed in the Engineer comment and must be human-approved before it is committed (`HUMAN_APPROVED=1`) and before #159 closes. The `Makefile` already wires `COMPOSE_JOBS=alert` (no Makefile change).
- [ ] Note: `I-OWNER-SENDER` MailHog form and `T-E6` stay follow-ups (Out of scope in #159).
- [ ] Close #159 when `make test-compose JOB=alert` (both passes) is green in CI with the approved `alert` job.

---

## Convention

- An item here is the agent saying "I wrote and offline-checked this; it needs a real run I can't do." The agent records the same steps in the issue's session summary; this file is the cross-issue index.
- Prefer the smallest capable environment: CI for anything a workflow already runs; a Codespace/cloud session for Docker/network; the human's machine only for AWS applies and secrets.
- After a run, paste the result on the issue (and tick here). Keep this file to **open** items only.
