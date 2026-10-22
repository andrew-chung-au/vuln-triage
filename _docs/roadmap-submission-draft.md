# VulnTriage roadmap: submission track (temporary draft)

Status: temporary, drafted 2026-10-22 at the human's request while another session works roadmap step 13 (`_docs/plan-summary.md`). It does not change `_docs/roadmap.md` or `_docs/roadmap-tiers-b-c.md`. The merge is a follow-up issue: fold this file and `_docs/roadmap-tiers-b-c.md` into `_docs/roadmap.md` as one main roadmap for Tiers A, B and C, then delete both drafts. The showcase work after submission lives in `_docs/roadmap-showcase.md`, which stays a separate file after the merge.

Goal: every rubric point evidenced (24/24) by the first submission deadline, in the smallest shape that meets the criteria in `_docs/rubric.md` and the course's project requirements (a rollback path, an alert trigger, an on-call responder; peer review of three other projects is required to pass). Anything that scores nothing goes to the showcase track instead of being dropped.

Deadline: set by the human from the course platform (not recorded here yet).

## Decisions (human, 2026-10-22)

| # | Decision | Replaces |
|---|---|---|
| H1 | Two tracks: submission (this file) and showcase (`_docs/roadmap-showcase.md`, kept separate) | Steps 15-17 as one sequence |
| H2 | Infrastructure as code with Terraform (or OpenTofu), not CloudFormation | The 2026-10-17 decision's "CloudFormation"; architecture Deployment's stack table |
| H3 | One server runs both dev and prod, as two Compose projects behind two hostnames; a deploy pulls and restarts by image tag on the server; rollback runs the production deploy again with the previous tag | (A36) one instance per environment; deploys by stack update |
| H4 | Images in GitHub's container registry (GHCR), public | ECR and the `vt-ecr` stack |
| H5 | No domain: hostnames from the server's IP via `sslip.io`, HTTPS from Let's Encrypt (VERIFY: rate limits) | Open question 7 / D3 |
| H6 | Observability, the US-14 alert and the responder run in local Compose for submission, with a recorded alert-to-fix run as evidence | `vt-observability` and milestone C4; C7's drill on dev |
| H7 | n8n and the other committed-scope features (LLM brief, its evaluation, MCP server, reminders and digest) move to the showcase track; the backend sends the top-tier notification itself | Tasks 30-36 in submission scope |

Why (one line each): the rubric scores Deployment 2 for a public URL or a clear demo, CI/CD 3 for dev auto-deploy plus a manual production deploy, and Observability 2 for signals "viewable in a UI", none of which needs separate servers or deployed observability. Each change removes standing cost or setup steps, and each removed piece returns as a showcase item without rework (except deployed observability, which also moves the responder to AWS).

H2-H7 need document changes before plan review (step 14); see "Documents to update". H7 changes the protected `_docs/specs.md`, so it needs a proposed diff and the human's approval.

## Phases

Each phase banks points. **Cutoff rule:** if the deadline is close, stop at the last finished phase and submit; S1 alone passes (12 of the 10 needed). The course's second attempt is a safety net, not part of the plan.

| Phase | Main roadmap step / Tier B-C milestone | `tasks.md` tasks | Done when | Score after (estimate) |
|---|---|---|---|---|
| S0 Plan settled | Steps 13-14 | — | Plan review passed with H2-H7 applied to `architecture.md`, `tasks.md` and the spec | 10 |
| S1 App | Step 15 (Tier A) | 1-14 | Frontend, backend and database work end to end; unit and integration tests run with one command | 12 |
| S2 Containers and CI | B1-B3 | 15, 16, 19, 20 | `make` target starts the full stack with Postgres in Compose; CI runs tests on every pull request | 14 |
| S3 Deploy | B4-B6, reshaped by H2-H5 | 17, 18, 21, 22 (reshaped) | Terraform builds the server; a push to `main` deploys to dev when tests pass; a manual workflow in the GitHub `production` environment deploys the same image tag to prod; one rollback rehearsed and recorded; deployment steps and teardown in the README | 19 |
| S4 Observe and respond | C2, C3, C5, C6, C7 (local), plus the H7 notification | 23, 24 (Compose half), 25-29, plus a new task for the backend's top-tier email | Signals for the key journey share a trace ID and are viewable in local Grafana; the US-14 alert fires from the demo-defect switch; the responder opens a fix pull request; the run is recorded; the defect switch is removed before any prod deploy | 24 |
| S5 Submit | C8 | 2 (evidence note), #19 | README has the public URL, the one-command start, the recordings and the rollback steps; full rubric re-audit; time reserved for the three peer reviews | — |

## Changes from `_docs/roadmap-tiers-b-c.md`

- B4: no `vt-ecr` (H4); the GitHub OIDC role only needs to run the deploy on the server (VERIFY: SSM Run Command or an equivalent), and Terraform state needs a small S3 bucket (VERIFY: S3-native state locking).
- B5 and B6 merge onto one server (H3). Task 18 shrinks to a second Compose project and hostname; the manual production workflow and the rollback rehearsal stay. D7's split of task 21 still applies.
- C1 (n8n) moves to the showcase track (H7); the backend's own top-tier email replaces task 34 in submission scope. Check task 33's daily refresh and scheduled re-scan against the spec when the PM reshapes the tasks.
- C3 now scores Observability 2 (checkpoint 21 moves from C4 to C3). C4 moves to the showcase track (H6).
- C7 runs locally: defect switch, alert, responder pull request, merge, local check, recording.
- Decisions: D1 yes but one server for both environments (H3); D2 kept (the tag works with GHCR); D3 answered by H5; D4 unchanged; D5 unchanged (a kind deployment can't be reached by GitHub-hosted runners, so it can't score CI/CD 3); D6 moot (H7); D7 task 21 still splits, task 24's AWS half moves to the showcase track.

## Documents to update (before step 14)

- `_docs/architecture.md`: Deployment (stack table to Terraform modules, (A36), (A37), cost controls, teardown), the Components CI/CD row (GHCR), Observability (`vt-observability` for showcase only), Responder agent placement (A34: local for submission), Open questions 6 and 7.
- `_docs/tasks.md`: tasks 17, 18, 21, 24 and 29 reshaped; a new task for the backend's top-tier notification; tasks 30-36 moved to a showcase section.
- `_docs/specs.md` (protected): the H7 features move to a "Showcase (post-submission)" section; the human approves the diff.
- `_docs/aws-setup.md`: rewrite for Terraform, one server, GHCR, `sslip.io`, the state bucket and about $0 standing cost while down.
- `_docs/plan-summary.md` (step 13's output): update its rubric map and risks if it lands before these changes.
