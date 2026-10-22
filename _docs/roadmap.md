# VulnTriage roadmap

The order in which open work is done, and the checks used to tell whether the
project is on track. It sequences the work; it is not part of the build plan
that the plan review checks (`_docs/planning-process.md` Stages 1-6).

- Adopted: 2026-10-19, from a review of opencode's status analysis (Claude Code, claude-opus-5-5); see `_docs/ai-usage-log.md`.
- Goal: 24/24, built as Tier A → B → C milestones (human decision of 2026-10-17; tiers in `_docs/reviews/2026-10-16-final-rubric-impact.md` §5), in the smallest shape that meets the criteria in `_docs/rubric.md` and the course's project requirements (a rollback path, an alert trigger, an on-call responder; peer review of three other projects is required to pass). This file is the submission track, phases S0-S5 (human decision H1, 2026-10-22). Anything that scores nothing goes to the showcase track, [`roadmap-showcase.md`](roadmap-showcase.md), which stays a separate file and starts only after the submission is in.
- Timing and scope trade-offs are the human's. "On track" here means steps are done in order and the audited score meets the checkpoint for the steps done.
- Source of truth for status: the GitHub tracker and `_docs/rubric-evidence.md`. The status column here is a snapshot taken at each check-in, not live state.

## Priority rule

VulnTriage is the product; the agent kit and dev container are tooling. From 2026-10-20 (human direction), the next product step always comes first. Kit, hook and dev-container issues go under "Later, not scheduled" unless one blocks the next product step, and then it joins that step's row. The tooling the build needs, Docker and Postgres in the dev environment, is on the parallel tooling track (T2, T3) below, and phase S2 depends on it.

## Sequence

Status values: `todo`, `doing`, `done`, `blocked`, `deferred`. A step starts only when the steps it depends on are `done`; a `deferred` step does not block anything.

| # | Step | Issues | Depends on | Done when | Status (2026-10-22) |
|---|---|---|---|---|---|
| 1 | Refresh the rubric evidence | (auditor skill) | none | `_docs/rubric-evidence.md` re-audited at current `main`; confirms or rejects Testing 1 and CI/CD 1 | done (2026-10-20 audit, 10/24 at `74e9cfc`) |
| 2 | README problem description | #13 | none | Auditor marks Problem Description MET (2) | done (auditor confirmed MET 2) |
| 3 | Push check plan-mode fix | #35 | none | #35 closed | done (`df72298`, QA PASS after the approval record; closed 2026-10-20; follow-up #42) |
| 4 | Remaining #15/#20 findings | #33 | none | #33 closed | deferred (2026-10-20, priority rule: tooling hardening; moved to "Later") |
| 5 | Approval-record hardening | #17, #18 | none | Both closed before the step 6 protected commits, or the human defers them | done (both closed 2026-10-20) |
| 6 | Spec review issues | #3, #4, #5, #6, #7, #8 | none | PM grooms all six together; one batched decision message to the human; each implemented as its own protected commit; all six closed | done (six protected commits `45f6fa6`..`fdc7b51`, all QA PASS, closed 2026-10-20; follow-up #41) |
| 7 | Stage 2: `_docs/architecture.md` (next) | #41, then #43 | 6 | #41's spec commit landed; Stage 2 checklist PASS; #9's architecture rows ticked; Docker-capable environment named; #9 hosting decision closed as AWS (the infrastructure tool is Terraform since H2, 2026-10-22) | done (#41 `1445ca5`; #43: spec `faea412` and `3ecd54b`, `architecture.md` `072c17e`..`4180fe3`, QA PASS, closed 2026-10-20) |
| 8 | Stage 3: API contract | #23, then #27 | 7 | Both closed | done (#23 and #27 closed 2026-10-21; US-15's responder contract split out as #50) |
| 8b | Stage 3 completion: responder read-only contract | #50 | 8 | #50 closed; the human approved the contract diff; `make openapi-validate` exits 0 | done (contract `6ff10d9`, QA PASS at `9a03ba9`; closed 2026-10-22; spec notes 1-3 in `cd870df`, `54bdce3`, `147bd7a`; follow-up #58 settled 2026-10-22) |
| 9 | Frontend SPA shell | #34 | 8 (#23), #45 | #34 closed (its criteria say "existing tests still pass plus the new regression test", no fixed count) | done (QA PASS at `d8c2ffe`; closed 2026-10-21) |
| 10 | Stage 4: `_docs/testing.md` | #56 | 8, 8b | Stage 4 checklist PASS; #9's testing rows ticked | done (#56: `_docs/testing.md` `8d9db69`..`2430912`; QA PASS 6329945929, re-check 6330289999; closed 2026-10-22; spec notes to #63) |
| 11 | Stage 5: `_docs/tasks.md` | #72 | 10 | Stage 5 checklist PASS (no cycles; every story and criterion covered) | done (#72: `_docs/tasks.md` `05e3e60`; QA PASS 6332195958, re-check PASS at `ae6b708` 6332346303; closed 2026-10-22) |
| 12 | Backlog issues from `tasks.md` | #74-#88, #26 | 11 | PM proposal approved by the human; each issue carries its story's acceptance criteria | doing (2026-10-22: proposal approved; Milestone A filed as #74, #75, #26 rewritten, #76-#88; #24/#25 closed as superseded; B/C/Committed file at their boundaries). Milestone B, C and Committed issues are filed at their boundaries and no longer gate step 14 |
| 13 | Stage 6: `_docs/plan-summary.md` | #91 | 11 | Stage 6 checklist PASS (all 12 criteria mapped) | done (#91: `_docs/plan-summary.md` and the README link; QA PASS at `882c75d`; closed 2026-10-22; follow-up #95) |
| 14 | Plan review and phase change | new issue | 11, 13 (Milestone A filed) | Review passed with H2-H7 applied to `architecture.md` and `tasks.md`; human-approved `AGENTS.md` phase line committed | todo (the H2-H7 document changes #97-#103 are closed; this roadmap merge, #93, is the last one before the review) |
| S1 | Tier A build: the app | #74 → #26 → #76 → … (step 12 Milestone A issues), then #81-#88; `tasks.md` tasks 1-14 | 14 | Frontend, backend and database work end to end; `make dev` (task 11) starts them together on SQLite with no Docker; unit and integration tests run with one command; auditor: Application 2, Testing 2. Score after (estimate): 12 | blocked (phase line) |
| S2 | Containers and CI: milestones B1-B3 | step 12 Milestone B issues, filed at the boundary; tasks 15, 16, 19, 20 | S1; T3 (#31, the Compose Postgres recipe) | A `make` target starts the full stack with Postgres in Compose; CI runs the tests on every pull request. Score after (estimate): 14 | todo |
| S3 | Deploy: milestones B4-B6, on one server | step 12 Milestone B issues; tasks 17, 18, 21, 22 | S2; the human's AWS prerequisites below | Terraform builds the server; a push to `main` deploys to dev when the tests pass; a manual workflow in the GitHub `production` environment deploys the same image tag to prod; one rollback rehearsed and recorded; deployment steps and teardown in the README. Score after (estimate): 19 | todo |
| S4 | Observe and respond, in local Compose: milestones C2, C3, C5, C6, C7 and C9, with the backend notification | step 12 Milestone C issues; tasks 23, 24 (Compose half), 25-29, 37, 38 | S2 (S3 is not needed; see "Ordering if AWS is slow") | Signals for the key journey share a trace ID and are viewable in local Grafana; the US-14 alert fires from the demo-defect switch; the responder opens a fix pull request; the run is recorded; the defect switch is removed before any prod deploy. Score after (estimate): 24 | todo |
| S5 | Submit: milestone C8 | task 2 (evidence note), #19 | S3, S4 | README has the public URL, the one-command start, the recordings and the rollback steps; full rubric re-audit shows all 12 criteria MET; time reserved for the three peer reviews | todo |

S0 (plan settled) is steps 13-14. Each phase banks points, so the human can submit at the end of any finished phase; S1 alone passes (12 estimated points of the 10 needed). When to submit is the human's call, not an agent's: agents work the phases in order and do not change scope because of a date. The milestones B1-B6 and C1-C9 are in "Tier B and Tier C milestones" below.

**#44 (cloud sessions, human direction 2026-10-21):** done (2026-10-21), after #23 and before #27. It is tooling, so the priority rule would have left it under "Later"; the human scheduled it here because it unblocks #31 and the Docker-dependent build steps. #44's own criteria had the orchestrator close it with the new `make issue-close N=44` target.

**Parallel tooling track (human direction, 2026-10-22).** Tooling that runs beside the product steps and blocks none of them. It is not a numbered step, so a delay here does not hold up steps 11-14. Groomed with the human's answers D1-D5 (PM comments 6331077862, 6331105969, 6331091593, 6331105799; answers 6331160446):

| Item | Issue | Must be done before | Runs beside | Notes |
|---|---|---|---|---|
| T1 | #53: type check in `make verify`; warn when `BASE` equals `HEAD`, fail when `BASE` does not resolve | S1 and #24 (both edit `agent-kit.conf`) | steps 11-14, T2, T3 | Protected: `verify.sh`, `verify.md` (one commit), `agent-kit.conf`, `AGENTS.md` line 35; `_docs/testing.md` is not protected |
| T2 | #48: `make docker-start`/`docker-stop` for cloud sessions, gated on `CLAUDE_CODE_REMOTE=true`, no `sudo` | S2, and before T3 | steps 11-14, T1 | The whole issue runs in one cloud session the human starts; share the `AGENTS.md` Environment line and the end of the `Makefile` with T3, so T2 then T3, never at once |
| T3 | #31: Compose Postgres recipe and `make db-check` | S2 | steps 11-14, T1 | Before #26; "run #26's persistence test against Postgres" is #68 |

Rebuilding the dev container (T3) is a human step: not mid-issue. Every item appends to `_docs/ai-usage-log.md`; keep both entries on conflict.

Later, not scheduled (tooling and process; see the priority rule): #10, #16, #19, #29, #30, #33, #36, #38, #39, #40, #42, #46, #47, #65, #66, #67 (CI passes a real `BASE`, after #53), #68 (after #26 and #31). #38 carries out the human's 2026-10-20 remove decision for #36; #36 can close when #38 does. #19 (ai-usage-report) is graded evidence; pick it up with the Tier C work.

#48 (cloud `docker-start`/`docker-stop` targets, filed 2026-10-21 from the cloud trial): the human answered D1 (a cloud session is an acceptable, optional Docker route) and D2 (the former step 16's row, now S2's dependency on T3) on 2026-10-22; it is item T2 on the parallel tooling track above.

#50 (the US-15 responder's read-only API contract, split out of #27 by the human on 2026-10-21) was step 8b, groomed with the human's D1-D3 answers; done and closed 2026-10-22.

#60, #37 and #61 (permission settings and the permission sweep) are not in the step sequence. They are tooling, so the priority rule would have left them under "Later"; the human scheduled them outside the roadmap on 2026-10-22, on their own branch, while #56 (step 10) ran in another session. They did not block any step. Done and closed 2026-10-22 (settings `a5b21c0`; `make permission-report` `2520c9c`; sweep procedure and rules `4c42cf3`; QA PASS on all three). The live prompt check passed in a local default-mode session (#60 comment 6330923566). Follow-ups #65 (first permission sweep) and #66 (`make issue-close` ask rule and option order) are under "Later".

#45 (the D4 `types.ts`/mock/UI alignment, filed from #23) is not in the step sequence: it started after #23 and before step 9 (#34), and #34/#25 waited for it. Done 2026-10-21 (QA PASS at `3f55509`; closed). It added `make frontend-typecheck`; #53 (T1, parallel tooling track) puts it into `make verify`.

#41 and #43 completed step 7. Leftovers from #43 (human's choice: recorded here and on #23, no new issue):
- **Step 8 (#23):** comment 6301758496 covers which brief the API returns, a "no brief yet" state, status codes, wire values and the types.ts differences table.
- **Step 10 (Stage 4 testing, #56, done 2026-10-22):** the US-14 gauge's `tier` label test (`A-TIER`), the no-resolve/re-fire metric-gap case (`A-GAP`, `VERIFY:`), and the "resolved" message decision (D1 option 1, `A-RESOLVE`) are in `_docs/testing.md`. The data-model gap is #63.
- **Next spec change:** E10's wording on uv workspace entries; US-2 on the project's own `uv.lock` package. Also `VERIFY:` tags on the OpenTelemetry attribute names in `architecture.md`.

## Tier B and Tier C milestones (phases S2-S4)

The old step 17 was one row for 8 criteria and 12 of the 24 points. It is split
into the milestones below, in build order, with a dependency, a "done when" and
a score checkpoint for each. The plan is from the Tier B/C draft merged into
this file on 2026-10-22 (commit `1edc468`), reshaped by the human's decisions
H1-H7 of 2026-10-22 (see "Open decisions"): Terraform, one server for dev and
prod, GHCR, `sslip.io` hostnames, observability, the alert and the responder in
local Compose, and the n8n and other committed-scope features in the showcase
track.

Sources: `_docs/rubric.md`; the course's Module 3 (containerize and deploy) and
Module 4 (DevOps and observability) notes and homework the human shared on
2026-10-22; `_docs/architecture.md` (Components, Observability, Responder
agent, Deployment); `_docs/testing.md` (US-13, US-14, US-15, CI jobs);
`_docs/tasks.md` (Stage 5). Where this section and those documents differ, they
win and the difference is a defect here, except for the proposals under "Open
decisions". Task numbers are from `_docs/tasks.md`. Task boundaries follow
`tasks.md`; a milestone boundary that falls inside a task (15, 17 or 24) is a
checkpoint grouping only, and the issue filed from it keeps the task whole.
Task 21 is already split from the production promotion in `tasks.md` (decision
D7): the dev auto-deploy is task 21, the manual promotion is part of task 18.
Where `tasks.md` and this file differ, this file follows `tasks.md` on task
boundaries and the submission-track decisions (H1-H7) on order and checkpoints.

**What the course pattern settles.** The Module 4 notes describe CloudFormation
on AWS, one EC2-based stack per environment (dev, then a prod copy), images built
once and pushed to Amazon ECR, GitHub Actions deploying to dev on every push to
`main` and promoting to prod by a manual workflow, and a separate observability
Compose project. The plan follows the pattern as adapted by H2-H4: Terraform
instead of CloudFormation, one server running both environments as two Compose
projects, and GHCR instead of ECR. Architecture Open question 6 is closed with
this (decision D1 below).

| Course practice | Plan today | Gap or proposal |
|---|---|---|
| Image tag `YYYYMMDD-HHMMSS-shortsha`, sortable and traceable | The course tag; record each digest (architecture Deployment, pipeline step 2) | D2, resolved: the tag works with GHCR; the digest is still recorded |
| Telemetry carries service name, environment and deployed version | Allowlist has `service.name`, `deployment.environment`; no version yet (A32) | D2, kept: add `service.version` (= the image tag) to the allowlist so an incident maps to a release; made in `architecture.md` A32 by #107 |
| `observability/` as its own Compose project, deployed apart from the app | Local Compose project for submission (H6); an AWS server for it is showcase item X3 | Use `observability/` as the repository folder |
| Alert payload names service, environment, version, owner and dashboard URL | Labels: `finding_id`, `tier` only (no excluded data) | Add the dashboard link and environment/version as annotations, not labels, so the one-alert-per-finding grouping stays |
| Responder: on a false positive, explain and change nothing; smallest fix; tests must pass | Responder opens a PR with a failing test and a fix | D4: add the false-positive rule (spec change, protected) |
| A deliberate bug that existing tests miss, to prove the loop | `VT_DEMO_DEFECT=notify_no_fix`, refused in production | Consistent; the flag is the safer form |
| Rollback listed as "beyond the module" | Run the production deploy again with the previous image tag (architecture Deployment) | The rubric task list says "a rollback path", so B6 rehearses it once |
| kind/Kubernetes and `act` (Module 3 homework) | Not in the plan | Not needed for any criterion; kept only as the fallback in D5 |

**Prerequisites (human, can start now).** None of these waits for step 11; most
are the human's. The human-side AWS and GitHub steps for B4-B6 are in
[`aws-setup.md`](aws-setup.md).

| Item | Needed by | Owner | Notes |
|---|---|---|---|
| T2 (#48) then T3 (#31): Docker in cloud sessions and the Compose Postgres recipe | B2 | agents, human for the dev-container rebuild | Parallel tooling track above |
| AWS account with an AWS Budgets alert (A37 amount); steps in [`_docs/aws-setup.md`](aws-setup.md) | B4 | human | Set before any server exists. Open: the human has done no AWS step |
| Domain name and TLS approach (architecture Open question 7) | B5 | none | Closed by H5: `sslip.io` hostnames from the server's Elastic IP, HTTPS from Let's Encrypt (VERIFY: rate limits) |
| GitHub `production` environment with the human as required reviewer | B6 | human | VERIFY: available on this repository's plan |
| `main` branch protection that refuses the responder's push (D2 of #43) | C6 | human | Already required by the architecture |
| The responder's agent runtime (the brief's LLM provider, Open question 9, is showcase item X4) | C6 | human | The responder runtime is a dependency: ask before adding |

### Tier B: deployment path (target 19 of 24)

Starts when S1 (the Tier A build) is `done`; B1-B3 need only Docker, not AWS.

| # | Milestone | Tasks | Depends on | Done when | Criteria | Size |
|---|---|---|---|---|---|---|
| B1 | Images: multi-stage Dockerfiles for backend and frontend, non-root, health checks, backend listens on `0.0.0.0` | 15 | S1 | Both images build in CI; each container answers its health check | Containerization | S |
| B2 | Compose stack: `compose.yaml` with frontend, backend and `postgres` (named volume, health checks, `depends_on` healthy), `.env.example`, one start target; #68 runs #26's persistence test against Postgres | 15, 16; #68 | B1, T3 | `docker compose up --build -d --wait` (through a `make` target) starts everything; data survives a restart; auditor marks Containerization 2 | Containerization, Application | M |
| B3 | CI on every pull request: the `testing.md` job table up to `postgres-integration` and `security-scan`, plus image builds; #67 passes a real `BASE` | 19, 20 | B2 | Every job runs on a PR and fails the PR when red; auditor re-confirms CI/CD 1 with Testing 2 | CI/CD, Testing | M |
| B4 | AWS foundation: the Terraform modules (state bucket, GitHub OIDC deploy roles, one server with its Elastic IP); on push to `main`, build once, tag (D2), push to GHCR with the workflow's `GITHUB_TOKEN`, record the digest. The deploy role needs only to run the deploy on the server (VERIFY: SSM Run Command or an equivalent); the state bucket needs S3-native locking (VERIFY) | 17 | B3, AWS account | An image tagged from a `main` commit is in GHCR; the human has applied the Terraform modules; the deploy role is assumed through OIDC with no long-lived AWS key | CI/CD | M |
| B5 | Dev environment: the `dev` Compose project on the one server behind the reverse proxy at `dev.<elastic-ip>.sslip.io`; push to `main` deploys the new tag to dev only when tests pass | 17, 21, 22 | B4 | The app is reachable at the dev URL; a pushed change appears there with no manual step; a red test leaves the old version running; auditor marks Deployment 2 and CI/CD 2 | Deployment, CI/CD | L |
| B6 | Production and rollback: the `prod` Compose project and hostname `app.<elastic-ip>.sslip.io` on the same server; manual workflow in the `production` environment deploys the tag running in dev, never rebuilding; rollback by running the production deploy again with the previous tag, rehearsed once; a README section (or `docs/DEPLOYMENT.md`) with the steps and teardown | 18 | B5 | Prod runs the same digest as dev; one recorded rollback; auditor marks CI/CD 3 | CI/CD, Deployment | M |

Cost controls go in with B4-B6, not after: the budget alert and the nightly stop
of the server (architecture Deployment, Cost controls; A37).

### Tier C: observability, alert, on-call (target 24 of 24)

For submission every Tier C milestone runs on the local Compose stack (H6), so
none waits for B4-B6. C1 and C4 are showcase items, not submission milestones.

| # | Milestone | Tasks | Depends on | Done when | Criteria | Size |
|---|---|---|---|---|---|---|
| C1 | Showcase (X6): n8n routing, reminders, digest and workflow export (tasks 33-36). For submission the backend sends the top-tier notification itself (task 37, in C3) | 33-36 (Showcase) | submission done | Not a submission milestone; built after S5 | none for submission | M |
| C2 | Backend instrumentation: OpenTelemetry SDK and FastAPI auto-instrumentation; the US-13 spans, `vt_notifications_total`, `vt_notification_delivery_seconds`, `vt_top_tier_notification_overdue`; JSON logs with `trace_id`; the allowlist helper; `service.name`, `deployment.environment`, `service.version`; export is a no-op without a Collector, real span contexts always (A40) | 23 | S1 (the `notification.deliver` span comes from task 37, in C3) | With a console exporter, one scan shows a span, a metric and a log line with the same trace ID and no excluded data | Observability | M |
| C3 | Observability stack in `observability/` (local Compose) and the backend's top-tier notification: Collector with the allowlist processor, Prometheus, Loki, Tempo, Grafana with provisioned data sources and the "US-13 journey" dashboard, filterable by environment and version; MailHog; the backend delivery worker (task 37, built after task 24 and before task 25) | 24 (Compose half), 37, 25 | C2 | `T-JOURNEY` and `T-REFUSE` pass in Compose; the three signals show side by side in local Grafana; a top-tier finding's owner email reaches MailHog from the backend; auditor marks Observability 2 | Observability, Application | L |
| C4 | Showcase (X3): deploy observability and the responder in AWS, Grafana behind a login; dev and prod export to it. Not a submission milestone | none (the AWS half of task 24 is no longer in the task) | C3, B5, B6, submission done | Not a submission milestone; built after S5 | none for submission | M |
| C5 | US-14 alert as code: the provisioned rule, notification policy and contact points (email and responder webhook); annotations with dashboard link, environment, version | 26, 27 | C3 | `A-FIRE`, `A-HELD`, `A-TIER`, `A-GAP`, `A-RESOLVE` pass; auditor marks Alerting 1 | Alerting on User Impact | S |
| C6 | Responder in local Compose: webhook receiver (bearer secret, repeat-fingerprint guard) that starts one headless agent run per alert in a fresh checkout; `RESPONDER_MODE=stub` in CI; read-only API and Loki tokens; branch `responder/<fingerprint>` and a pull request; every action logged; false-positive rule if D4 is approved | 28 | C5, #50's contract (closed) | `I-RESP-*` and the stubbed `P-DEMO` pass in CI; a test alert with no incident ends with "no change" and an explanation | On-Call Agent | M |
| C7 | End-to-end drill, run locally: `VT_DEMO_DEFECT=notify_no_fix` → job fails → metric 1 → one alert → responder PR → human merges → local check → delivered to MailHog → alert resolves; recorded (screenshots or a short video) as review evidence; then the cleanup commit removes the flag and `P-FLAG-GONE` passes before any prod promotion | 28 (live drill), 29 | C6 | The drill is recorded and linked from the README; the flag is gone; auditor marks On-Call Agent 2 | On-Call Agent, Alerting, Observability | M |
| C8 | Close-out: README sections for deployment, observability and the responder; #19 (AI usage report); full rubric re-audit; teardown plan ready for after grading (the human runs it); time reserved for the three peer reviews | 2 (evidence note), #19 | C7, B6 | `_docs/rubric-evidence.md` shows all 12 criteria MET | all | S |
| C9 | Backend scheduler: the daily KEV and EPSS refresh and the scheduled re-scan run inside the backend (replaces the n8n schedule for submission) | 38 | S1 (needs tasks 8 and 10 only; build any time after task 10) | A fake-clock test shows changed signals and ranks after the scheduled run, a re-scan of every asset and no second notification job on a repeated run | Application | S |

**Mapping to `tasks.md`.** Task numbers are from `_docs/tasks.md` (step 11, QA
PASS). Step 12 files the Milestone B, C and Committed-scope issues at each
milestone boundary; this table is input to that filing, not a second backlog.

| Milestone | `tasks.md` tasks | Difference |
|---|---|---|
| B1 | 15 (Dockerfiles) | none |
| B2 | 15, 16; #68 | none |
| B3 | 19, 20 | none |
| B4 | 17 (Terraform modules: state bucket, deploy roles, server; build once and push to GHCR) | Image tag format (D2); the milestone covers the first half of task 17 |
| B5 | 17 (the `dev` project and hostname), 21, then 22 (pilot seed data) | Task 21 depends on 17 and 19 only; the production promotion is part of task 18 (D7), so dev auto-deploy does not wait for prod |
| B6 | 18 | Task 18 is the second Compose project and hostname on the same server plus the manual production workflow and the rollback; D7 |
| C1 | 33-36 (Showcase) | Not a submission milestone (X6); the backend sends the top-tier notification (task 37) |
| C2 | 23 | `service.version` in the allowlist (D2) |
| C3 | 24 (Compose half), 37, 25 | Task 24 depends on 23 only (no wait for AWS; D7); task 37 is numbered last but built after task 24 and before task 25 (`tasks.md` Build order) |
| C4 | none (Showcase) | The AWS half of task 24 moved to showcase item X3; not a submission milestone |
| C5 | 26, 27 | Annotations with dashboard link, environment, version |
| C6 | 28 | False-positive rule (D4); the responder runs in local Compose (H6) |
| C7 | 28 (live drill), 29 | Task 29 is the local-run demo with MailHog; no dev deploy in the drill |
| C8 | 2 (evidence note), #19 | The final re-audit has no task |
| C9 | 38 | `tasks.md` task 38 carries the daily refresh and scheduled re-scan that the n8n tasks held before H7 |

Not in these milestones: tasks 30-36 (LLM brief, brief evaluation, MCP server and
the n8n tasks: workflows, reminders, digest, export check). They are in the
showcase track (items X4-X6 in [`roadmap-showcase.md`](roadmap-showcase.md)), and
none of them scores a Tier B or C criterion.

**Ordering if AWS is slow.** If AWS setup holds up B4-B6, do B1 → B2 → B3 → C2 →
C3 → C5 → C6 → C7 on the local Compose stack (C9 any time after task 10), then B4
→ B5 → B6 → C8. Everything up to C7 is testable in CI or on the local Compose
stack, so no AWS wait blocks the observability work. The order in the tables
above stays the default because it banks the 7 Tier B points first. The one rule
that crosses the two groups: the demo-defect switch is removed (`P-FLAG-GONE`)
before the first production deploy.

## Open decisions

| # | Decision | Recommendation | Status |
|---|---|---|---|
| 1 | Groom #3-#8 together and answer one batched decision message, instead of one issue at a time | Yes | resolved 2026-10-20: groomed and answered as one batch |
| 2 | Drop #31's "blocked by #26" dependency, since the environment does not need persistence code | Yes; move before Tier B work starts, decide which environment in step 7 | resolved 2026-10-20: dropped; #31 starts once step 7 names the environment (recorded on #31) |
| 3 | Promote #17/#18 ahead of the spec commits | Yes, unless the human prefers to defer | resolved 2026-10-20: both landed before the spec commits |
| 4 | Schedule #39 (quoted filenames bypass the protected-path check) and #38 (remove the stale `agent-kit/` copy) before step 14, instead of leaving them under "Later" | Withdrawn | resolved 2026-10-20: no. The human put product work first; both stay under "Later" |
| 5 | D1: close architecture Open question 6 with the Module 4 description (one EC2 instance per environment, Compose, ECR, CloudFormation) | Yes; (A36) stands | resolved (human, 2026-10-22, via the submission-track draft): yes, but one server for both environments (H3) |
| 6 | D2: adopt the course image tag `YYYYMMDD-HHMMSS-shortsha` and add `service.version` (the tag) to the telemetry allowlist (A32) | Yes; both are `architecture.md` edits (not protected, gated by convention) | resolved (human, 2026-10-22, via the draft): kept; the tag works with GHCR |
| 7 | D3: domain name and TLS approach for the public URL (Open question 7) | Human's choice; needed before B5 | resolved (human, 2026-10-22, via the draft): answered by H5 (`sslip.io` hostnames, no domain) |
| 8 | D4: add to US-15 that on an alert with no reproducible defect (false positive or test alert) the responder explains and changes nothing | Yes; `specs.md` is protected, so a proposed diff and approval first | open |
| 9 | D5: fallback if AWS is not available in time: a kind cluster or local Compose deployment with a recorded demo (a clear demo with the deployment scores Deployment 2, but CI/CD 3 then needs a deploy target CI can reach) | Keep AWS as the plan; name the fallback date at B4 | open |
| 10 | D6: move n8n tasks 33 and 34 ahead of task 25, and add 34 to the `Depends on:` of tasks 25 and 28 (`T-JOURNEY` asserts the `notification.deliver` span n8n's report call creates, and `P-DEMO` needs n8n's retry) | Yes; keep n8n out of task 15's Compose file, so Containerization still scores first | resolved (human, 2026-10-22, via the draft): moot, the n8n tasks moved to the showcase track (H7) |
| 11 | D7: when filing the Milestone B and C issues, split task 21 (dev auto-deploy depends on 17 and 19 only; prod promotion on 18) and task 24 (Compose stack depends on 23 only; `vt-observability` on 17) | Yes; Deployment 2 and CI/CD 2 no longer wait for the prod stack, and the observability work no longer waits for AWS | resolved (human, 2026-10-22, via the draft): task 21 split (dev auto-deploy in task 21, promotion in task 18); task 24's AWS half moved to the showcase track (X3) |
| 12 | H1: two tracks, submission (this file) and showcase (`roadmap-showcase.md`, kept separate) | replaces steps 15-17 as one sequence | resolved (human, 2026-10-22) |
| 13 | H2: infrastructure as code with Terraform (or OpenTofu), not CloudFormation | replaces the 2026-10-17 decision's CloudFormation | resolved (human, 2026-10-22) |
| 14 | H3: one server runs dev and prod as two Compose projects behind two hostnames; a deploy pulls and restarts by image tag on the server; rollback runs the production deploy again with the previous tag | replaces (A36) one instance per environment | resolved (human, 2026-10-22) |
| 15 | H4: images in GitHub's container registry (GHCR), public | replaces ECR | resolved (human, 2026-10-22) |
| 16 | H5: no domain; hostnames from the server's IP via `sslip.io`, HTTPS from Let's Encrypt (VERIFY: rate limits) | replaces Open question 7 / D3 | resolved (human, 2026-10-22) |
| 17 | H6: observability, the US-14 alert and the responder run in local Compose for submission, with a recorded alert-to-fix run as evidence | replaces deployed observability (C4) and the C7 drill on dev | resolved (human, 2026-10-22) |
| 18 | H7: n8n and the other committed-scope features (LLM brief, its evaluation, MCP server, reminders and digest) move to the showcase track; the backend sends the top-tier notification itself | replaces tasks 30-36 in submission scope | resolved (human, 2026-10-22) |

## Score checkpoints

Evidenced points come only from `_docs/rubric-evidence.md`; estimates are labelled.

| Checkpoint | Expected points | Basis |
|---|---|---|
| Baseline audit (2026-10-17) | 7 | Audited |
| After step 1 | 9 | Audited 2026-10-20 at `74e9cfc`: Testing 1 and CI/CD 1 confirmed |
| After step 2 | 10 | Audited 2026-10-20 at `74e9cfc`: Problem Description 2 confirmed |
| After steps 3-6 | 10 (ASSUMPTION) | Process and spec work only; no criterion expected to move, not re-audited |
| After S0 (steps 13-14) | 10 (ASSUMPTION) | Plan work only; no criterion expected to move |
| After S1 (Tier A build) | 12 | Estimate: Tier A |
| After B2 | 14 | Estimate: + Containerization 2; S2 (B1-B3) ends at 14 |
| After B5 | 17 | Estimate: + Deployment 2, CI/CD 2 (from 1) |
| After B6 (S3) | 19 | Estimate: CI/CD 3 |
| After C3 | 21 | Estimate: + Observability 2 (moved up from the deployed-observability milestone, now showcase) |
| After C5 | 22 | Estimate: + Alerting 1 |
| After C7 (S4) | 24 | Estimate: + On-Call Agent 2 |
| After C8 (S5) | 24 | Full rubric re-audit |

The 17, 21 and 22 rows are on the order of the tables above; with the "Ordering if AWS is slow" the local milestones C3, C5 and C7 come before B4-B6, so the running totals shift, and the phase totals 12, 14, 19 and 24 stay the same.

## How to check progress

At each check-in (suggested: the end of each issue session, and at least weekly):

1. Update the Status column from the tracker (`gh issue list --state all`).
2. Note any step done out of order, and why.
3. Compare the latest audited score with the checkpoint table.
4. Add a line to the check-in log below.

Off-track signals:
- A step is `doing` while a step it depends on is not `done`.
- Work on issues listed under "Later, not scheduled" before step 14.
- A tooling issue is worked while the next product step waits, without being that step's blocker.
- The audited score is below the checkpoint for the steps already done.
- An open decision blocks the next step for more than one session.

## Check-in log

| Date | Steps done since last check-in | Audited score | On track? | Notes |
|---|---|---|---|---|
| 2026-10-19 | none (roadmap adopted) | 7 (2026-10-17 audit) | yes | Baseline |
| 2026-10-20 | step 2 implementation (#13) | 7 (not re-audited) | yes | #13 QA PASS at `e46fadf`; step 2 started ahead of step 1 at the human's request and stays `doing` until the auditor confirms Problem Description 2 |
| 2026-10-20 | steps 1 and 2; step 6 grooming; #35/#33 grooming | 10 (2026-10-20 audit) | yes | Auditor re-audited at `74e9cfc` (commit `639b9a9`) and confirmed Testing 1, CI/CD 1 and Problem Description 2. All six spec-review issues are groomed; the batched decision is still open, so step 6 stays `doing`. #35 and #33 are groomed; PM filed follow-ups #36 and #37. |
| 2026-10-20 | step 5 (#17, #18); step 6 batched answers | 10 (2026-10-20 audit) | yes | #17 (`64308d7`) and #18 (`efae1ea`) closed after QA PASS; #39 and #40 filed from #17 QA risks. The six #3-#8 answers are recorded in the issues; step 6 implementation is next. #35 is implemented (`df72298`) and waits for QA in the paused session. |
| 2026-10-20 | step 6 (#3-#8) | 10 (2026-10-20 audit) | yes | Six protected spec commits `45f6fa6`..`fdc7b51`, each with an approval record; all six QA PASS. The OpenCode orchestrator stopped during QA of #5, #7 and #8; Claude Code reran those three fresh and closed out the step. The human chose to file the QA risks outside the criteria as one follow-up, #41. Step 3 (#35 QA) is still `doing`; step 7 is next. |
| 2026-10-20 | step 3 (#35) | 10 (2026-10-20 audit) | yes | QA failed only criterion 10 (no approval record). The Claude Code orchestrator posted a record in the #18 format (6287006555), and the QA re-check passed. The human chose to file the QA risks outside the criteria as #42 (low priority). Step 4 (#33) and step 7 are next. `.scratch/` cleaned. |
| 2026-10-20 | none (review check-in) | 10 (2026-10-20 audit) | yes | Reviewed `48cbb9d` and `b1ab1e5` against the tracker: statuses match. `make verify` PASS WITH WARNINGS at `b1ab1e5`; the 7 removed assertion lines come from earlier frontend work since `origin/main`, not these commits. Placed the unscheduled follow-ups #36-#40 and #42 under "Later"; decision 4 asks whether to promote #38 and #39. Score table updated with the 2026-10-20 audit. Next: step 4 (#33), and step 7 with #41. |
| 2026-10-20 | none (reprioritised) | 10 (2026-10-20 audit) | yes | The human said the project was sidetracked by safeguards. Added the priority rule; deferred step 4 (#33) to "Later"; withdrew decision 4. Step 7 is next and starts with #41's spec commit, then the plan stages 8-14 lead to the Tier A build. |
| 2026-10-20 | none (decisions) | 10 (2026-10-20 audit) | yes | The human answered #41 D1-D3 (all option 1; comment 6287579005); D4 unanswered, so the status line stays unless answered before the spec diff. Decision 2 resolved: #31 no longer waits on #26 (comment 6287579525). #41 is unblocked; step 7 can start. |
| 2026-10-20 | #41 (first part of step 7) | 10 (2026-10-20 audit) | yes | Spec commit `1445ca5` (D1-D5 option 1), approval record 6288541138, QA PASS, assert clean PASS, closed. QA's status-model risks go to the architecture issue (human's choice). Next: the PM proposes the Stage 2 architecture issue. |
| 2026-10-20 | none (step 7 issue filed) | 10 (2026-10-20 audit) | yes | The human chose option A for Docker: Compose service containers in the sandbox, with `_docs/docker-runbook.md` for the human's part. Cloud sessions are optional only (`_docs/cloud-sessions.md`), because credit is limited. #43 (architecture) created with D1 (Compose recipe), D2 (responder: PRs only, human merges) and D3-D8 (PM recommendations) answered in 6289876616. Next: the Engineer drafts #43 Part 1 (spec diff). |
| 2026-10-20 | step 7 (#43) | 10 (2026-10-20 audit) | yes | Two human-approved spec commits (`faea412`, `3ecd54b`, records 6290689973 and 6291380101); `architecture.md` written and fixed through two QA FAILs (types.ts differences table) to PASS; the alert set to fire once with no repeat (human), re-checked PASS. #9's architecture boxes ticked; #31 told the environment (Compose dev container), so step 16 can start. Next: step 8 (#23 API contract), and #31 when the human has time for the setup. |
| 2026-10-21 | step 8 started (#23) | 10 (2026-10-20 audit) | yes | PM groomed #23; the human chose D1-D5 all option 1 (session cookie + CSRF, `forbidden`/403, current-lifecycle brief + `pending`, types/mock follow-up, manual re-scan). Engineer committed `7d6fe6e` (`openapi.yaml`), `3bdc565` (`api.md`), `dc94837` (Stage 3 text) and `49a296f` (README links). Left: fix the response-set bullet's missing 403 for `POST /assets` and rescan, approve/apply `make openapi-validate`, run the validator and broken-`$ref` case, human review of `openapi.yaml`, QA, then #27. Also corrected the permission-review rule (`1b37fd1`) at the human's direction. |
| 2026-10-21 | step 8: #23 closed | 10 (2026-10-20 audit) | yes | PM folded the senior review's A-K into the body; Engineer applied A-N (`3cb40af`, `d9817f9`); human approved the contract at `3cb40af` (record 6308766939) and the protected `openapi-validate` target (`aa066fc`, record 6308646350); validator exit 0, broken-response-`$ref` exit 2, path guard refused `../x.yaml`. QA PASS at `052f53a` (6309058776). Decision point: protected `AGENTS.md` line (`5b35ece`, record 6309239012), three spec sentences (`67a4076`, record 6309240051), architecture A30 note (`525284b`); QA re-check PASS at `13b0ee9` (6310520840). Filed #45 (D4 alignment, before #34) and #46 (QA risks, Later). Human scheduled #44 after #23, before #27. `.scratch/` cleaned. No score change (docs only). |
| 2026-10-21 | #44 (scheduled step) | 10 (2026-10-20 audit) | yes | PM groomed #44 (comment 6310709588); Engineer implemented the REST `issue-dump`/`issue-comment`/`issue-close` targets, the `guard_git.py` cloud push exception, `cloud_session_start.sh` and the settings/`AGENTS.md` changes in the protected commit `8eeaf53` (record 6313318576). QA FAILed only on two record-keeping criteria (missing matrix and live-comment URL in a comment), fixed by Engineer comment 6314178652; QA PASS at 6314208500. Decision point: #47 filed for the four outside-criteria guard/`FILE` gaps (Later); the `_docs/cloud-sessions.md` notes deferred to the § 5 trial follow-up. Closed with `make issue-close N=44`. `.scratch/` cleaned. No score change (tooling; § 5 trial still unverified). |
| 2026-10-21 | none (cloud-session setup and trial) | 10 (2026-10-20 audit) | yes | The human did the `_docs/cloud-sessions.md` § 4 setup (ruleset Active, bypass `For pull requests only`, GitHub App, environment) and ran the § 5 trial: verify 35/35 on Node 22, REST issue targets, branch push and the guard all worked; Docker and Postgres are installed but not running at start (`sudo dockerd` works). Results in § 5.1 (`1914b0e`). Filed #48 (Docker start targets; D1/D2 open) and added a `core.hooksPath` false positive to #47 (6315677576). The #27 grooming comment (11:11) is posted; #27 is next. |
| 2026-10-21 | step 8 done: #27 closed | 10 (2026-10-20 audit) | yes | Cloud session. Human chose option 1 for US-15 (#50 filed). Engineer: nine n8n/MCP operations and two bearer service credentials (`7355d8e`, `d89597a`); the human approved the contract at `7355d8e`. QA PASS (6316386844). Decision point: R2 untrusted marks (`6494f28`), then `cveId` and overview (`e74b2d1`, fixed after one QA FAIL in `fe55261`), each re-reviewed by the human; architecture notes (`7855dda`, `1f4515a`); US-12 spec line (`97893c1`, record 6316890596); R3-R5 noted on #24. Worker restart mid-session; nothing lost. `.scratch/` cleaned. No score change (docs only). Next: #45 before step 9 (#34); #50 to be groomed and placed. |
| 2026-10-21 | #45 done (before step 9); #50 groomed and placed as step 8b | 10 (2026-10-20 audit) | yes | Cloud session. PM groomed #45 (6317572464) and #50 (6317612610); the human chose D1-D4 on #45 and D1-D3 on #50, all recommended. The orchestrator found two PM errors (`AuditEntry.source` is a plain string in the contract; `vite build` does not type-check) and corrected them in the #45 comment. Engineer `72903cc` (14 frontend files, 61 tests); protected commits `0d5197b` (Makefile `frontend-typecheck`), `3f55509` (AGENTS.md line), `4e10afe` (AGENTS.md) and `b18157c` (agent-kit.conf) stop recording the test count, per the human; each has an approval record on #45. QA PASS at `3f55509` (6325826655). Filed #53 (verify-gate gaps, Later). Next: step 9 (#34) is unblocked; #50 (8b) runs after it or alongside, before step 10. No score change (mock/UI work). |
| 2026-10-21 | step 9 done: #34 closed | 10 (2026-10-20 audit) | yes | Cloud session. PM groomed #34 (6326704884); the human chose D1 (all meta in `index.html`, `head()` deleted) and D2 (C and D out to #33), both recommended. Engineer `67419b2` (62 tests; regression test run red then green). QA FAILed provisionally on criteria 9 and 10 (no way to load the page); the human approved a read-only `.scratch/` HTTP check, then QA PASS (6328697373) at `d8c2ffe`, assert clean PASS. Sign-in in a real browser was not machine-verified. QA risks noted only, no follow-up (human). `.scratch/` cleaned. No score change (frontend fix). Next: #50 (step 8b), then step 10. |
| 2026-10-22 | step 8b done: #50 closed | 10 (2026-10-20 audit) | yes | Cloud session. Engineer `6ff10d9` (`responderAuth`, two GET operations, strict `ResponderNotificationJob`; logs from Loki) and usage log `3188ce7`; the human merged PR #57 (`9a03ba9`), taken as the contract approval. QA PASS (6329301519), assert clean PASS. The human approved spec notes 1-3: `cd870df`, `54bdce3`, `147bd7a` (records 6329360243, 6329361058, 6329361312). #56 (step 10, Stage 4 testing) filed for a parallel agent; its US-15 section waits on this contract, which is now closed. QA risks go to #24 and the next `api.md` edit. `.scratch/` cleaned. No score change (docs only). Next: groom #56. |
| 2026-10-22 | step 8b follow-up: #58 (contract); step 8b row corrected to `done` | 10 (2026-10-20 audit) | yes | Cloud session, run alongside another session working #56 (step 10). Chosen as the next product task that touches neither `testing.md` nor the roadmap's step 10. PM groomed #58 (6329518860); the human chose D1 (job ids are opaque strings; the `id` order is a stable tie-break by code point) and D2 (`traceparent` always set) as recommended, and approved spec notes 1 and 3. Engineer `2e9a4dd` (descriptions only, no schema change), `4cebbd2` (`architecture.md`: every job-creating path records `notification.enqueue`), `b7b4d36` (`api.md` sentence). QA FAILed once, only because the orchestrator posted a protected-change record for `architecture.md`, which is not in `PROTECTED`; the human chose option 2 (gated by convention), and QA re-check PASS (6329743761). Spec note 2 (finding tie-break) is deferred to the next spec change. Next: #56 (step 10) in the other session, then step 11. No score change (docs only). |
| 2026-10-22 | step 10 done: #56 closed | 10 (2026-10-20 audit) | yes | Branch `claude/issue-056-stage-4-testing`, based on the merged #50/#58 work. PM groomed #56 (6329411066); the human chose D1 option 1 (a resolution is not a second alert). Engineer `8d9db69`, `2430912`: `_docs/testing.md` (385 lines), the README link, and #9's two Stage 4 rows ticked. QA PASS 6329945929 (re-check 6330289999 at `ae0d55d`), assert clean PASS. The four spec notes are deferred to #63; QA's `make verify` BASE risk and the scan advisory-source question are noted only. The branch is local; `git push*` is denied by the permission rules, so the human pushes it. No score change (docs only). Next: step 11. |
| 2026-10-22 | none in the sequence; tooling #60, #37, #61 done outside it | 10 (2026-10-20 audit) | yes | Cloud session on `claude/beautiful-lovelace-la54rn`, at the human's direction and run beside #56. PM groomed the three together (6330134485, 6330134704, 6330137277); the human chose all six decisions as recommended. Protected commits `a5b21c0` (settings), `2520c9c` (`make permission-report`), `4c42cf3` (rules and sweep procedure), each with an approval record; QA PASS on all three. Live prompt check passed in a local session (6330923566); cloud sessions cannot run it because they do not prompt for edits. Filed #65 and #66 (Later). This is an exception to the priority rule, recorded here so it is not read as off-track. No score change (tooling). Next: step 11. |
| 2026-10-22 | none in the sequence; parallel tooling track scheduled (T1-T3) | 10 (2026-10-20 audit) | yes | Same cloud session. At the human's direction #53, #48 and #31 are scheduled on a parallel tooling track below the step table, not as numbered steps: T1 (#53) before step 15 and #24, T2 (#48) then T3 (#31) before step 17. PM groomed them together (6331077862, 6331105969, 6331091593, 6331105799); the human chose D1-D5 as recommended (6331160446). Filed #67 (CI passes a real `BASE`) and #68 (run #26's persistence test against Postgres), both Later. Grooming only; no protected commit yet. No score change (tooling). Next: step 11; T1 may start beside it. |
| 2026-10-22 | none in the sequence; T1 (#53) done | 10 (2026-10-20 audit) | yes | Cloud session on `claude/start-53-7oaxg3`. Protected commits `bdda483` (`verify.sh`, `verify.md`), `e0cf368` (`agent-kit.conf`), `1d869a5` (`AGENTS.md`) and `3d978fe` (one-line stderr fix QA found), each with an approval record on #53; `make verify` now runs `make frontend-typecheck`, fails on an unresolvable `BASE` and warns when `BASE` equals `HEAD`. QA PASS (6331468388), assert clean PASS. T1 is done, so step 15 and #24 are unblocked on `agent-kit.conf`. #67 (CI passes a real `BASE`) stays Later. No score change (tooling). Next: step 11. |
| 2026-10-22 | step 11 done: #72 closed | 10 (2026-10-20 audit) | yes | Local sandbox session on `main`. The human approved filing #72 and chose D1 (three rubric-tier milestones A/B/C, then a Committed scope section) and D2 (one Milestone A planning-evidence task), both recommended (6331775484). PM groomed (6331821940); Engineer `05e3e60` (36 tasks, `_docs/tasks.md` and the README link) and `ae6b708` (US-15 `Covers:` alignment). QA PASS (6332195958), re-check PASS (6332346303); assert clean PASS and HEAD unchanged after each. Follow-ups filed at the decision point: #73 (README `withdrawn` and Stage 5 tier-label note; no "fast lane" exists, so normal process) and `andrew-chung-au/agent-kit` #19 (task-template is the issue template, not the Stage 5 task format). Other QA risks (tasks 9, 10, 28, 29 size; task 17 deploy wording) are noted for step 12. No score change (docs only). Next: step 12 (backlog issues from `tasks.md`). |
| 2026-10-22 | step 12 started: Milestone A backlog filed | 10 (2026-10-20 audit) | yes | Same local session. PM proposal: 38 issues from the 36 tasks (splits 9a/9b and 10a/10b). The human approved filing Milestone A now, closing #24/#25 and rewriting #26, the two splits, accepting the four #63 notes before Milestone C, and deciding the LLM/responder runtime at Milestone C/Committed start with stubs. Filed #74 (task 1), #75 (task 2), #26 rewritten as task 3, #76-#88 (tasks 4-14); close notes 6333191444 (#24) and 6333194914 (#25), both closed. Issue 1's criteria keep the existing frontend suite inside `make test` rather than dropping it, so `make verify` does not lose coverage (orchestrator correction to the PM draft; task 13's growth is preserved). B/C/Committed file at their milestone boundaries. Next: finish step 12 at Milestone B, and step 13 (`plan-summary.md`). |
| 2026-10-22 | none in the sequence; Tier B/C draft merged into step 17 | 10 (2026-10-20 audit) | yes | Local sandbox session on `main`. Merged `_docs/roadmap-tiers-b-c.md` into step 17 as milestones B1-B6 (Tier B) and C1-C8 (Tier C), with task-number mapping, prerequisites, the AWS-slow ordering and B/C checkpoints; moved D1-D7 into "Open decisions"; removed a stray `=======` left in the previous check-in by merge `de0c25d`; deleted the draft. Task boundaries follow `_docs/tasks.md` (the draft's splits of tasks 15, 17, 21 and 24 are checkpoint groupings; D7 proposes splitting 21 and 24 at filing). No score change (docs only). Next: step 13 (`plan-summary.md`), the last gate before the plan review and the Tier A build. |
| 2026-10-22 | step 13 done: #91 closed | 10 (2026-10-20 audit) | yes | Same local session. PM groomed #91 (6334007642); Engineer `731f11b` (`_docs/plan-summary.md`, 12-row rubric map, 9 risks, 106-entry register, Stage 6 checklist) and `e8e4ddb` (literal `ASSUMPTION:` labels), plus README link. QA FAILed once on broad word-match counts in the completeness table and the resulting false PASS; Engineer `882c75d` recomputed label-only counts with locations and fixed the checklist evidence; QA re-check PASS (6336177091) at `882c75d`. Human decisions: defer the Q2-Q4 spec note to the next spec change; file one follow-up for the tasks.md Application/task 15 discrepancy (#95), with README `withdrawn` left to #73; note only the minor checklist recount wording. `.scratch/` cleaned. No score change (docs only). Step 14 still depends on step 12 (Milestone B/C filing); next is finishing step 12 at the Milestone B boundary or the human's call on that dependency. |
| 2026-10-22 | none in the sequence; #73 done (outside the step sequence) | 10 (2026-10-20 audit) | yes | #73 done: commits `0aa61b1` and `6248c29`; PM comment 6334306395, human answers 6334352037, Engineer 6334375597, QA PASS 6334401494; assert-clean PASS at `6248c29`. No step moves. No score change (docs only). (Folded in from #92 item 2.) |
| 2026-10-22 | none in the sequence; `_docs/aws-setup.md` added (outside the step sequence) | 10 (2026-10-20 audit) | yes | `_docs/aws-setup.md` (the human-side AWS and GitHub setup for the Tier B/C deployment) added in commit `25960f5`, outside the step sequence; later revised under #103. No step moves. (Folded in from #92 item 2.) |
| 2026-10-22 | none in the sequence; submission track merged into the main roadmap (#93) | 10 (2026-10-20 audit) | yes | Local sandbox session on `main`. Steps 15-17 became phases S1-S5 (S0 is steps 13-14), with the draft's "Done when" and estimates 12, 14, 19, 24; the Tier B/C section follows H1-H7 (B4 on GHCR, B5 and B6 on one server, C1 and C4 marked showcase, C3 scoring Observability 2, C7 local) and gained C9 for task 38; H1-H7 are recorded as resolved and D1, D2, D3, D6, D7 as resolved, with D4 and D5 open; the submission draft is deleted; `roadmap-showcase.md` is linked and unchanged; the README links this guide and the showcase roadmap; the Budgets prerequisite row points at `_docs/aws-setup.md` and stays open; Status refreshed from the tracker. Differences left between the roadmap and `tasks.md`/`architecture.md`: the draft has no row for task 38 (added as C9, following `tasks.md`); `service.version` is not yet in the `architecture.md` allowlist (A32), so D2 is kept but half applied; `roadmap-showcase.md` line 3 still names the deleted draft (the file is not edited here); `testing.md` line 175 (prose) still names MailHog for `I-OWNER-SEND`. A second commit, made right after this one, holds the small clean-ups: the two `testing.md` owner-notification rows moved to an in-process fake mail sink, the task 17 and task 37 sentences in `tasks.md`, the showcase marks and the LLM-key row in `architecture.md`, and the A37 cell in `plan-summary.md`. The GitHub milestones "Submission" and "Showcase" are not created yet (tracker write, needs approval). No score change (docs only). Next: step 14 (plan review). |
| 2026-10-22 | none in the sequence; pre-review clean-up (#107) | 10 (2026-10-20 audit) | yes | Local sandbox session on `main`. Human decision (Q1 option 1): step 14 now depends on steps 11 and 13 (Milestone A filed) and its "Done when" drops "and the spec"; Milestone B, C and Committed issues are filed at their boundaries and no longer gate step 14. Stale Deployment wording in `planning-process.md`, the `plan-summary.md` register and counts, and `service.version` in the `architecture.md` A32 allowlist (D2) brought in line with H2-H7. No score change (docs only). Next: step 14 (plan review, #108). |
| 2026-10-22 | none in the sequence; step 14 pre-review edits (#108 stage 1) | 10 (2026-10-20 audit) | yes | Local sandbox session on `main`. Added the task 17 OIDC provider verification row to the `plan-summary.md` register (113 entries); fixed the stale #31 step cross-reference in `architecture.md` to T3; applied the human decisions of 2026-10-22: A16-A18 confirmed, Open questions 8 and 10 closed, the no-CVE sentence added to Prioritisation, plan-summary risk R10 and source discrepancy D8 added (`specs.md` wording left as written, aligned at the next approved spec change). No score change (docs only). The Reviewer run, the README wording and the `AGENTS.md` phase line come after QA PASS. |
