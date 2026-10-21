# VulnTriage roadmap

The order in which open work is done, and the checks used to tell whether the
project is on track. It sequences the work; it is not part of the build plan
that the plan review checks (`_docs/planning-process.md` Stages 1-6).

- Adopted: 2026-10-19, from a review of opencode's status analysis (Claude Code, claude-opus-5-5); see `_docs/ai-usage-log.md`.
- Goal: 24/24, built as Tier A → B → C milestones (human decision of 2026-10-17; tiers in `_docs/reviews/2026-10-16-final-rubric-impact.md` §5).
- Timing and scope trade-offs are the human's. "On track" here means steps are done in order and the audited score meets the checkpoint for the steps done.
- Source of truth for status: the GitHub tracker and `_docs/rubric-evidence.md`. The status column here is a snapshot taken at each check-in, not live state.

## Priority rule

VulnTriage is the product; the agent kit and dev container are tooling. From 2026-10-20 (human direction), the next product step always comes first. Kit, hook and dev-container issues go under "Later, not scheduled" unless one blocks the next product step, and then it joins that step's row. The one tooling step kept in the sequence is step 16, because Postgres needs it.

## Sequence

Status values: `todo`, `doing`, `done`, `blocked`, `deferred`. A step starts only when the steps it depends on are `done`; a `deferred` step does not block anything.

| # | Step | Issues | Depends on | Done when | Status (2026-10-21) |
|---|---|---|---|---|---|
| 1 | Refresh the rubric evidence | (auditor skill) | none | `_docs/rubric-evidence.md` re-audited at current `main`; confirms or rejects Testing 1 and CI/CD 1 | done (2026-10-20 audit, 10/24 at `74e9cfc`) |
| 2 | README problem description | #13 | none | Auditor marks Problem Description MET (2) | done (auditor confirmed MET 2) |
| 3 | Push check plan-mode fix | #35 | none | #35 closed | done (`df72298`, QA PASS after the approval record; closed 2026-10-20; follow-up #42) |
| 4 | Remaining #15/#20 findings | #33 | none | #33 closed | deferred (2026-10-20, priority rule: tooling hardening; moved to "Later") |
| 5 | Approval-record hardening | #17, #18 | none | Both closed before the step 6 protected commits, or the human defers them | done (both closed 2026-10-20) |
| 6 | Spec review issues | #3, #4, #5, #6, #7, #8 | none | PM grooms all six together; one batched decision message to the human; each implemented as its own protected commit; all six closed | done (six protected commits `45f6fa6`..`fdc7b51`, all QA PASS, closed 2026-10-20; follow-up #41) |
| 7 | Stage 2: `_docs/architecture.md` (next) | #41, then #43 | 6 | #41's spec commit landed; Stage 2 checklist PASS; #9's architecture rows ticked; Docker-capable environment named; #9 hosting decision closed as AWS (CloudFormation) | done (#41 `1445ca5`; #43: spec `faea412` and `3ecd54b`, `architecture.md` `072c17e`..`4180fe3`, QA PASS, closed 2026-10-20) |
| 8 | Stage 3: API contract | #23, then #27 | 7 | Both closed | done (#23 and #27 closed 2026-10-21; US-15's responder contract split out as #50) |
| 8b | Stage 3 completion: responder read-only contract | #50 | 8 | #50 closed; the human approved the contract diff; `make openapi-validate` exits 0 | todo (groomed 2026-10-21, D1-D3 option 1; runs after #45) |
| 9 | Frontend SPA shell | #34 | 8 (#23), #45 | #34 closed (test count in its criteria updated to 35 at grooming) | todo |
| 10 | Stage 4: `_docs/testing.md` | new issue | 8, 8b | Stage 4 checklist PASS; #9's testing rows ticked | todo |
| 11 | Stage 5: `_docs/tasks.md` | new issue | 10 | Stage 5 checklist PASS (no cycles; every story and criterion covered) | todo |
| 12 | Backlog issues from `tasks.md` | new issues | 11 | PM proposal approved by the human; each issue carries its story's acceptance criteria | todo |
| 13 | Stage 6: `_docs/plan-summary.md` | new issue | 11 | Stage 6 checklist PASS (all 12 criteria mapped) | todo |
| 14 | Plan review and phase change | new issue | 12, 13 | Review passed; human-approved `AGENTS.md` phase line committed | todo |
| 15 | Tier A build | #24 → #25 → #26, then step 12 issues | 14 | Auditor: Application 2, Testing 2 | blocked (phase line) |
| 16 | Docker-capable environment | #31 | 7 | Compose runs Postgres in the dev environment | todo (decision 2 resolved; human performs the change) |
| 17 | Tier B and C build | step 12 issues | 15, 16 | Auditor: all 12 criteria MET | todo |

**#44 (cloud sessions, human direction 2026-10-21):** done (2026-10-21), after #23 and before #27. It is tooling, so the priority rule would have left it under "Later"; the human scheduled it here because it unblocks #31 and the Docker-dependent build steps. #44's own criteria had the orchestrator close it with the new `make issue-close N=44` target.

Later, not scheduled (tooling and process; see the priority rule): #10, #16, #19, #29, #30, #33, #36, #37, #38, #39, #40, #42, #46, #47. #38 carries out the human's 2026-10-20 remove decision for #36; #36 can close when #38 does. #19 (ai-usage-report) is graded evidence; pick it up with the Tier C work.

#48 (cloud `docker-start`/`docker-stop` targets, filed 2026-10-21 from the cloud trial) waits for the human's D1 (is the cloud an acceptable Docker route, given the agent controls the daemon there) and D2 (step 16's row, or "Later"). Until then it is not scheduled.

#50 (the US-15 responder's read-only API contract, split out of #27 by the human on 2026-10-21) is step 8b, groomed with the human's D1-D3 answers; it runs after #45.

#45 (the D4 `types.ts`/mock/UI alignment, filed from #23) is not in the step sequence: it starts after #23 and before step 9 (#34), and #34/#25 wait for it. Groomed 2026-10-21 (D1-D4 option 1); D4 adds a protected `make frontend-typecheck` target that needs the human's approval at commit time.

#41 and #43 completed step 7. Leftovers from #43 (human's choice: recorded here and on #23, no new issue):
- **Step 8 (#23):** comment 6301758496 covers which brief the API returns, a "no brief yet" state, status codes, wire values and the types.ts differences table.
- **Step 10 (Stage 4 testing):** a test that the US-14 gauge's `tier` label is the job's tier; the alert must not resolve and re-fire after a metric gap (Grafana no-data and error-state handling, `VERIFY:`); and whether Grafana's "resolved" message counts as a second alert.
- **Next spec change:** E10's wording on uv workspace entries; US-2 on the project's own `uv.lock` package. Also `VERIFY:` tags on the OpenTelemetry attribute names in `architecture.md`.

## Open decisions

| # | Decision | Recommendation | Status |
|---|---|---|---|
| 1 | Groom #3-#8 together and answer one batched decision message, instead of one issue at a time | Yes | resolved 2026-10-20: groomed and answered as one batch |
| 2 | Drop #31's "blocked by #26" dependency, since the environment does not need persistence code | Yes; move before Tier B work starts, decide which environment in step 7 | resolved 2026-10-20: dropped; #31 starts once step 7 names the environment (recorded on #31) |
| 3 | Promote #17/#18 ahead of the spec commits | Yes, unless the human prefers to defer | resolved 2026-10-20: both landed before the spec commits |
| 4 | Schedule #39 (quoted filenames bypass the protected-path check) and #38 (remove the stale `agent-kit/` copy) before step 14, instead of leaving them under "Later" | Withdrawn | resolved 2026-10-20: no. The human put product work first; both stay under "Later" |

## Score checkpoints

Evidenced points come only from `_docs/rubric-evidence.md`; estimates are labelled.

| Checkpoint | Expected points | Basis |
|---|---|---|
| Baseline audit (2026-10-17) | 7 | Audited |
| After step 1 | 9 | Audited 2026-10-20 at `74e9cfc`: Testing 1 and CI/CD 1 confirmed |
| After step 2 | 10 | Audited 2026-10-20 at `74e9cfc`: Problem Description 2 confirmed |
| After steps 3-6 | 10 (ASSUMPTION) | Process and spec work only; no criterion expected to move, not re-audited |
| After step 15 | 12 | Tier A |
| After step 17 | 24 | Tier C |

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
