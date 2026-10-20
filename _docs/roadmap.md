# VulnTriage roadmap

The order in which open work is done, and the checks used to tell whether the
project is on track. It sequences the work; it is not part of the build plan
that the plan review checks (`_docs/planning-process.md` Stages 1-6).

- Adopted: 2026-10-19, from a review of opencode's status analysis (Claude Code, claude-opus-5-5); see `_docs/ai-usage-log.md`.
- Goal: 24/24, built as Tier A → B → C milestones (human decision of 2026-10-17; tiers in `_docs/reviews/2026-10-16-final-rubric-impact.md` §5).
- Timing and scope trade-offs are the human's. "On track" here means steps are done in order and the audited score meets the checkpoint for the steps done.
- Source of truth for status: the GitHub tracker and `_docs/rubric-evidence.md`. The status column here is a snapshot taken at each check-in, not live state.

## Sequence

Status values: `todo`, `doing`, `done`, `blocked`. A step starts only when the steps it depends on are `done`.

| # | Step | Issues | Depends on | Done when | Status (2026-10-20) |
|---|---|---|---|---|---|
| 1 | Refresh the rubric evidence | (auditor skill) | none | `_docs/rubric-evidence.md` re-audited at current `main`; confirms or rejects Testing 1 and CI/CD 1 | done (2026-10-20 audit, 10/24 at `74e9cfc`) |
| 2 | README problem description | #13 | none | Auditor marks Problem Description MET (2) | done (auditor confirmed MET 2) |
| 3 | Push check plan-mode fix | #35 | none | #35 closed | todo (groomed 2026-10-20) |
| 4 | Remaining #15/#20 findings | #33 | none | #33 closed | todo (groomed 2026-10-20) |
| 5 | Approval-record hardening | #17, #18 | none | Both closed before the step 6 protected commits, or the human defers them | todo |
| 6 | Spec review issues | #3, #4, #5, #6, #7, #8 | none | PM grooms all six together; one batched decision message to the human; each implemented as its own protected commit; all six closed | doing (all six groomed 2026-10-20; batched decision pending) |
| 7 | Stage 2: `_docs/architecture.md` | new issue | 6 | Stage 2 checklist PASS; #9's architecture rows ticked; Docker-capable environment named; #9 hosting decision closed as AWS (CloudFormation) | todo |
| 8 | Stage 3: API contract | #23, then #27 | 7 | Both closed | todo |
| 9 | Frontend SPA shell | #34 | 8 (#23) | #34 closed (test count in its criteria updated to 35 at grooming) | todo |
| 10 | Stage 4: `_docs/testing.md` | new issue | 8 | Stage 4 checklist PASS; #9's testing rows ticked | todo |
| 11 | Stage 5: `_docs/tasks.md` | new issue | 10 | Stage 5 checklist PASS (no cycles; every story and criterion covered) | todo |
| 12 | Backlog issues from `tasks.md` | new issues | 11 | PM proposal approved by the human; each issue carries its story's acceptance criteria | todo |
| 13 | Stage 6: `_docs/plan-summary.md` | new issue | 11 | Stage 6 checklist PASS (all 12 criteria mapped) | todo |
| 14 | Plan review and phase change | new issue | 12, 13 | Review passed; human-approved `AGENTS.md` phase line committed | todo |
| 15 | Tier A build | #24 → #25 → #26, then step 12 issues | 14 | Auditor: Application 2, Testing 2 | blocked (phase line) |
| 16 | Docker-capable environment | #31 | 7 | Compose runs Postgres in the dev environment | blocked (see decision 2) |
| 17 | Tier B and C build | step 12 issues | 15, 16 | Auditor: all 12 criteria MET | todo |

Later, not scheduled: #10, #16, #19, #29, #30.

## Open decisions

| # | Decision | Recommendation | Status |
|---|---|---|---|
| 1 | Groom #3-#8 together and answer one batched decision message, instead of one issue at a time | Yes | open (grooming done 2026-10-20; batched answer pending) |
| 2 | Drop #31's "blocked by #26" dependency, since the environment does not need persistence code | Yes; move before Tier B work starts, decide which environment in step 7 | open |
| 3 | Promote #17/#18 ahead of the spec commits | Yes, unless the human prefers to defer | open |

## Score checkpoints

Evidenced points come only from `_docs/rubric-evidence.md`; estimates are labelled.

| Checkpoint | Expected points | Basis |
|---|---|---|
| Last audit (2026-10-17) | 7 | Audited |
| After step 1 | 9 (ASSUMPTION) | Testing 1 (35 unit tests) and CI/CD 1 (`verify.yml` runs them on every PR), if the auditor accepts them |
| After step 2 | 10 (ASSUMPTION) | Problem Description 2: pass mark on paper |
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
- The audited score is below the checkpoint for the steps already done.
- An open decision blocks the next step for more than one session.

## Check-in log

| Date | Steps done since last check-in | Audited score | On track? | Notes |
|---|---|---|---|---|
| 2026-10-19 | none (roadmap adopted) | 7 (2026-10-17 audit) | yes | Baseline |
| 2026-10-20 | step 2 implementation (#13) | 7 (not re-audited) | yes | #13 QA PASS at `e46fadf`; step 2 started ahead of step 1 at the human's request and stays `doing` until the auditor confirms Problem Description 2 |
| 2026-10-20 | steps 1 and 2; step 6 grooming; #35/#33 grooming | 10 (2026-10-20 audit) | yes | Auditor re-audited at `74e9cfc` (commit `639b9a9`) and confirmed Testing 1, CI/CD 1 and Problem Description 2. All six spec-review issues are groomed; the batched decision is still open, so step 6 stays `doing`. #35 and #33 are groomed; PM filed follow-ups #36 and #37. |
