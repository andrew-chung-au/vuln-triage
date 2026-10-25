# Rubric evidence

Status of each of the 12 criteria (24 points, 10 to pass) in `_docs/rubric.md`,
with links to evidence that exists now. Only the Rubric Evidence Auditor
(`.opencode/agents/rubric-auditor.md` and `.claude/agents/rubric-auditor.md`,
via the `update-rubric-evidence` skill) updates this file. Planned work does
not count, and the log's claims alone are not accepted without opening the
linked evidence.

- Audit date: 2026-10-25 (second audit of the day, after the first AWS
  deployment)
- Commit audited: `234cccf` (HEAD of branch `claude/quirky-brahmagupta-uisrck`,
  PR #207, verified with `git rev-parse HEAD`). The deployed code is `main` at
  `215ea78` (merge of PR #206). Previous audits: 2026-10-25 at `fb24904`
  (17 of 24) and 2026-10-20 at `74e9cfc` (10 of 24).
- Auditor environment: Claude Code cloud session, no Docker daemon, no AWS
  credentials, and an egress proxy that blocks `*.sslip.io`. This is a limit of
  the audit sandbox, not of the deployment: the live URLs were not fetched from
  here. That both URLs load was confirmed in person by the project owner, who
  operates the deployment, and is cited below as **owner-confirmed**. CI and
  deploy evidence comes from the GitHub Actions run, job and log records read
  through the GitHub API.
- `_docs/rubric.md` defines 12 criteria (24 points). The auditor role files'
  "14 criteria" wording is stale (tracked in issue #10).
- Status values: MET (top point level), PARTIAL (a lower non-zero level),
  MISSING (0 points).
- **Points currently evidenced: 21 of 24 (pass mark 10).** Two items are
  confirmed by the project owner rather than by a record this audit could
  read: that both live URLs load, and the `production` environment's reviewer
  rule. They are marked **[owner-confirmed]** below and listed in "Items
  confirmed by the owner". Nothing in the records contradicts either: the
  deploy logs show healthy services and an approval wait on the production runs.
- Rule applied this audit: count what the repo and the Actions records show;
  where a record cannot show a fact (a page loading in a browser, a GitHub
  settings page), cite the owner's confirmation and say so.

## Score table

| # | criterion | max | score | status | change since 17/24 |
|---|---|---|---|---|---|
| 1 | Problem Description | 2 | 2 | MET | none |
| 2 | Product Specification | 2 | 2 | MET | none |
| 3 | Agent Team Specification | 2 | 2 | MET | none |
| 4 | Context Management | 2 | 2 | MET | none |
| 5 | Application | 2 | 2 | MET | none (more supporting evidence) |
| 6 | Testing | 2 | 2 | MET | none |
| 7 | Containerization | 2 | 2 | MET | +1 (deploy logs show the four-service Compose project healthy) |
| 8 | Deployment | 2 | 2 | MET [URLs owner-confirmed] | +1 |
| 9 | CI/CD | 3 | 3 | MET [production gate owner-confirmed] | +2 |
| 10 | Observability | 2 | 1 | PARTIAL | none |
| 11 | Alerting on User Impact | 1 | 1 | MET | none |
| 12 | On-Call Agent | 2 | 0 | MISSING | none |
| | **Total** | **24** | **21** | | **+4** |

## Evidence by criterion

| criterion | max points | full-marks condition | status | evidence | gap |
|---|---|---|---|---|---|
| 1. Problem Description | 2 | "The README clearly describes the problem, the system functionality, and expected behaviour." | MET (2) | `README.md` at `234cccf`: "The problem" (lines 54-64), "What it does" (66-82) and "Expected behaviour" (84-92) state the problem, functionality and expected behaviour; the reviewer table (lines 28-45) maps each rubric criterion to evidence. The earlier overclaim is fixed: README line 7, line 45, lines 76 and 237 now say the on-call responder is "planned, not built yet" (checked against criterion 12). The two screenshots `docs/images/dashboard.png` and `docs/images/assets.png` are now tracked (`git ls-files`). | None for the level. One new inconsistency: README line 7 still says "the production promotion has not been done yet", but lines 213-215 say production is live and the rollback was rehearsed. Update line 7. Line 148 says the demo "may be stopped overnight"; the nightly stop is off (`_session-summaries/planning-2026-10-25-aws-deployment.md` line 32), so either is safe but they should agree. |
| 2. Product Specification | 2 | "A specification exists and there's a publicly accessible task tracker. The tasks define acceptance criteria and there's evidence that the agents used the tracker." | MET (2) | Spec `_docs/specs.md` (US-1 to US-15, each with an Acceptance line; edge cases). Public tracker https://github.com/andrew-chung-au/vuln-triage/issues (public repo, issue API answered in this audit). Issues carry "## Acceptance criteria" sections: #141 and #143 read in this audit, each with five checkbox criteria. Agent use: role-labelled comments on earlier issues, `_session-summaries/issue-*.md` for #137 to #198, and PRs that reference issues (#187 closes #143). | None for the level. Weak spot: #143 is closed (by PR #187) with every acceptance box unticked, and #141 is still open with two comments; the production and dev deploys that satisfy their "Check" lines (runs below) are recorded in `_docs/human-tasklist.md`, not as issue comments. Closing #141 and #143 with run links would tighten the trail. |
| 3. Agent Team Specification | 2 | "The project defines the agent team and process of how they work together." | MET (2) | `_docs/agent-team.md` (roles, tool/model, QA independence, lifecycle); `_docs/agent-kit/process.md`; role files `_docs/agent-kit/team/pm.md`, `software-engineer.md`, `qa-engineer.md`; tool definitions in `.claude/agents/` and `.opencode/agents/`. | None for the level. The stale "14 criteria" wording (issue #10) is a documentation inconsistency only. |
| 4. Context Management | 2 | "AGENTS.md exists and it also points to modular docs (process, teams, etc.)." | MET (2) | `AGENTS.md` "Where to read more" links `README.md`, `_docs/project-brief.md`, `_docs/specs.md`, `_docs/rubric.md`, `_docs/roadmap.md`, `_docs/reviews/`, `_docs/agent-kit/process.md`, `_docs/agent-kit/team/`, `_docs/agent-team.md`, `_docs/agent-kit/procedures/`, `_docs/agent-kit/environments.md`, `_docs/ai-usage-log.md`, `_docs/human-tasklist.md`; `CLAUDE.md` imports `AGENTS.md`. | None for the level. |
| 5. Application | 2 | "Full-stack application works end to end: frontend talks to backend, data persists in a database. Application runs locally with a single command." | MET (2) | Backend `backend/vulntriage/` (FastAPI, SQLAlchemy, Alembic); frontend `frontend/src/services/index.ts` uses `httpServices`; `Makefile` `dev` target (migrate, then backend on SQLite plus Vite, no Docker) and the new `demo` target (commits `7beafd9`, `936ca53`). CI shows the backend end to end on Postgres: telemetry job at `fb24904` (run 40188742150, job 121154986870) logs a login, `POST /assets`, a scan and a notification. New this audit: the deploy logs show the full stack running on a server, not only in CI. Dev deploy job https://github.com/andrew-chung-au/vuln-triage/actions/runs/40209680272/job/121218249980 (run #30) logs `dev-db-1`, `dev-migrations-1` (Exited after running), `dev-backend-1` and `dev-frontend` all Healthy. The session summary and tasklist A13 say four assets were registered and scanned through the live API and the dashboard lists findings **[owner-confirmed]**. README now carries two committed screenshots from a real `make dev` session (`docs/images/*.png`). | No recorded run I could re-check of the browser reaching the backend. The live UI (sign-in page, seeded findings) is owner-confirmed; the audit sandbox could not open it. The recorded evidence of the link is the typed HTTP client, `frontend/src/test/http-service.test.ts`, the OpenAPI conformance job and the CI telemetry journey. To harden: link the two screenshots to a dated `make demo` run in a session summary. |
| 6. Testing | 2 | "Both unit and integration tests exist, run with a single command, and pass." | MET (2) | `make test` runs vitest and pytest. CI `verify` workflow on this PR head is green: https://github.com/andrew-chung-au/vuln-triage/actions/runs/40214720806 (event `pull_request`, PR #207, `234cccf`, conclusion `success`); the earlier PR run on `fb24904` listed seven jobs (unit, sqlite-integration, frontend, openapi-validation, postgres-integration, telemetry, verify). `tests/` holds 30+ test modules plus Compose cases. Test counts in the usage log (496 backend, 89 frontend) were not re-counted by me. | None for the level. The Postgres suite is a separate command (`make test-integration`); the criterion is met because `make test` itself includes SQLite integration cases. |
| 7. Containerization | 2 | "The full system, including the database, runs via Docker or Docker Compose and starts with a single command." | MET (2) | `backend/Dockerfile`, `frontend/Dockerfile`, `compose.yaml` (`db` Postgres 16.4 with named volume, `migrations`, `backend`, `frontend`, health checks, `depends_on`), `Makefile` line 245 `compose-up` (`docker compose up --build -d --wait`). New recorded evidence: the deploy script `terraform/server/deploy-env.sh` lines 216-219 starts the app with one `docker compose ... up -d --wait`, and the Actions logs show all four services of the project reach healthy. Dev: run #30 job 121218249980 ("Container dev-db-1 Healthy ... dev-backend-1 Healthy ... dev-frontend Healthy", `final status: Success`). Production: run #33 job https://github.com/andrew-chung-au/vuln-triage/actions/runs/40213639091/job/121229992961 (same lines for `prod-*`, `final status: Success`). Images are built in CI and pushed to GHCR (run 40209680272, job `build-and-push` success). | Honest limit: what ran on the server is the deploy variant of the Compose project (`compose.yaml` plus `compose.deploy.yaml`, images from GHCR), started by the deploy script, not `make compose-up` itself, and no `make compose-up` session is recorded (issue #137 still has no comment with that run). The `frontend` health state comes from the Compose health check in the log, not from fetching the page (the page load is **[owner-confirmed]**). Optional hardening: record one `make compose-up` run on #137. |
| 8. Deployment | 2 | "The application is deployed and reachable at a public URL, or there's a clear demo with the deployment." | MET (2) **[URL reachability owner-confirmed]** | Deployment is real and recorded in Actions: Terraform modules `terraform/bootstrap`, `terraform/deploy-roles`, `terraform/server` are applied (tasklist A6: server `i-090e482680338eb75`, Elastic IP `52.206.221.145`); the deploy jobs reach that instance, for example the `prod` deploy job reads the instance state and gets `Success` from the SSM command on `i-090e482680338eb75` (run #33, job 121229992961) and Caddy `vt-caddy` is recreated and started. Public URLs documented in `README.md` (lines 143, 213): https://dev.52-206-221-145.sslip.io and https://app.52-206-221-145.sslip.io, plus a public reviewer login (README "Try it as a reviewer"). Deployment steps and rollback are in README "Deployment & rollback" and `_docs/aws-setup.md`. | The audit sandbox's proxy blocks `*.sslip.io`, so this audit did not fetch the pages. The project owner confirmed that both URLs answer over HTTPS and show the sign-in page (`_docs/human-tasklist.md` A9, A12, A14). The logs are consistent with that: all containers healthy and Caddy started on the server. Anyone can check by opening either link. Optional extra: a dated screenshot or short recording of each URL committed to the repo. Also leave the nightly stop off until after grading (tasklist A11); if it is turned on the URL goes down at 04:00 UTC. |
| 9. CI/CD | 3 | "CI runs tests, CD deploys to dev, and there's a manual deploy to production." | MET (3) **[production gate owner-confirmed; tests-before-deploy relies on branch protection]** | CI on every pull request: `.github/workflows/verify.yml` triggers on push and pull_request; PR run https://github.com/andrew-chung-au/vuln-triage/actions/runs/40214720806 is `success`. CD to dev, automatic on merge to `main`: `deploy.yml` push run #30 (https://github.com/andrew-chung-au/vuln-triage/actions/runs/40209680272, event `push`, merge of PR #206): `build-and-push` success, `deploy-dev` success (steps "Assume the dev deploy role", "Read the server's instance state", "Deploy the dev Compose project (SSM Run Command)", "Record the dev deploy" all green; image tag `20261025-160125-215ea78` with backend digest `sha256:fe2412ef7ffe...` in the job log). An earlier push run, #29 attempt 2 (run 40206841216), also passed after the OIDC trust fix (PR #205); #26, #27 and #28 failed before that, which the history shows. Manual deploy to production: `deploy-prod` runs only on `workflow_dispatch` in `environment: production` (`deploy.yml` lines 249-252), skipped on push runs. It has run three times: #31 (https://github.com/andrew-chung-au/vuln-triage/actions/runs/40211501839, job started 3 s after creation, so ungated), #32 (https://github.com/andrew-chung-au/vuln-triage/actions/runs/40212984494, attempt 1: job created 16:42:45, started 16:43:43, 58 s waiting, then success, explicit older tag `20261025-152518-37baad0`; this is the rollback rehearsal) and #33 (https://github.com/andrew-chung-au/vuln-triage/actions/runs/40213639091, forward run, job created 16:50:55 and started 16:57:03, about 6 minutes waiting, success). The per-job timings are consistent with a reviewer approval wait. | (a) The `production` environment's Required reviewers rule with administrator bypass off was set by the project owner, who confirms it. The audit tools cannot read environment settings; the run records show the effect: the first run (#31) started 3 s after creation, and after the rule was added runs #32 and #33 waited for approval. Cheap hardening: a screenshot of the environment settings page or the run's "Review deployments" panel. (b) `deploy.yml` triggers on every push to `main` with no `needs` on `verify.yml`; "tests gated" depends on branch protection requiring the CI checks (stated in `deploy.yml` comments, not verified by me; I have no tool to read branch protection). (c) Cosmetic, but a grader reads the Actions tab: run #32 shows overall `cancelled` because attempt 2 (a re-run, cancelled after 18 s) replaced attempt 1's success, and run #34 (a duplicate queued behind #33) is `cancelled`. Point graders to attempt 1 of #32. The `deploy` history also still holds failures #25 to #28 from before AWS existed. |
| 10. Observability | 2 | "A key user journey is instrumented with metrics, traces, and structured logs that share a trace ID; no customer data or credentials are sent to telemetry; and the signals are collected, stored, and viewable in a UI." | PARTIAL (1) | Unchanged since the last audit. Instrumented and correlated, shown by CI: `backend/vulntriage/observability/`; `observability/` stack (Collector, Prometheus, Tempo, Loki, Grafana, the US-13 dashboard `observability/grafana/dashboards/us13-journey.json`). Telemetry job at `fb24904` (job 121154986870): `3 passed in 55.02s`, including `T-REFUSE` (excluded keys absent from Tempo and Loki) and `T-JOURNEY-BE` (journey trace id `82b6f68eb8b0b5b7ffa97eb739b6ef79`; Tempo span list, `vt_notifications_total{vt_outcome="sent"}` metric and a Loki log line carrying the trace id). The deployment did not add observability: the AWS server runs the app Compose project only (no Grafana there; README line 197 says the stack runs in local Compose). | Not yet evidenced: "viewable in a UI". The Grafana dashboard has never been looked at on a running stack and no screenshot is committed (README line 184 says "Not captured yet"). `_docs/pending-verification.md` #155 and #199 remain unticked. The metric is matched by name and outcome, not by trace id (no exemplar). Take the Grafana screenshot (needs a Docker-capable session). |
| 11. Alerting on User Impact | 1 | "At least one alert exists." | MET (1) | Provisioned Grafana rule `observability/grafana/provisioning/alerting/us14-overdue.yaml` (undelivered top-priority finding, from `vt_top_tier_notification_overdue`, tested by `tests/test_metrics_overdue.py`). It fired in real Grafana in CI: `alert` job in run https://github.com/andrew-chung-au/vuln-triage/actions/runs/40160976080 at `79f9f47` (job 121072278559), with A-FIRE and the rule-absent negative. `git log 79f9f47..HEAD -- observability/grafana/provisioning/alerting` is empty (checked at `fb24904`; not re-run this audit), so the rule is unchanged. | The run predates the trim to A-FIRE only (`4ba7e52`); the nightly `alert.yml` has no recorded run. One manual run would show the current state. Does not affect the point. |
| 12. On-Call Agent | 2 | "An agent wakes up on an alert and fixes the issue." | MISSING (0) | No responder agent exists. `ci/test-compose.sh` shows `JOB=responder` as "not implemented" (task 28, #160); no responder agent definition, webhook receiver or recorded run. The Grafana rule's responder webhook goes only to a stub sink in the alert test (`tests/alert_webhook_sink.py`). The README now says plainly that the responder is planned, not built (lines 7, 45, 76, 237). | A responder agent woken by the US-14 alert webhook that reproduces the notification defect, opens a fix PR with a test, and logs its actions (task 28 / #160, then the recorded run, task 39). The runtime and credentials decision (F1-F3) is still open. |

## Items confirmed by the owner

These facts cannot be read from the records available to this audit, so they
rest on the project owner's confirmation. Both are counted as MET.

1. **The live URLs load** (Deployment, criterion 8). The Actions logs show a
   healthy Compose project and Caddy on the instance; the audit sandbox cannot
   fetch the public pages. The owner confirmed both load (tasklist A9, A12,
   A14), and anyone can open the links to check.
2. **The `production` environment's Required reviewers rule and administrator
   bypass off** (CI/CD, criterion 9, the third point). The job timings (58 s for
   #32, about 6 minutes for #33, against 3 s for the ungated #31) match an
   approval wait, and the session summary records that the owner added the rule
   after #31. The settings page was not readable by the audit tools.
3. **Tests gate the dev deploy.** `deploy.yml` has no dependency on `verify.yml`;
   gating rests on branch protection, which I did not read. The dev deploy
   itself ran automatically on push (run #30), so the "CD deploys to dev" level
   is shown regardless.
4. **The seeded demo data and sign-in page** (supporting criterion 5, not
   scored on it): owner-confirmed.

Nothing in the Actions records contradicts items 1 and 2.

## Corrections to earlier claims

- README line 7 ("the production promotion has not been done yet") is stale and
  contradicts README lines 213-215. The Actions record shows production was
  promoted (runs #31, #32, #33).
- `_docs/pending-verification.md` (#172 and #193 sections) still lists
  `T-JOURNEY-BE` and the Loki leg as unticked; the CI telemetry job at
  `fb24904` ran both and passed (criterion 10).
- Session summary `planning-2026-10-25-aws-deployment.md` line 33 says the
  re-audit had not run; this file is that re-audit (21 of 24).
- The previous audit's claims that the README overstates the responder and that
  the screenshots are untracked are now resolved (criterion 1, criterion 12).

## Top three gaps (priority order, by points gained per effort)

1. **On-Call Agent +2 (highest effort, the only criterion at 0).** Build the
   responder (task 28 / #160, decisions F1-F3 first) and record one
   alert-to-PR run. This is the only way past 21; everything else is at most
   +1.
2. **Observability +1 (small effort, needs a Docker-capable session).** Bring up
   `observability/`, open the US-13 Grafana dashboard on a journey run, commit
   a screenshot, and tick the pending-verification items #155/#199 (and the
   now-green `T-JOURNEY-BE` items). "Viewable in a UI" is the only missing
   clause.
3. **Add visible evidence for the owner-confirmed items (no new points).**
   Commit or attach evidence a grader can see without a separate confirmation:
   a screenshot of the `production` environment's required-reviewer setting (or
   the "Review deployments" panel of a gated run), a dated screenshot or short
   recording of each live URL, and a note that branch protection requires the
   CI checks before merge. Also fix README line 7, close #141/#143 with run
   links, and leave the nightly stop off until after grading.
