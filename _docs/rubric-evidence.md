# Rubric evidence

Status of each of the 12 criteria (24 points, 10 to pass) in `_docs/rubric.md`,
with links to evidence that exists now. Only the Rubric Evidence Auditor
(`.opencode/agents/rubric-auditor.md` and `.claude/agents/rubric-auditor.md`,
via the `update-rubric-evidence` skill) updates this file. Planned work does
not count, and the log's claims alone are not accepted without opening the
linked evidence.

- Audit date: 2026-10-26 (third audit; previous: 2026-10-25 at `234cccf`, 21 of
  24).
- Tree audited: `20a1fd8`, HEAD of branch `claude/funny-dijkstra-svm6xw` (read
  with `git log`). This is `main` at `8f7a3ee` (merge of PR #235) plus exactly
  the 17 files of PR #236 (`git diff --stat 8f7a3ee 20a1fd8`, identical to the
  file list GitHub gives for the PR).
- **PR #236 status.** The audit request described #236 as open. While this audit
  ran, the GitHub API showed it **merged** on 2026-10-26 14:15:37 UTC as `main`
  `b1f5d0c` (parents `8f7a3ee` and `20a1fd8`; the merge commit's changed-file
  list is the same 17 files). The `verify` run on `b1f5d0c`
  (https://github.com/andrew-chung-au/vuln-triage/actions/runs/40337986272, all
  seven jobs `success`) and the `deploy` run #50
  (https://github.com/andrew-chung-au/vuln-triage/actions/runs/40337986321,
  `success`) are green. I could not fetch `b1f5d0c` locally, so "the tree equals
  `20a1fd8`" is an inference from the identical file list and the clean
  merge, not a diff. Everything below was read at `20a1fd8`. Points that depend
  on #236 are labelled **[from PR #236, merged as b1f5d0c]**, and "If #236 were
  not merged" says what `main` at `8f7a3ee` would score.
- Auditor environment: Claude Code cloud session, no Docker, no AWS
  credentials, no access to `*.sslip.io`. Nothing was run live by me. CI and
  deploy evidence comes from the Actions run, job and log records read through
  the GitHub API; screenshots were opened and looked at; issue comments were read
  from `make issue-dump N=226` and the GitHub issue API.
- **Owner-confirmed** means: the fact rests on the project owner's live run or
  settings page, recorded in an issue comment or a committed screenshot, and I
  could not independently reproduce it. Issue comments 6417013401, 6417309808
  (#226) and 6415509715 (#220) are written by the orchestrator relaying what the
  owner ran and pasted; they are the only record of those runs. A committed
  screenshot is an artefact I can read, but its capture is still the owner's.
- `_docs/rubric.md` defines 12 criteria (24 points). The auditor role files'
  "14 criteria" wording is stale (tracked in issue #10).
- Status values: MET (top point level), PARTIAL (a lower non-zero level),
  MISSING (0 points).
- **Points currently evidenced: 22 of 24 (pass mark 10).** The only criterion
  below its maximum is On-Call Agent (0 of 2). Sum: criteria 1 to 8 at 2 each
  (16), CI/CD 3, Observability 2, Alerting 1, On-Call 0 = 22. If #236 were not
  merged the total would be 21 (see the Observability section).

## Score table

| # | criterion | max | score | status | change since 2026-10-25 (21/24) |
|---|---|---|---|---|---|
| 1 | Problem Description | 2 | 2 | MET | none |
| 2 | Product Specification | 2 | 2 | MET | none |
| 3 | Agent Team Specification | 2 | 2 | MET | none |
| 4 | Context Management | 2 | 2 | MET | none |
| 5 | Application | 2 | 2 | MET | none |
| 6 | Testing | 2 | 2 | MET | none |
| 7 | Containerization | 2 | 2 | MET | none |
| 8 | Deployment | 2 | 2 | MET [URLs owner-confirmed, now with committed screenshots] | none |
| 9 | CI/CD | 3 | 3 | MET [production gate: committed screenshots] | none |
| 10 | Observability | 2 | 2 | MET [from PR #236; one limit stated below] | **+1** |
| 11 | Alerting on User Impact | 1 | 1 | MET | none |
| 12 | On-Call Agent | 2 | 0 | MISSING | none |
| | **Total** | **24** | **22** | | **+1** |

Maxima sum to 24 (eight criteria at 2, CI/CD 3, Observability 2, Alerting 1,
On-Call 2). The pre-merge audit by another tool at `8f7a3ee` scored 21 with
Observability at 1 and On-Call at 0, which agrees with the 2026-10-25 table here.

## Evidence by criterion

| criterion | max points | full-marks condition | status | evidence | gap |
|---|---|---|---|---|---|
| 1. Problem Description | 2 | "The README clearly describes the problem, the system functionality, and expected behaviour." | MET (2) | `README.md` at `20a1fd8`: "The problem", "What it does" and "Expected behaviour" sections; the reviewer table "Where to find each rubric criterion" (lines 28-45) maps every criterion to evidence. The responder is described honestly as "planned, not built yet" (lines 45, 76, 92, 262). Line 7 no longer says production has not been promoted; line 239 says both dev deploy and a production promotion have run. Two dashboard screenshots `docs/images/dashboard.png` and `assets.png` are tracked. | None for the level. Small inconsistencies: README lines 45, 76, 211, 222, 262 say the responder is "not built" or "planned", but a stub responder service exists in `responder/` and Compose (criterion 12), so "no real runner yet" would be exact. Line 150 says the demo "may be stopped overnight"; the nightly stop is off. Line 43 (criterion 10 row) says metric, trace and log "share one trace ID in Grafana", which is stronger than the screenshots show (see criterion 10). |
| 2. Product Specification | 2 | "A specification exists and there's a publicly accessible task tracker. The tasks define acceptance criteria and there's evidence that the agents used the tracker." | MET (2) | Spec `_docs/specs.md` (US-1 to US-15, each with Acceptance lines). Public tracker https://github.com/andrew-chung-au/vuln-triage/issues (public repo; issue API answered in this audit, issues #199, #220, #226 read). Issues carry acceptance criteria (the #220 and #226 comments quote checkbox lists); role-labelled comments (`Orchestrator:`, QA verdicts quoted in PR #236 as 6417378357 and 6417556909); `_session-summaries/` files; PRs reference issues. | None for the level. #141 and #143 closure-with-run-links advice from the last audit was not re-checked this time. |
| 3. Agent Team Specification | 2 | "The project defines the agent team and process of how they work together." | MET (2) | `_docs/agent-team.md`; `_docs/agent-kit/process.md`; `_docs/agent-kit/team/pm.md`, `software-engineer.md`, `qa-engineer.md`; definitions in `.claude/agents/` and `.opencode/agents/`. | None. Stale "14 criteria" wording (issue #10) is cosmetic. |
| 4. Context Management | 2 | "AGENTS.md exists and it also points to modular docs (process, teams, etc.)." | MET (2) | `AGENTS.md` "Where to read more" links the README, brief, spec, rubric, roadmap, reviews, process, team files, agent-team, procedures, environments, usage log and human tasklist; `CLAUDE.md` imports `AGENTS.md`. | None. |
| 5. Application | 2 | "Full-stack application works end to end: frontend talks to backend, data persists in a database. Application runs locally with a single command." | MET (2) | Backend `backend/vulntriage/`, frontend `frontend/`, `Makefile` `dev` and `demo` targets. CI runs the backend end to end on Postgres in the `telemetry` job (run 40291587781, job 121467668560, `3 passed in 61.07s`, journey `T-JOURNEY-BE: registered asset '1'; driving the journey`) and again on `b1f5d0c` (run 40337986272, job 121624603761, `success`). The live UI is visible in committed screenshots: `docs/images/dashboard.png`, `assets.png` (local `make dev`) and `docs/images/g7-vuln-triage-dev-findings.png` (I opened it: the dev site at `dev.52-206-221-145.sslip.io/findings`, signed in as "Public reviewer (demo)", ranked P2/P3 findings with KEV/EPSS reasons). The owner's live demo run on 2026-10-26 (#226 comment 6417013401) registered four assets and showed each finding once **[owner-confirmed]**. | No recorded run I could re-check of a browser reaching the backend locally; the browser-to-backend link is evidenced by the screenshots of the deployed app (owner-captured), the typed HTTP client, the OpenAPI conformance job and the CI journey. |
| 6. Testing | 2 | "Both unit and integration tests exist, run with a single command, and pass." | MET (2) | `make test` runs vitest, backend pytest and responder pytest. CI `verify` workflow on `b1f5d0c` is green, all seven jobs (unit, sqlite-integration, postgres-integration, frontend, openapi-validation, telemetry, verify): https://github.com/andrew-chung-au/vuln-triage/actions/runs/40337986272. The same workflow was green on the audited head `20a1fd8` (PR run https://github.com/andrew-chung-au/vuln-triage/actions/runs/40334369080, `success`) and at `8f7a3ee` (run 40312441177, `success`). Counts "frontend 89, backend 532, responder 77" are stated in PR #236 and the usage log; I did **not** re-count them, and `make verify` was not run by me. | None for the level. Postgres integration is a separate command (`make test-integration`), but `make test` includes SQLite integration cases. |
| 7. Containerization | 2 | "The full system, including the database, runs via Docker or Docker Compose and starts with a single command." | MET (2) | `backend/Dockerfile`, `frontend/Dockerfile`, `compose.yaml` (db Postgres 16.4 with volume, migrations, backend, frontend, health checks), `Makefile` `compose-up` (`docker compose up --build -d --wait`). Recorded evidence: deploy logs show all four services healthy on the server (dev run #30 job 121218249980; production run #33 job 121229992961, from the earlier audit, not re-read). New: the owner ran the six-container observability stack with `docker compose ... up -d --wait` and all containers healthy, and ran `make test-compose JOB=responder` green on a Docker host (#220 comment 6415509715, 8 passed in 103 s per PR #236) **[owner-confirmed]**; CI runs the app plus observability stack under Compose in the `telemetry` job. | Honest limit unchanged: no recorded `make compose-up` session for the plain app (issue #137), and the server runs the deploy variant of the Compose project (`compose.deploy.yaml`, GHCR images). The CI Compose jobs and deploy logs show the stack starting with one command each. |
| 8. Deployment | 2 | "The application is deployed and reachable at a public URL, or there's a clear demo with the deployment." | MET (2) **[URL reachability owner-confirmed; now with committed screenshots]** | Terraform modules `terraform/bootstrap`, `deploy-roles`, `server`; deploy jobs reach the instance (earlier audit, run #33 job 121229992961). Public URLs in `README.md`: https://dev.52-206-221-145.sslip.io and https://app.52-206-221-145.sslip.io, plus a public reviewer login. **New: committed screenshots** `docs/images/g7-vuln-triage-dev-findings.png` (opened: dev site over `dev.52-206-221-145.sslip.io/findings`, signed in, ranked findings, dated 26/10/2026 in the taskbar) and `g6-vuln-triage-production-login.png` (listed in README "Deployment evidence"; not opened). Deploys still run automatically: `deploy` run #50 on `b1f5d0c` is `success`. | My sandbox cannot fetch `*.sslip.io`, so reachability stays owner-confirmed; the screenshot is owner-captured. Leave the nightly stop off until after grading (it would take the URL down). |
| 9. CI/CD | 3 | "CI runs tests, CD deploys to dev, and there's a manual deploy to production." | MET (3) | CI on every PR: `.github/workflows/verify.yml` (push and pull_request); PR run on the audited head https://github.com/andrew-chung-au/vuln-triage/actions/runs/40334369080 `success`. CD to dev on merge to `main`: `deploy.yml` push runs #49 (https://github.com/andrew-chung-au/vuln-triage/actions/runs/40312441052, `8f7a3ee`) and #50 (https://github.com/andrew-chung-au/vuln-triage/actions/runs/40337986321, `b1f5d0c`) both `success`; earlier #30 recorded the dev job steps. Manual production deploy: `deploy-prod` only on `workflow_dispatch` in `environment: production` (runs #31 to #33 in the earlier audit). **New visible evidence, opened this audit:** `docs/images/g1-github-settings-environments-production.png` shows Required reviewers on (andrew-chung-au), "Allow administrators to bypass" unticked, deployment branches limited to `main`; `g2-github-actions-deploy33-review.png` shows deploy #33 stopped at "Review pending deployments / production / Review needed from andrew-chung-au" with `deploy-prod` "waiting for review"; `g5-github-settings-rulesets-protect-main.png` shows the `protect-main` ruleset Active, bypass list empty, requiring a pull request and status checks, blocking force pushes and deletions. | (a) "Prevent self-review" is unticked and the only reviewer is the owner who triggers the run, so the gate is a deliberate pause, not a second person. It satisfies "manual deploy" in the rubric. (b) The ruleset screenshot shows "Require status checks to pass" ticked but the list of required checks is in a collapsed section, so which checks gate the merge is not visible; the tests-before-deploy link rests on that ruleset plus `deploy.yml` having no `needs` on `verify.yml`. (c) Cosmetic: run #32 shows `cancelled` overall (attempt 2); point graders to attempt 1. |
| 10. Observability | 2 | "A key user journey is instrumented with metrics, traces, and structured logs that share a trace ID; no customer data or credentials are sent to telemetry; and the signals are collected, stored, and viewable in a UI." | **MET (2) [from PR #236, merged as `b1f5d0c`; one limit stated]** | See the detailed judgement in the next section. In short: instrumentation, collection and storage are shown by CI (`backend/vulntriage/observability/`, `observability/` stack; `telemetry` job, `T-REFUSE`, `T-JOURNEY-BE`). The three signals are now **seen in Grafana** in three committed screenshots (opened and described below), and the log and the trace carry the same trace id `42f5161ee955e543e2f5f355e410c247` on screen. The metric-to-trace link is asserted in CI as a Prometheus exemplar (`tests/test_compose_telemetry.py` lines 214-216, `wait_for_exemplar_trace_id`; green in the `telemetry` job of run 40291587781, job 121467668560: `3 passed in 61.07s`, journey trace id `c147954fd0218af18a27b8b5270731ba`; the same assertion is in the `telemetry` job of run 40337986272 on `b1f5d0c`, `success`). | **What is not shown:** no screenshot shows the metric's exemplar or the metric panel linking to a trace; the metric panel shows `vt_notifications_total` counts with no trace id, and the journey trace id in CI (`c147...`) is a different run from the one in the screenshots (`42f5...`). The exemplar link therefore rests on the CI assertion plus the owner-observed log-trace join, not on a UI view of the exemplar. The trace-to-logs link from the Tempo view was not tried (#226 comment 6417013401). The observability stack runs in local Compose only, not on the AWS server (README says so). A strict grader could treat the metric leg as asserted rather than demonstrated; I count it MET because the rubric asks for a shared trace id (CI-asserted) and signals viewable in a UI (shown). |
| 11. Alerting on User Impact | 1 | "At least one alert exists." | MET (1) | Provisioned Grafana rule `observability/grafana/provisioning/alerting/us14-overdue.yaml` (undelivered top-priority finding, `vt_top_tier_notification_overdue`). It fired in real Grafana in CI (alert run 40160976080 at `79f9f47`, job 121072278559); on 2026-10-26 the owner saw `us14-notification-overdue` in Grafana Alerting, Provisioned, Normal, health ok **[owner-confirmed, #226 comment 6417013401]**; contact points and policy were not checked. | Optional alert-firing screenshot (G10) not taken. Does not affect the point. |
| 12. On-Call Agent | 2 | "An agent wakes up on an alert and fixes the issue." | MISSING (0) | What exists, re-checked at `20a1fd8`: a responder service `responder/vt_responder/` (`app.py`, `guard.py`, `runner.py`, `api_client.py`, `actlog.py`, `fakes.py`, `config.py`) with tests; `compose.responder.yaml`; `ci/test-compose.sh` `JOB=responder` (stub mode only, `RESPONDER_MODE="stub"`); the repeat-alert guard; the owner's green `make test-compose JOB=responder` on a Docker host (#220 comment 6415509715; 8 passed in 103 s, owner-confirmed) showing the real Grafana 11.3.0 webhook body reaches the responder and starts a run. `responder/vt_responder/runner.py` is `StubRunner`: its docstring says "no model, no SDK", "the real runner (Claude Agent SDK) is task 28d (#221)", and the "pull request" is recorded against a fake GitHub client ("Nothing is pushed"). No real runner, no real branch or PR, no recorded alert-to-fix run, and the responder job is not in `verify.yml` (#161). F4 (pin the responder model) is still open in `_docs/human-tasklist.md`. | A real runner (#221, needs F4), a real alert-to-PR run that reproduces the defect and opens a fix PR with a test, the action log of that run, and the `verify.yml` job (#161). This is the only criterion below maximum. The stub and the wiring are real progress but, by the rubric's own wording, "wakes on an alert and fixes the issue" has not happened, so 0. |

## Observability: what the three screenshots show

All three were opened with an image reader at `20a1fd8`. Files are under
`docs/images/`; README "Observability evidence" (lines 201-209) links them.

1. `g9-grafana-dashboard-dev-local.png`. Grafana, dashboard "VulnTriage / US-13
   journey", **view mode** (Share and Edit buttons visible, not edit mode), time
   range Last 1 hour UTC. Three populated panes: (a) "Notifications (metric)
   vt_notifications_total, running total": two lines, `top tier/held` (green, 2)
   and `top tier/sent` (yellow, 1), times 12:15 to 12:30; (b) "Journey traces
   (Tempo) scan.run": four trace ids with start times 2026-10-26 12:22:14 to
   12:22:15, one of them `42f5161ee955e543e2f...`; (c) "Journey logs (Loki)
   backend events": `notification.deliver` and three `scan.finished` events.
   It still shows the **Environment `dev` and Version `local` dropdowns**.
2. `g9-grafana-trace-scan-loki-expandedlog.png`. Dashboard "View panel" of the
   Loki pane with the `notification.deliver` event expanded: fields include
   `trace_id 42f5161ee955e543e2f5f355e410c247`, `span_id 48820fffcc00b756`,
   `service_name vulntriage-backend`, `severity_text INFO`, `vt_finding_id 2`,
   `vt_notification_kind top tier`, `vt_outcome sent`, `vt_tier P1`,
   `deployment_environment dev`, `service_version local`. No email address,
   repository name, advisory text or credential is in the visible field list.
3. `g9-grafana-tempo-trace.png`. Grafana Explore on Tempo, TraceQL box containing
   `42f5161ee955e543e2f5f355e410c247`, result "vulntriage-backend: scan.run",
   29.34 s, 7 spans, list visible down to `notification.enqueue` (the other
   spans visible: `repository.read`, `osv.query`, `signals.enrich`,
   `prioritise`). The seventh span (`notification.deliver`) is cut off in the
   image; the owner's #226 comment (6417013401) says all seven were there.

Shown on screen: a metric, traces and structured logs each visible in a Grafana
UI; the same trace id in a log event and in a trace (and in the trace list on
the dashboard). Not shown on screen: the metric carrying that trace id (an
exemplar), a click-through from the metric or from the trace to the log, and
the dashboard after the filters were removed.

Earlier audit's gap (committed screenshot in edit mode with an empty metric
panel, a `GET /findings` trace, nothing linked) is closed: the old placeholders
`g9-grafana-dashboard.png` and `g9-grafana-trace.png` are deleted in the audited
tree, the three new images show a populated metric panel in view mode and a
`scan.run` trace, and all three are linked in the README. I did not open the
old images, so I cannot confirm what they showed; the description rests on the
pre-merge audit and the PR text.

**The dashboard filters.** The Environment and Version variables were removed
from `observability/grafana/dashboards/us13-journey.json` (`templating.list` is
now `[]`) after the screenshots were taken. They were not referenced by any
panel query (verified from the query text the owner's comment quotes and from
the PR description), so removing them does not change what any panel shows. The
criterion does not require filtering. What it does mean: the dashboard JSON in
the repo has not been loaded in Grafana since the change; only the static test
`tests/test_us13_dashboard.py` (green in CI) checks it. The risk is a provisioning
error that blanks the dashboard, which would make screenshot 1 no longer
reproducible. The first screenshot is honest about this (README caption says the
dropdowns "were removed afterwards"). Not affecting the score; one live load
would close it.

**Customer data.** `T-REFUSE` (CI, `telemetry` job) asserts the excluded keys are
absent from the Collector output, Tempo and Loki; the log fields in screenshot 2
agree. The demo data in the screenshots are recorded fixtures (`VT_FEEDS=fixtures`),
so this shows the field set, not real customers.

**If #236 were not merged.** `main` at `8f7a3ee` has no screenshots in the
README, the two superseded placeholders, and the dashboard filters. By the
2026-10-25 standard Observability would be PARTIAL (1) and the total **21 of 24**.
Since #236 merged as `b1f5d0c`, that case no longer applies to `main`.

## Items confirmed by the owner (not independently reproduced)

1. **The live URLs load** (criterion 8): committed screenshots g6, g7 plus the
   owner's confirmation; my sandbox cannot fetch the pages.
2. **The live observability run of 2026-10-26** (criterion 10, supporting 7 and
   11): six containers healthy, the journey, the dashboard, the trace and the
   trace id in the expanded log, MailHog mail, the alert rule visible. Source:
   #226 comments 6417013401 and 6417309808, written by the orchestrator from what
   the owner pasted ("I saw the page text and terminal output, not the
   screenshots"). The screenshots themselves are committed and I read them.
3. **`make test-compose JOB=responder` green** on a Docker host (criterion 12,
   supporting only): #220 comment 6415509715. Not reproduced in CI; the responder
   job is not in `verify.yml`.
4. **Branch protection requires the CI checks**: ruleset screenshot shows
   "Require status checks to pass" ticked; which checks is not visible.

## Corrections to earlier claims

- 2026-10-25 table: Observability PARTIAL (1) is superseded by MET (2); the gap
  text "no screenshot committed (README line 184 says Not captured yet)" and
  "the metric is matched by name and outcome, not by trace id (no exemplar)" are
  both out of date. The exemplar assertion now exists (`tests/compose_telemetry.py`
  `prometheus_exemplar_trace_ids`, `observability/compose.yaml` and
  `otel-collector.yaml` changes) and is green in CI. The README line number I
  cited then (184) is now the "Deployment evidence" table; the "Not captured
  yet" sentence is at line 211 and now only concerns the drill and responder PR.
- 2026-10-25 "Items confirmed by the owner" item 2 (production reviewer rule) is
  now backed by committed screenshots g1 and g2 that I opened; item 3 (tests gate
  the dev deploy) is better supported by the ruleset screenshot g5 but the exact
  required checks are still not visible.
- 2026-10-25 criterion 12 said `ci/test-compose.sh` shows `JOB=responder` as "not
  implemented", with no responder agent definition or webhook receiver. That is
  out of date: the service, Compose wiring and `JOB=responder` exist (stub only).
  The score (0) is unchanged.
- 2026-10-25 criterion 1 claimed README line 7 was stale about production
  promotion; at `20a1fd8` it no longer is.

## Top three gaps (priority order, by points gained per effort)

1. **On-Call Agent +2 (the only criterion below maximum).** Build the real runner
   (#221; needs the owner to pin the model, F4), run the alert-to-PR loop once for
   real with the action log, add the `verify.yml` responder job (#161), and
   record the drill (task 39). The stub and its Compose wiring are done and
   owner-run green; the fix itself is not.
2. **Observability: close the two soft spots (no new points, protects the 2).**
   Load the dashboard once after the filter removal and re-capture it; capture
   one view that shows the metric exemplar or a metric-to-trace click-through (or
   say plainly in the README that the metric leg is asserted in CI, not shown in
   a screenshot, and soften the criterion-10 row at README line 43). Try the
   trace-to-logs link.
3. **Documentation consistency (no new points).** Update the stale score and
   audit-date references and the README responder wording (list given in the
   audit report), show which status checks `protect-main` requires, and keep the
   nightly stop off until after grading.
