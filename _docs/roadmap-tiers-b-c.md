# VulnTriage roadmap: Tiers B and C (temporary draft)

Status: temporary, drafted 2026-10-22 at the human's request while another session works step 11 (`_docs/tasks.md`). It does not change `_docs/roadmap.md`. Merge it in when convenient (see "Merging into the main roadmap"), then delete this file.

Why it exists: the main roadmap plans Tier A in detail (steps 11-15) but gives Tiers B and C one row, step 17 ("Tier B and C build"), for 8 criteria and 12 of the 24 points. This file splits that row into milestones with an order, dependencies, a "done when" and a score checkpoint for each.

Sources: `_docs/rubric.md`; the course's Module 3 (containerize and deploy) and Module 4 (DevOps and observability) notes and homework the human shared on 2026-10-22; `_docs/architecture.md` (Components, Observability, Responder agent, Deployment); `_docs/testing.md` (US-13, US-14, US-15, CI jobs). Where this file and those documents differ, they win and the difference is a defect here, except for the proposals under "Decisions for the human".

Conventions: milestone ids `B1`.. and `C1`.. are local to this file; "Mapping to `tasks.md`" gives the Stage 5 task numbers for each (from PR #89, step 11). Sizes are S, M or L, relative only (ASSUMPTION: no hour estimates until `tasks.md` exists). `VERIFY:` marks an external detail not yet confirmed.

## What the course pattern settles

The Module 4 notes answer architecture Open question 6 ("What exactly is the Module 3/4 pattern?"): CloudFormation on AWS, one EC2-based stack per environment (dev, then a prod copy), images built once and pushed to Amazon ECR, GitHub Actions deploying to dev on every push to `main` and promoting to prod by a manual workflow, and a separate observability Compose project (Collector, Prometheus, Loki, Tempo, Grafana). The notes list ECS as a "beyond the module" improvement. So (A36), one instance per environment running Compose, matches the pattern and needs no change. Proposed: close Open question 6 with this (decision D1 below).

| Course practice | Plan today | Gap or proposal |
|---|---|---|
| Image tag `YYYYMMDD-HHMMSS-shortsha`, sortable and traceable | Tag with the commit SHA; record each digest (architecture Deployment, pipeline step 2) | D2: adopt the course tag; keep recording the digest |
| Telemetry carries service name, environment and deployed version | Allowlist has `service.name`, `deployment.environment`; no version | D2: add `service.version` (= the image tag) to the allowlist (A32) so an incident maps to a release |
| `observability/` as its own Compose project, deployed apart from the app | `vt-observability` stack on its own instance | Consistent; use `observability/` as the repository folder |
| Alert payload names service, environment, version, owner and dashboard URL | Labels: `finding_id`, `tier` only (no excluded data) | Add the dashboard link and environment/version as annotations, not labels, so the one-alert-per-finding grouping stays |
| Responder: on a false positive, explain and change nothing; smallest fix; tests must pass | Responder opens a PR with a failing test and a fix | D4: add the false-positive rule (spec change, protected) |
| A deliberate bug that existing tests miss, to prove the loop | `VT_DEMO_DEFECT=notify_no_fix`, refused in production | Consistent; the flag is the safer form |
| Rollback listed as "beyond the module" | Re-promote the previous digest (architecture Deployment) | The rubric task list says "a rollback path", so B6 rehearses it once |
| kind/Kubernetes and `act` (Module 3 homework) | Not in the plan | Not needed for any criterion; kept only as the fallback in D5 |

## Prerequisites (human, can start now)

None of these waits for step 11; most are the human's.

| Item | Needed by | Owner | Notes |
|---|---|---|---|
| T2 (#48) then T3 (#31): Docker in cloud sessions and the Compose Postgres recipe | B2 | agents, human for the dev-container rebuild | Main roadmap parallel tooling track, step 16 |
| AWS account with an AWS Budgets alert (A37 amount) | B4 | human | Set before any stack exists |
| Domain name and TLS approach (architecture Open question 7) | B5 | human | D3 |
| GitHub `production` environment with the human as required reviewer | B6 | human | VERIFY: available on this repository's plan |
| `main` branch protection that refuses the responder's push (D2 of #43) | C6 | human | Already required by the architecture |
| LLM provider for the brief (Open question 9) and the responder's agent runtime | Tier A, C6 | human | The responder runtime is a dependency: ask before adding |

## Tier B: deployment path (target 19 of 24)

Starts when step 15 (Tier A build) is `done`; B1-B3 need only Docker, not AWS.

| # | Milestone | Depends on | Done when | Criteria | Size |
|---|---|---|---|---|---|
| B1 | Images: multi-stage Dockerfiles for backend and frontend, non-root, health checks, backend listens on `0.0.0.0` | step 15 | Both images build in CI; each container answers its health check | Containerization | S |
| B2 | Compose stack: `compose.yaml` with frontend, backend and `postgres` (named volume, health checks, `depends_on` healthy), `.env.example`, one start target; #68 runs #26's persistence test against Postgres | B1, T3 | `docker compose up --build -d --wait` (through a `make` target) starts everything; data survives a restart; auditor marks Containerization 2 | Containerization, Application | M |
| B3 | CI on every pull request: the `testing.md` job table up to `postgres-integration` and `security-scan`, plus image builds; #67 passes a real `BASE` | B2 | Every job runs on a PR and fails the PR when red; auditor re-confirms CI/CD 1 with Testing 2 | CI/CD, Testing | M |
| B4 | AWS foundation: `vt-ci-iam` (GitHub OIDC, dev and prod roles) and `vt-ecr`; on push to `main`, build once, tag (D2), push, record the digest | B3, AWS account | An image tagged from a `main` commit is in ECR, pushed by OIDC with no long-lived AWS key | CI/CD | M |
| B5 | Dev environment: `vt-dev` stack (Compose on one instance, TLS proxy); push to `main` deploys the new tag to dev only when tests pass | B4, D3 | The app is reachable at the dev URL; a pushed change appears there with no manual step; a red test leaves the old version running; auditor marks Deployment 2 and CI/CD 2 | Deployment, CI/CD | L |
| B6 | Production and rollback: `vt-prod` from the same template; manual workflow in the `production` environment promotes the tag running in dev, never rebuilding; rollback by promoting the previous tag, rehearsed once; `docs/DEPLOYMENT.md` (or a README section) with the steps and teardown | B5 | Prod runs the same digest as dev; one recorded rollback; auditor marks CI/CD 3 | CI/CD, Deployment | M |

Cost controls go in with B4-B6, not after: the budget alert, the nightly stop of dev (and later observability), and the ECR lifecycle rule (architecture Deployment, Cost controls).

**Checkpoint after B6: 19** (Tier A 12 + Containerization 2 + Deployment 2 + CI/CD 3).

## Tier C: observability, alert, on-call (target 24 of 24)

C1-C3 and C5 can run on the local Compose stack before B4-B6 finish; only C4 and C7 need the deployed environments.

| # | Milestone | Depends on | Done when | Criteria | Size |
|---|---|---|---|---|---|
| C1 | n8n routing in Compose: the top-tier notification job path (US-8) with a mail catcher, and the exported workflows (US-16) | B2 | A top-tier finding's job is claimed, delivered to the mail catcher and reported back; `W-EXPORT` passes | Application (committed scope); the US-13 journey needs it | M |
| C2 | Backend instrumentation: OpenTelemetry SDK and FastAPI auto-instrumentation; the US-13 spans, `vt_notifications_total`, `vt_notification_delivery_seconds`, `vt_top_tier_notification_overdue`; JSON logs with `trace_id`; the allowlist helper; `service.name`, `deployment.environment`, `service.version`; no-op without a Collector (A40) | step 15 (C1 for `notification.deliver`) | With a console exporter, one scan shows a span, a metric and a log line with the same trace ID and no excluded data | Observability | M |
| C3 | Observability stack in `observability/`: Collector with the allowlist processor, Prometheus, Loki, Tempo, Grafana with provisioned data sources and the "US-13 journey" dashboard, filterable by environment and version | C2 | `T-JOURNEY` and `T-REFUSE` pass in Compose; the three signals show side by side in local Grafana | Observability | L |
| C4 | Deploy observability: `vt-observability` stack, Grafana behind a login; dev and prod export to it | C3, B5 (B6 for prod) | The same journey, run on dev, is visible in the deployed Grafana; auditor marks Observability 2 | Observability | M |
| C5 | US-14 alert as code: the provisioned rule, notification policy and contact points (email and responder webhook); annotations with dashboard link, environment, version | C3 | `A-FIRE`, `A-HELD`, `A-TIER`, `A-GAP`, `A-RESOLVE` pass; auditor marks Alerting 1 | Alerting on User Impact | S |
| C6 | Responder: webhook receiver (bearer secret, repeat-fingerprint guard) that starts one headless agent run per alert in a fresh checkout; `RESPONDER_MODE=stub` in CI; read-only API and Loki tokens; branch `responder/<fingerprint>` and a pull request; every action logged; false-positive rule if D4 is approved | C5, #50's contract (closed) | `I-RESP-*` and the stubbed `P-DEMO` pass in CI; a test alert with no incident ends with "no change" and an explanation | On-Call Agent | M |
| C7 | End-to-end drill on dev: `VT_DEMO_DEFECT=notify_no_fix` → job fails → metric 1 → one alert → responder PR → human merges → CI deploys to dev → n8n retries → delivered → alert resolves; recorded (screenshots or a short video) as review evidence; then the cleanup commit removes the flag and `P-FLAG-GONE` passes before any prod promotion | C4, C6, B6 | The drill is recorded and linked from the README; the flag is gone; auditor marks On-Call Agent 2 | On-Call Agent, Alerting, Observability | M |
| C8 | Close-out: README sections for deployment, observability and the responder; #19 (AI usage report); full rubric re-audit; teardown plan ready for after grading (the human runs it) | C7 | `_docs/rubric-evidence.md` shows all 12 criteria MET | all | S |

**Checkpoints: after C4, 21; after C5, 22; after C7, 24.**

## Mapping to `tasks.md`

Task numbers are from `_docs/tasks.md` as proposed in PR #89 (step 11, QA PASS). Step 12 files the Milestone B, C and Committed-scope issues at each milestone boundary; this file is input to that filing, not a second backlog.

| Milestone | `tasks.md` tasks | Difference |
|---|---|---|
| B1 | 15 (Dockerfiles) | none |
| B2 | 15, 16; #68 | none |
| B3 | 19, 20 | none |
| B4 | 17 (`vt-ci-iam`, `vt-ecr`) | Image tag format (D2) |
| B5 | 17 (`vt-dev`), 21 (dev half), then 22 (pilot seed data) | Task 21 depends on 18, so the dev auto-deploy waits for the prod stack; D7 |
| B6 | 18, 21 (prod half) | none |
| C1 | 33, 34, 36 (Committed scope) | `tasks.md` puts n8n after Milestone C; D6 |
| C2 | 23 | `service.version` in the allowlist (D2) |
| C3 | 24 (Compose half), 25 | Task 24 depends on 17, so the local stack waits for AWS; D7 |
| C4 | 24 (`vt-observability` half) | none |
| C5 | 26, 27 | Annotations with dashboard link, environment, version |
| C6 | 28 | False-positive rule (D4) |
| C7 | 28 (live drill), 29 | none |
| C8 | 2 (evidence note), #19 | The final re-audit has no task |

Not in this file's milestones: tasks 30-32 and 35 (LLM brief, brief evaluation, MCP server, reminders and digest). They are committed scope, and none of them scores a Tier B or C criterion.

## Ordering if AWS is slow

If AWS setup or the domain name holds up B4-B6, do B1 → B2 → B3 → C1 → C2 → C3 → C5 → C6 on the local Compose stack, then B4 → B5 → B6 → C4 → C7. Everything up to C6 is testable in CI with Compose, so no AWS wait blocks the observability work. The order in the tables above stays the default because it banks the 7 Tier B points first.

## Score checkpoints

| After | Expected points | Basis |
|---|---|---|
| Step 15 (Tier A) | 12 | Main roadmap |
| B2 | 14 | Estimate: + Containerization 2 |
| B5 | 17 | Estimate: + Deployment 2, CI/CD 2 (from 1) |
| B6 | 19 | Estimate: CI/CD 3 |
| C4 | 21 | Estimate: + Observability 2 |
| C5 | 22 | Estimate: + Alerting 1 |
| C7 | 24 | Estimate: + On-Call Agent 2 |

Estimates only; evidenced points come from `_docs/rubric-evidence.md`. Pass mark is 10, so Tier A alone passes; the B and C points are margin against an auditor or peer reviewer scoring a criterion lower.

## Decisions for the human

| # | Decision | Recommendation |
|---|---|---|
| D1 | Close architecture Open question 6 with the Module 4 description above (one EC2 instance per environment, Compose, ECR, CloudFormation) | Yes; (A36) stands |
| D2 | Adopt the course image tag `YYYYMMDD-HHMMSS-shortsha` and add `service.version` (the tag) to the telemetry allowlist (A32) | Yes; both are `architecture.md` edits (not protected, gated by convention) |
| D3 | Domain name and TLS approach for the public URL (Open question 7) | Human's choice; needed before B5 |
| D4 | Add to US-15: on an alert with no reproducible defect (false positive or test alert), the responder explains and changes nothing | Yes; `specs.md` is protected, so a proposed diff and approval first |
| D5 | Fallback if AWS is not available in time: a kind cluster or local Compose deployment with a recorded demo ("a clear demo with the deployment" scores Deployment 2, but CI/CD 3 then needs a deploy target CI can reach) | Keep AWS as the plan; name the fallback date at B4 |
| D6 | Move n8n tasks 33 and 34 ahead of task 25, and add 34 to the `Depends on:` of tasks 25 and 28: `T-JOURNEY` asserts the `notification.deliver` span that n8n's report call creates, and `P-DEMO` needs n8n's retry, but `tasks.md` schedules n8n after Milestone C | Yes; keep n8n out of task 15's Compose file, so Containerization still scores first |
| D7 | When filing the Milestone B and C issues, split task 21 (dev auto-deploy depends on 17 and 19 only; prod promotion on 18) and task 24 (Compose stack depends on 23 only; `vt-observability` on 17) | Yes; Deployment 2 and CI/CD 2 no longer wait for the prod stack, and the observability work no longer waits for AWS |

## Merging into the main roadmap

When PR #89 (step 11) has merged and it is convenient (not while another session edits `_docs/roadmap.md`):
1. Replace step 17 with rows for B1-B6 and C1-C8, using the task numbers in "Mapping to `tasks.md`" (or the step 12 issue numbers once filed) and keeping this file's "depends on" and "done when".
2. Add the B and C checkpoints to the main score table.
3. Move the decisions the human has answered into the main "Open decisions" table and the relevant documents.
4. Delete this file in the same commit and add a check-in line.

Check against `tasks.md` while merging: its Tier B and C milestones (Stage 5 rules) may group the work differently; where they differ, `tasks.md` wins on task boundaries and this file only on order and checkpoints.
