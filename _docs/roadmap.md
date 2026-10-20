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

| # | Step | Issues | Depends on | Done when | Status (2026-10-20) |
|---|---|---|---|---|---|
| 1 | Refresh the rubric evidence | (auditor skill) | none | `_docs/rubric-evidence.md` re-audited at current `main`; confirms or rejects Testing 1 and CI/CD 1 | done (2026-10-20 audit, 10/24 at `74e9cfc`) |
| 2 | README problem description | #13 | none | Auditor marks Problem Description MET (2) | done (auditor confirmed MET 2) |
| 3 | Push check plan-mode fix | #35 | none | #35 closed | done (`df72298`, QA PASS after the approval record; closed 2026-10-20; follow-up #42) |
| 4 | Remaining #15/#20 findings | #33 | none | #33 closed | deferred (2026-10-20, priority rule: tooling hardening; moved to "Later") |
| 5 | Approval-record hardening | #17, #18 | none | Both closed before the step 6 protected commits, or the human defers them | done (both closed 2026-10-20) |
| 6 | Spec review issues | #3, #4, #5, #6, #7, #8 | none | PM grooms all six together; one batched decision message to the human; each implemented as its own protected commit; all six closed | done (six protected commits `45f6fa6`..`fdc7b51`, all QA PASS, closed 2026-10-20; follow-up #41) |
| 7 | Stage 2: `_docs/architecture.md` (next) | #41, then a new issue | 6 | #41's spec commit landed; Stage 2 checklist PASS; #9's architecture rows ticked; Docker-capable environment named; #9 hosting decision closed as AWS (CloudFormation) | doing (#41 done: `1445ca5`, QA PASS, closed 2026-10-20; architecture issue not yet filed) |
| 8 | Stage 3: API contract | #23, then #27 | 7 | Both closed | todo |
| 9 | Frontend SPA shell | #34 | 8 (#23) | #34 closed (test count in its criteria updated to 35 at grooming) | todo |
| 10 | Stage 4: `_docs/testing.md` | new issue | 8 | Stage 4 checklist PASS; #9's testing rows ticked | todo |
| 11 | Stage 5: `_docs/tasks.md` | new issue | 10 | Stage 5 checklist PASS (no cycles; every story and criterion covered) | todo |
| 12 | Backlog issues from `tasks.md` | new issues | 11 | PM proposal approved by the human; each issue carries its story's acceptance criteria | todo |
| 13 | Stage 6: `_docs/plan-summary.md` | new issue | 11 | Stage 6 checklist PASS (all 12 criteria mapped) | todo |
| 14 | Plan review and phase change | new issue | 12, 13 | Review passed; human-approved `AGENTS.md` phase line committed | todo |
| 15 | Tier A build | #24 → #25 → #26, then step 12 issues | 14 | Auditor: Application 2, Testing 2 | blocked (phase line) |
| 16 | Docker-capable environment | #31 | 7 | Compose runs Postgres in the dev environment | todo (decision 2 resolved; human performs the change) |
| 17 | Tier B and C build | step 12 issues | 15, 16 | Auditor: all 12 criteria MET | todo |

Later, not scheduled (tooling and process; see the priority rule): #10, #16, #19, #29, #30, #33, #36, #37, #38, #39, #40, #42. #38 carries out the human's 2026-10-20 remove decision for #36; #36 can close when #38 does. #19 (ai-usage-report) is graded evidence; pick it up with the Tier C work.

#41 (spec fixes from the #3-#8 QA risks) opened step 7 and is closed. Inputs to the architecture issue: #41's Out-of-scope list, PM comment 6288008663, the status-model risks in 6289212246, and #9.

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
