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

---

## Convention

- An item here is the agent saying "I wrote and offline-checked this; it needs a real run I can't do." The agent records the same steps in the issue's session summary; this file is the cross-issue index.
- Prefer the smallest capable environment: CI for anything a workflow already runs; a Codespace/cloud session for Docker/network; the human's machine only for AWS applies and secrets.
- After a run, paste the result on the issue (and tick here). Keep this file to **open** items only.
