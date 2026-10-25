# Rubric evidence

Status of each of the 12 criteria (24 points, 10 to pass) in `_docs/rubric.md`,
with links to evidence that exists now. Only the Rubric Evidence Auditor
(`.opencode/agents/rubric-auditor.md` and `.claude/agents/rubric-auditor.md`,
via the `update-rubric-evidence` skill) updates this file. Planned work does
not count, and the log's claims alone are not accepted without opening the
linked evidence.

- Audit date: 2026-10-25
- Commit audited: `fb24904` (HEAD of branch `claude/quirky-brahmagupta-uisrck`,
  verified with `git rev-parse HEAD`; it is the merge of PR #200 and equals
  `main` on GitHub). Previous audit: 2026-10-20 at `74e9cfc` (10 of 24).
- Auditor environment: Claude Code cloud session, no Docker daemon, no AWS
  credentials. Nothing below was credited from a run I made; CI evidence comes
  from the GitHub Actions run and job records read through the GitHub API.
- `_docs/rubric.md` defines 12 criteria (24 points). The auditor role files'
  "14 criteria" wording is stale (tracked in issue #10).
- Status values: MET (top point level), PARTIAL (a lower non-zero level),
  MISSING (0 points).
- **Points currently evidenced: 17 of 24 (pass mark 10).**
- Rule applied this audit: anything that needs a real run that has not happened
  (AWS deploy, a live Grafana look, a Docker run nobody recorded) is scored at
  the level the repo proves, and the missing evidence is named in the gap.

## Score table

| # | criterion | max | score | status |
|---|---|---|---|---|
| 1 | Problem Description | 2 | 2 | MET |
| 2 | Product Specification | 2 | 2 | MET |
| 3 | Agent Team Specification | 2 | 2 | MET |
| 4 | Context Management | 2 | 2 | MET |
| 5 | Application | 2 | 2 | MET (lowest-confidence MET, see gap) |
| 6 | Testing | 2 | 2 | MET |
| 7 | Containerization | 2 | 1 | PARTIAL |
| 8 | Deployment | 2 | 1 | PARTIAL |
| 9 | CI/CD | 3 | 1 | PARTIAL |
| 10 | Observability | 2 | 1 | PARTIAL |
| 11 | Alerting on User Impact | 1 | 1 | MET |
| 12 | On-Call Agent | 2 | 0 | MISSING |
| | **Total** | **24** | **17** | |

## Evidence by criterion

| criterion | max points | full-marks condition | status | evidence | gap |
|---|---|---|---|---|---|
| 1. Problem Description | 2 | "The README clearly describes the problem, the system functionality, and expected behavior." | MET (2) | `README.md` at `fb24904`: "The problem" (lines 54-64), "What it does" (66-82) and "Expected behaviour" (84-92) state the problem, functionality and expected behaviour; the reviewer table (lines 28-45) maps each rubric criterion to evidence. | None for the level. Caution: README line 7 says the on-call responder is implemented, and line 12/45/193 describe it as working; no responder exists (criterion 12). That is an overclaim a grader can check; fix the wording or build the responder. The Screenshots section (lines 135-141) links `docs/images/*.png`, which are not in `git ls-files`. |
| 2. Product Specification | 2 | "A specification exists and there's a publicly accessible task tracker. The tasks define acceptance criteria and there's evidence that the agents used the tracker." | MET (2) | Spec `_docs/specs.md` (US-1 to US-15, each with an Acceptance line; edge cases). Public tracker https://github.com/andrew-chung-au/vuln-triage/issues (public repo, issues enabled, confirmed 2026-10-20 and the issue API answered in this audit). Issues carry "## Acceptance criteria" sections (for example #137, read in this audit). Agent use: role-labelled comments on earlier issues (#1, #2, #13 linked in the previous audit) and `_session-summaries/issue-*.md` for #137, #138, #139, #141, #154, #155, #157, #159, #193, #194, #195, #198; PRs #147 (closes #137) and #200 reference issues. | None for the level. Weak spot: #137 has zero comments and unticked acceptance boxes, so the tracker trail for the Compose task is the PR and summary, not issue comments. |
| 3. Agent Team Specification | 2 | "The project defines the agent team and process of how they work together." | MET (2) | `_docs/agent-team.md` (roles, tool/model, QA independence, lifecycle); `_docs/agent-kit/process.md`; role files `_docs/agent-kit/team/pm.md`, `software-engineer.md`, `qa-engineer.md`; tool definitions in `.claude/agents/` and `.opencode/agents/`. | None for the level. The stale "14 criteria" wording (issue #10) is a documentation inconsistency only. |
| 4. Context Management | 2 | "AGENTS.md exists and it also points to modular docs (process, teams, etc.)." | MET (2) | `AGENTS.md` "Where to read more" links `README.md`, `_docs/project-brief.md`, `_docs/specs.md`, `_docs/rubric.md`, `_docs/roadmap.md`, `_docs/reviews/`, `_docs/agent-kit/process.md`, `_docs/agent-kit/team/`, `_docs/agent-team.md`, `_docs/agent-kit/procedures/`, `_docs/agent-kit/environments.md`, `_docs/ai-usage-log.md`, `_docs/human-tasklist.md`; `CLAUDE.md` imports `AGENTS.md`. | None for the level. |
| 5. Application | 2 | "Full-stack application works end to end: frontend talks to backend, data persists in a database. Application runs locally with a single command." | MET (2) | Backend `backend/vulntriage/` (FastAPI, SQLAlchemy models, Alembic migrations `0001`, `0002`); frontend `frontend/src/services/index.ts` line 10 sets `services = httpServices` (the mock is no longer the default); `Makefile` line 191 `dev` target (migrate, then backend on SQLite plus Vite, no Docker). Backend end to end on Postgres is shown by CI: telemetry job log at `fb24904` (https://github.com/andrew-chung-au/vuln-triage/actions/runs/40188742150, job 121154986870) logs "created user 'telemetry-lead'", "T-JOURNEY-BE: registered asset '1'; driving the journey" and "3 passed" (login and `POST /assets` over HTTP, scan, notification, Postgres via Compose). `postgres-integration` and `openapi-validation` (OpenAPI conformance) jobs are green in the same run. | No recorded run of `make dev` or of the browser reaching the backend through the nginx `/api` proxy; the frontend-to-backend link is evidenced by the typed HTTP client, `frontend/src/test/http-service.test.ts` and the OpenAPI conformance job, not by a live UI session. To harden: record one `make dev` (or `make compose-up`) session with a login and a dashboard screenshot. |
| 6. Testing | 2 | "Both unit and integration tests exist, run with a single command, and pass." | MET (2) | `make test` (`Makefile` line 112) runs vitest and pytest; CI `verify` job runs `make verify` and passed at `fb24904` (job 121154986929, run 40188742150); the same run is green for `unit` (U-* cases), `sqlite-integration` (I-* on SQLite), `postgres-integration` (`make test-integration`, real Postgres), `frontend` (tests and typecheck), `openapi-validation`. `tests/` holds 30+ test modules plus Compose cases. Test counts in the usage log (496 backend, 88 frontend) were not re-counted by me; the green CI jobs are the evidence. | None for the level. Note the Postgres suite is a separate command (`make test-integration`), not part of `make test`; the criterion is met because `make test` itself includes SQLite integration cases. |
| 7. Containerization | 2 | "The full system, including the database, runs via Docker or Docker Compose and starts with a single command." | PARTIAL (1) | `backend/Dockerfile`, `frontend/Dockerfile`, `compose.yaml` (services `db` Postgres 16.4 with named volume, `migrations`, `backend`, `frontend`, health checks, `depends_on`), `Makefile` line 223 `compose-up` (`docker compose up --build -d --wait`). CI starts `compose.yaml` plus overrides with one command (`make test-compose JOB=telemetry`, green at `fb24904`) but with `up -d --wait db migrations ... backend`, so the `frontend` service is never started (`ci/test-compose.sh` line 103). The deploy workflow builds and pushes the frontend image successfully (run 40188742170, job `build-and-push`), which shows the image builds, not that it serves. `_session-summaries/issue-137-compose-stack.md` lines 47-53 hand `make compose-up` to the human to verify; issue #137 is closed with no comment recording that run, and its acceptance boxes are unticked. | Not yet evidenced: a recorded run of `make compose-up` with all four services healthy, the SPA answering on `http://localhost:8080`, and data surviving a restart. Cheapest fix: run it in a Docker-capable cloud session or Codespace and post the output on #137 (or add `frontend` to a CI job). |
| 8. Deployment | 2 | "The application is deployed and reachable at a public URL, or there's a clear demo with the deployment." | PARTIAL (1) | Deployment steps are described: `README.md` "Deployment & rollback" (lines 165-175), `_docs/aws-setup.md`, `_docs/terraform-verify.md`, `terraform/` (bootstrap, deploy-roles, server), `.github/workflows/deploy.yml`. No working deployment is shown: README line 171 states the first live deploy is a human step; `_docs/human-tasklist.md` section A (A1-A13) is entirely unticked; and every `deploy` workflow run on `main` ends `failure` (run 40188742170 at `fb24904`: job `deploy-dev`, step "Assume the dev deploy role" failed with "Input required and not supplied: aws-region", so the `AWS_REGION` and `AWS_DEV_ROLE_ARN` variables are not set). No public URL or demo recording is committed (README demo and URL placeholders are comments). | Not yet evidenced: `terraform apply` of the three modules, the GitHub variables set, a green `deploy-dev` run, and `https://dev.<elastic-ip>.sslip.io` answering (or a recorded demo of it). Needs the human's AWS identity (#141, tasklist A1-A9). |
| 9. CI/CD | 3 | "CI runs tests, CD deploys to dev, and there's a manual deploy to production." | PARTIAL (1) | CI on every pull request: `.github/workflows/verify.yml` triggers `on: [push, pull_request]`; PR run https://github.com/andrew-chung-au/vuln-triage/actions/runs/40188575862 (event `pull_request`, PR #200) concluded `success`, with seven jobs (unit, sqlite-integration, frontend, openapi-validation, postgres-integration, telemetry, verify). That is the 1-point level. CD is authored but not working: `deploy.yml` has `build-and-push` (green: images pushed to GHCR with digests, run 40188742170), `deploy-dev` (automatic on push to `main`, `environment: dev`) and `deploy-prod` (`workflow_dispatch`, `environment: production`, human reviewer). `deploy-dev` has failed on all recent `main` pushes (runs 40188742170, 40174812369, 40171835930, 40165543718, 40165055818) at the AWS role step, and `deploy-prod` has never run (skipped in the push run). | Not yet evidenced for 2 points: one green `deploy-dev` run that deploys (needs the AWS apply and variables, tasklist A6-A9). Not yet evidenced for 3 points: one approved `deploy-prod` run (tasklist A12). Also, each push to `main` now shows a red `deploy` run, which a grader reading the Actions tab will see; set the variables or gate the job until AWS exists. |
| 10. Observability | 2 | "A key user journey is instrumented with metrics, traces, and structured logs that share a trace ID; no customer data or credentials are sent to telemetry; and the signals are collected, stored, and viewable in a UI." | PARTIAL (1) | Instrumented and correlated, shown by CI: `backend/vulntriage/observability/` (tracing, metrics, logs, allowlist); `observability/` stack (Collector, Prometheus, Tempo, Loki, Grafana, provisioned datasources and the US-13 dashboard `observability/grafana/dashboards/us13-journey.json`). Telemetry job at `fb24904` (job 121154986870): `3 passed in 55.02s`, including `T-REFUSE` ("helper path sent excluded keys to Collector: []"; the case also asserts excluded values are absent from Tempo and Loki) and `T-JOURNEY-BE` (journey trace id `82b6f68eb8b0b5b7ffa97eb739b6ef79`; `tests/test_compose_telemetry.py` lines 205-216 assert the Tempo span list, the `vt_notifications_total{vt_outcome="sent"}` metric, and a Loki log line carrying that trace id). `tests/test_us13_dashboard.py` statically checks the dashboard queries. | Not yet evidenced: "viewable in a UI". The Grafana dashboard has never been looked at on a running stack: `_docs/pending-verification.md` #155 and the cloud-queue item #199 are unticked, and no screenshot is committed (README images are placeholders). Also: the metric is matched by name and outcome, not by trace id (no exemplar), so the shared-trace-id claim rests on trace plus log. Tick the `#172`/`#155` items now that the CI Loki leg passed, and take the Grafana dashboard screenshot. |
| 11. Alerting on User Impact | 1 | "At least one alert exists." | MET (1) | Provisioned Grafana rule `observability/grafana/provisioning/alerting/us14-overdue.yaml` (undelivered top-priority finding, from the `vt_top_tier_notification_overdue` metric, tested by `tests/test_metrics_overdue.py`). The rule fired in real Grafana in CI: `alert` job (`make test-compose JOB=alert`) concluded `success` in run https://github.com/andrew-chung-au/vuln-triage/actions/runs/40160976080 at `79f9f47` (job 121072278559), with A-FIRE and the rule-absent negative; `git log 79f9f47..HEAD -- observability/grafana/provisioning/alerting` is empty, so the rule is unchanged since that run. `_docs/pending-verification.md` lines 158-163 record the same. | The run predates the trim to A-FIRE only (`4ba7e52`); the nightly `alert.yml` workflow has zero runs so far (checked through the API). One manual run (Actions, alert, Run workflow) would show the current state. Does not affect the point. |
| 12. On-Call Agent | 2 | "An agent wakes up on an alert and fixes the issue." | MISSING (0) | No responder agent exists. `ci/test-compose.sh` lines 209-217 and `.github/workflows/verify.yml` (comment at lines 76-77) show `JOB=responder` as "not implemented" (task 28, #160); there is no responder agent definition, webhook receiver, `VT_DEMO_DEFECT` driver in `backend/` (only `ingest/settings.py` mentions the setting) and no recorded run. The Grafana rule's responder webhook is delivered only to a stub sink in the alert test (`tests/alert_webhook_sink.py`). | A responder agent woken by the US-14 alert webhook that reproduces the notification defect, opens a fix PR with a test, and logs its actions (task 28 / #160, then the recorded run, task 39). The runtime and credentials decision is still open (roadmap line 128). |

## Corrections to earlier claims

- `_docs/pending-verification.md` (#172 and #193 sections) still lists
  `T-JOURNEY-BE` and the Loki leg as unticked. The CI telemetry job at
  `fb24904` ran both and passed (see criterion 10), so those boxes can be ticked
  with the run link; the held-job Loki case remains optional and unverified.
- README (line 7 and the criterion 12 row) claims the on-call responder is
  implemented; the repo shows it is not (criterion 12).

## Top three gaps (priority order, by points gained per effort)

1. **Containerization +1, Observability +1 (about 2 points, small effort, no
   AWS).** Both are one Docker-capable session away. Run `make compose-up`
   with all four services healthy and post the output on #137 (or add the
   frontend to a CI job); bring up `observability/`, open the US-13 Grafana
   dashboard, take a screenshot and post it on #155/#199. Also tick the
   now-green `T-JOURNEY-BE` items.
2. **Deployment +1, CI/CD +1 to +2 (up to 3 points, moderate effort, needs the
   human's AWS identity).** One chain of human steps unlocks all of it: apply
   the Terraform modules, set `AWS_REGION`, `AWS_DEV_ROLE_ARN`,
   `AWS_PROD_ROLE_ARN`, re-run the `deploy` workflow until `deploy-dev` is
   green and the dev URL answers (Deployment 2, CI/CD 2), then run and approve
   one `deploy-prod` (CI/CD 3). This is `_docs/human-tasklist.md` A1-A12.
3. **On-Call Agent +2 (highest effort).** Build the responder (task 28 /
   #160) and record one alert-to-PR run. It is the only criterion at 0.
   Fix the README claim at the same time if it is not built before
   submission.
