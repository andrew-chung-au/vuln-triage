# AI usage log

Append-only record of AI-assisted work, kept for rubric criteria 2
(AI-assisted development workflow) and 13 (security, audit, and DevOps
hardening). Append one entry per task; facts only — never record a review
or verification that did not happen. Where the prompt, model, or
verification is not recorded in the repo, write literally `not recorded`
(for prompt/model) or `none` (for verification/human review) rather than
guessing. Key prompts that define a role, stage, or task are saved verbatim
in `_docs/prompts/` and linked from the entry.

## Entry template

Copy this template for each new entry:

- date:
- task/issue:
- agent role:
- model:
- prompt or instruction given (or link to a file in `_docs/prompts/`):
- files changed:
- verification (tests run, reviewer verdict):
- human review (what I checked or corrected, or `none`):

## Entries

### 2026-10-12 — project setup (commit f2735e9)

- date: 2026-10-12
- task/issue: project setup — instructions, settings, hooks, OpenCode layer
- agent role: not recorded
- model: not recorded
- prompt or instruction given (or link to a file in `_docs/prompts/`): not recorded
- files changed: `AGENTS.md`, `agent-kit.conf`, `Makefile`, `opencode.json`, `.opencode/agents/pm.md`, `.opencode/agents/qa-engineer.md`, `.opencode/agents/software-engineer.md`, `README.md`, `.gitignore`, `.githooks/` (verified via `git show f2735e9 --stat`)
- verification (tests run, reviewer verdict): none
- human review (what I checked or corrected, or `none`): none

### 2026-10-12 — project brief Stage 0 (commit 269d30d)

- date: 2026-10-12
- task/issue: add project brief for VulnTriage (Stage 0)
- agent role: not recorded
- model: not recorded
- prompt or instruction given (or link to a file in `_docs/prompts/`): not recorded
- files changed: `_docs/project-brief.md` (verified via `git show 269d30d --stat`)
- verification (tests run, reviewer verdict): none
- human review (what I checked or corrected, or `none`): none

### 2026-10-12 — independent plan review (commit c631603)

- date: 2026-10-12
- task/issue: independent plan review (verdict FAIL: plan docs missing)
- agent role: not recorded
- model: not recorded
- prompt or instruction given (or link to a file in `_docs/prompts/`): not recorded
- files changed: `_docs/plan-review.md` (verified via `git show c631603 --stat`)
- verification (tests run, reviewer verdict): none
- human review (what I checked or corrected, or `none`): none

### 2026-10-12 — final project rubric (commit 235b9f4)

- date: 2026-10-12
- task/issue: add final project rubric (planning reference, 14 criteria)
- agent role: not recorded
- model: not recorded
- prompt or instruction given (or link to a file in `_docs/prompts/`): not recorded
- files changed: `_docs/rubric.md` (verified via `git show 235b9f4 --stat`)
- verification (tests run, reviewer verdict): none
- human review (what I checked or corrected, or `none`): none

### 2026-10-12 — planning process stages 0-6 (commit 88858aa)

- date: 2026-10-12
- task/issue: add VulnTriage planning process (stages 0-6)
- agent role: not recorded
- model: not recorded
- prompt or instruction given (or link to a file in `_docs/prompts/`): not recorded
- files changed: `_docs/planning-process.md` (verified via `git show 88858aa --stat`)
- verification (tests run, reviewer verdict): none
- human review (what I checked or corrected, or `none`): none

### 2026-10-12 — product spec Stage 1 (commit dafd91e)

- date: 2026-10-12
- task/issue: add VulnTriage product spec (Stage 1: users, stories, non-goals, edge cases)
- agent role: not recorded
- model: not recorded
- prompt or instruction given (or link to a file in `_docs/prompts/`): not recorded
- files changed: `_docs/specs.md` (verified via `git show dafd91e --stat`)
- verification (tests run, reviewer verdict): none
- human review (what I checked or corrected, or `none`): none

### 2026-10-12 — README planning-doc links Stage 1 (commit 59bb33a)

- date: 2026-10-12
- task/issue: link planning docs from README (Stage 1)
- agent role: not recorded
- model: not recorded
- prompt or instruction given (or link to a file in `_docs/prompts/`): not recorded
- files changed: `README.md` (verified via `git show 59bb33a --stat`)
- verification (tests run, reviewer verdict): none
- human review (what I checked or corrected, or `none`): none

### 2026-10-12 — implement groomed issue #1 (evidence logging + rubric evidence auditor)

- date: 2026-10-12
- task/issue: implement groomed issue #1 per `.scratch/issue-1-groomed.md` with human overrides (A) prompts README notes no prompts yet, (B) out-of-scope unlinked
- agent role: Software Engineer
- model: opencode/muse-spark-1.3-contributor-free
- prompt or instruction given (or link to a file in `_docs/prompts/`): orchestrator instruction to implement `.scratch/issue-1-groomed.md` (12 criteria) with overrides; no key prompt file in `_docs/prompts/` (only `README.md`, zero entries)
- files changed: `_docs/ai-usage-log.md`, `_docs/rubric-evidence.md`, `_docs/ai-usage-report.md`, `_docs/prompts/README.md`, `README.md` (link lines only), `AGENTS.md` (two rule sentences only, uncommitted pending approval), `.opencode/agents/pm.md`, `.opencode/agents/software-engineer.md`, `.opencode/agents/qa-engineer.md` (DoD line only, uncommitted pending approval), `.opencode/agents/rubric-auditor.md` (new, uncommitted pending approval), `.agents/skills/update-rubric-evidence/SKILL.md` (new)
- verification (tests run, reviewer verdict): `make verify` PASS WITH WARNINGS (no TEST_CMD as no code exists; whitespace PASS; no test files changed); `.scratch/check_issue1.py` run — all substantive checks pass (two check-script strictness notes: C8 counts 8 TODOs including intro line; C11 lists untracked dirs `.agents/` and `_docs/prompts/` instead of expanded files)
- human review (what I checked or corrected, or `none`): none

### 2026-10-13 — update token permissions and post issue #1 comments

- date: 2026-10-13
- task/issue: apply human-approved protected changes for new GitHub token permissions; post PM/Engineer/QA comments on issue #1
- agent role: Orchestrator
- model: opencode/muse-spark-1.3-contributor-free
- prompt or instruction given (or link to a file in `_docs/prompts/`): human instruction in-session (new token: read-only code, read/write issues; three AGENTS.md/opencode.json edits enumerated verbatim; post the four drafted comments; ask before closing #1); no key prompt file in `_docs/prompts/`
- files changed: `AGENTS.md` (Environment line rewritten; untrusted-issue-text rule added), `opencode.json` (gh issue comment allow; close/create/edit ask; delete deny; api ask) — committed as c22a657 with HUMAN_APPROVED=1 after human approval of the exact diff
- verification (tests run, reviewer verdict): `git diff --check` clean; exact diff shown to human before commit; four comments posted (ids 6136675116, 6136679351, 6136682287, 6136689656)
- human review (what I checked or corrected, or `none`): human authored and approved the changes; flagged pre-existing working-tree extras in the same diff (one-command bullet in AGENTS.md, tool-added opencode.json allow rules) as included-but-not-new

### 2026-10-16 — install Claude Code layer alongside OpenCode

- date: 2026-10-16
- task/issue: install the agent kit's Claude Code layer (`_docs/agent-kit/claude-code/START.md`, steps 2-5) without clashing with the OpenCode layer; Claude Code is to supervise/review OpenCode's work
- agent role: Orchestrator (Claude Code main session)
- model: claude-opus-5-5
- prompt or instruction given (or link to a file in `_docs/prompts/`): human instruction in-session ("help me set up the claude code layer. make sure it does not clash with opencode. I will use claude code to supervise/review the work opencode has done."); no key prompt file in `_docs/prompts/`
- files changed: `CLAUDE.md` (new, from template), `.claude/agents/pm.md`, `.claude/agents/software-engineer.md`, `.claude/agents/qa-engineer.md` (new, from kit plus the project's ai-usage-log DoD line), `.claude/agents/rubric-auditor.md` (new, port of `.opencode/agents/rubric-auditor.md`), `.claude/settings.json` (new, kit settings; ask list matched to PROTECTED plus Makefile; gh issue view/list allowed; gh issue delete denied), `agent-kit.conf` (PROTECTED adds `CLAUDE.md`, `.claude/*`), `opencode.json` (edit ask for `CLAUDE.md`, `.claude/*`; also commits the human's pending `gh issue create*` ask→allow change), `_session-summaries/planning-2026-10-16-claude-code-layer.md`
- verification (tests run, reviewer verdict): `make verify` PASS WITH WARNINGS (no TEST_CMD: no code exists; whitespace PASS; no test files changed). START.md step 6 checks (`/agents`, `/hooks`, `/permissions`, guard test) not yet run: they need a Claude Code restart
- human review (what I checked or corrected, or `none`): human approved the protected edits to `agent-kit.conf` and `opencode.json` and chose to include the pending opencode.json change in this commit

### 2026-10-16 — independent plan review of Stage 1 (at 27d4760)

- date: 2026-10-16
- task/issue: independent review of the planning documents written so far (brief, rubric, planning process, `_docs/specs.md`); Stages 2-6 not yet written
- agent role: Reviewer (Claude Code, independent of the OpenCode planning agent)
- model: claude-opus-5-5
- prompt or instruction given (or link to a file in `_docs/prompts/`): human-pasted reviewer prompt in-session (find errors, gaps, scope, checkability, unmarked external API facts, feasibility, security; write only the review and this log entry); not saved to `_docs/prompts/` because the instruction limited the files written (raised as a question in the review)
- files changed: `_docs/reviews/2026-10-16-plan-review.md` (new), `_docs/ai-usage-log.md` (this entry)
- verification (tests run, reviewer verdict): reviewer verdict FAIL (2 High, 10 Medium, 6 Low findings; 6 questions for the human); `make verify` run before commit
- human review (what I checked or corrected, or `none`): none

### 2026-10-16 — turn plan review findings into GitHub issues

- date: 2026-10-16
- task/issue: convert `_docs/reviews/2026-10-16-plan-review.md` (ba39c5c) into GitHub issues #3-#9; record the human's decisions on the review questions
- agent role: Reviewer (Claude Code)
- model: claude-opus-5-5
- prompt or instruction given (or link to a file in `_docs/prompts/`): human-pasted instruction in-session (one issue per High finding, Medium/Low grouped by topic in at most 5 issues, a carry-forward issue for later stages, task-template bodies, VERIFY: on feed assumptions, show titles before creating), then approval with changes (coverage check, Depends-on lines, recorded decisions); not saved as a key prompt (task instruction, not a role or stage definition)
- files changed: `_docs/plan-review.md` renamed to `_docs/plan-review-2026-10-12-superseded.md` with a superseded first line (human decision); `_docs/prompts/reviewer-plan-review.md` (new, Reviewer prompt verbatim, human decision); `_docs/prompts/README.md` (index row); `_docs/ai-usage-log.md` (this entry)
- GitHub issues created: #3 finding 1 (fixed version), #4 finding 2 (CVE aliases), #5 findings 4/7/8/9 (feeds and ingestion), #6 findings 3/10/13/16/17 (status and audit; depends on #3), #7 findings 5/6/15 (notifications; decisions on issue destination and issue-close sync), #8 findings 11/14 (security boundaries; depends on #7), #9 carry into later stages (findings 1, 2, 4, 11, 12, 15, 18 by stage; cloud hosting decision open). Coverage checked: findings 1-18 each appear in at least one issue; split findings (1, 2, 4, 11, 15) say which part each issue handles
- human decisions recorded: specs.md is a draft until the review issues are resolved (in #3); cloud hosting target left open (in #9)
- verification (tests run, reviewer verdict): issue numbers checked against each `gh issue create` result before cross-references were written; `make verify` run before commit; issue links point at ba39c5c, which resolve only after the human pushes
- human review (what I checked or corrected, or `none`): human approved the issue titles and grouping and asked for the coverage check, Depends-on lines and recorded decisions before creation

### 2026-10-16 — QA re-check of issue #1 at ba39c5c (fresh PASS)

- date: 2026-10-16
- task/issue: issue #1 — fresh full QA check at current HEAD ba39c5c (prior PASS at 0b2a18f was stale after e496aa5, c22a657, 3f6a919, 27d4760, ba39c5c)
- agent role: QA Engineer (subagent; entry appended by Orchestrator per the write-only-.scratch/ role limit)
- model: opencode/muse-spark-1.3-contributor-free
- prompt or instruction given (or link to a file in `_docs/prompts/`): orchestrator instruction to perform a fresh full QA check at current HEAD per `_docs/agent-kit/team/qa-engineer.md`; no key prompt file in `_docs/prompts/`
- files changed: none (QA changed nothing; `.scratch/` left empty)
- verification (tests run, reviewer verdict): `make verify` PASS WITH WARNINGS (no TEST_CMD: planning phase, no code exists; whitespace PASS; no test files changed); verdict QA PASS — all 11 criteria PASS at ba39c5c; E2E not applicable (`none` in AGENTS.md, docs-only change); `make assert-clean` PASS and HEAD unmoved (ba39c5c) confirmed by Orchestrator; verdict posted as issue comment 6217664490
- human review (what I checked or corrected, or `none`): none

### 2026-10-16 — PM files follow-up issue #2 (role log-entry contradiction)

- date: 2026-10-16
- task/issue: file approved follow-up for the QA-flagged risk that PM/QA role files contradict themselves (write-only-.scratch/ vs append to `_docs/ai-usage-log.md`); the 3 earlier-drafted follow-ups (prompts index, first audit, report content) stay deferred per human decision
- agent role: PM (Product Manager subagent; entry appended by Orchestrator per the write-only-.scratch/ role limit)
- model: opencode/muse-spark-1.3-contributor-free
- prompt or instruction given (or link to a file in `_docs/prompts/`): orchestrator instruction citing the human's decision-point approval to file exactly one follow-up; no key prompt file in `_docs/prompts/`
- files changed: none in working tree (body drafted in `.scratch/followup-pm-qa-log-body.md`, removed by `make clean-scratch`)
- verification (tests run, reviewer verdict): none (no code changed; new issue #2 returned with URL https://github.com/andrew-chung-au/vuln-triage/issues/2)
- human review (what I checked or corrected, or `none`): human approved filing this follow-up and deferring the other three at the issue #1 decision point

### 2026-10-16 — PM grooms issue #2 (orchestrator-appends rule)

- date: 2026-10-16
- task/issue: issue #2 — groom to task template (Goal + 7 checkable criteria + Out of scope + Constraints); recommend single rule (roles write only to `.scratch/`, orchestrator appends log entry after assert-clean)
- agent role: PM (Product Manager subagent; entry appended by Orchestrator per the write-only-.scratch/ role limit)
- model: opencode/muse-spark-1.3-contributor-free
- prompt or instruction given (or link to a file in `_docs/prompts/`): orchestrator instruction to groom #2 per `_docs/agent-kit/team/pm.md` using `_docs/agent-kit/templates/task-template.md`; no key prompt file in `_docs/prompts/`
- files changed: none in working tree (draft in `.scratch/issue-2-groomed.md`, later replaced by `.scratch/issue-2-groomed-v2.md`; both removed by `make clean-scratch`)
- verification (tests run, reviewer verdict): none (no code changed)
- human review (what I checked or corrected, or `none`): human confirmed the orchestrator-appends rule, chose keep-#2-PM/QA-only plus follow-up, and approved updating #2 with the groomed text

### 2026-10-16 — Engineer implements issue #2 (commit 2dcc89d)

- date: 2026-10-16
- task/issue: issue #2 — replace contradicting log line with orchestrator-appends rule in 4 role files
- agent role: Software Engineer (subagent; entry appended by Orchestrator per the write-only-.scratch/ role limit)
- model: opencode/muse-spark-1.3-contributor-free
- prompt or instruction given (or link to a file in `_docs/prompts/`): orchestrator instruction to implement groomed #2, leave protected edits uncommitted, run Verify, and return the diff; no key prompt file in `_docs/prompts/`
- files changed: `.opencode/agents/pm.md`, `.opencode/agents/qa-engineer.md`, `.claude/agents/pm.md`, `.claude/agents/qa-engineer.md` (one-line swap each: 4 insertions, 4 deletions; committed as 2dcc89d after human approval with HUMAN_APPROVED=1)
- verification (tests run, reviewer verdict): `make verify` PASS WITH WARNINGS (no TEST_CMD: planning phase, no code exists; whitespace PASS; no test files changed); `git diff --check` clean; report posted as issue comment 6218874639
- human review (what I checked or corrected, or `none`): human approved this exact diff before the protected commit

### 2026-10-16 — QA checks issue #2 at 2dcc89d (PASS)

- date: 2026-10-16
- task/issue: issue #2 — full QA check of all 7 criteria at commit 2dcc89d
- agent role: QA Engineer (subagent; entry appended by Orchestrator per the write-only-.scratch/ role limit)
- model: opencode/muse-spark-1.3-contributor-free
- prompt or instruction given (or link to a file in `_docs/prompts/`): orchestrator instruction to check #2 per `_docs/agent-kit/team/qa-engineer.md` at commit 2dcc89d; no key prompt file in `_docs/prompts/`
- files changed: none (QA changed nothing; `.scratch/` check script and output only, removed by `make clean-scratch`)
- verification (tests run, reviewer verdict): `make verify` PASS WITH WARNINGS (no TEST_CMD: planning phase; whitespace PASS; no test files changed); `make assert-clean` PASS at 2dcc89d; verdict QA PASS — all 7 criteria PASS; E2E not run (`none` in AGENTS.md, no user-facing behaviour); verdict posted as issue comment 6218959705
- human review (what I checked or corrected, or `none`): none

### 2026-10-16 — Orchestrator close-out of issue #2 (follow-up #10, edit, commit, close)

- date: 2026-10-16
- task/issue: issue #2 close-out — file approved follow-up #10, update #2 body to groomed text, commit protected diff, close #2
- agent role: Orchestrator
- model: opencode/muse-spark-1.3-contributor-free
- prompt or instruction given (or link to a file in `_docs/prompts/`): user instruction "work on the next issue and follow process.md"; no key prompt file in `_docs/prompts/`
- files changed: `_docs/ai-usage-log.md` (these entries); `_session-summaries/issue-002-qa-log-rule.md` (new); GitHub: created issue #10 (engineer/auditor log contradiction), edited #2 body to groomed text, posted PM/Engineer/QA relay comments, closed #2
- verification (tests run, reviewer verdict): `make assert-clean` PASS and HEAD unmoved at 2dcc89d confirmed after QA; QA verdict QA PASS at 2dcc89d
- human review (what I checked or corrected, or `none`): human approved the groomed-text edit, the protected commit, and closing #2

### 2026-10-16 — Add `make issue-dump` target and protect the Makefile (commits f999cd6, fc29661)

- date: 2026-10-16
- task/issue: add a Makefile target so fetching a long issue needs no shell redirect or script; add the matching Commands line to `AGENTS.md`; add `Makefile` to the PROTECTED list
- agent role: Orchestrator
- model: opencode/space-bunny-free
- prompt or instruction given (or link to a file in `_docs/prompts/`): user instruction to add the target with the supplied Make recipe and the `Fetch an issue` Commands line, to show both diffs before committing, and to add `Makefile` to PROTECTED; no key prompt file in `_docs/prompts/`
- files changed: `Makefile` (new `# --- Project targets (not from the kit) ---` section with `ISSUE_DIGITS_LEFT` validation and the `issue-dump` target; 13 insertions, commit f999cd6); `AGENTS.md` (`Fetch an issue` Commands line; 1 insertion, commit f999cd6); `agent-kit.conf` (`Makefile` added to PROTECTED; 1 insertion, commit fc29661)
- verification (tests run, reviewer verdict): `make verify` PASS WITH WARNINGS (no TEST_CMD: planning phase, no code exists; whitespace PASS; no test files changed) over 14 files / 368 insertions vs origin/main; `make issue-dump` with no N exits non-zero with `Usage: make issue-dump N=<issue number>`; `make issue-dump N=11a` exits non-zero with `N must be an issue number`; `make issue-dump N=11` wrote `.scratch/issue-11.json` (10910 bytes) containing body, title, state, labels and comments; `make help` lists `issue-dump`; `git diff --check` clean; recipe lines confirmed as tabs
- human review (what I checked or corrected, or `none`): human approved the Makefile and `AGENTS.md` diffs and the `agent-kit.conf` PROTECTED addition, each committed with `HUMAN_APPROVED=1`; human corrected two facts — `Makefile` was not protected before this entry, and the Makefile had no project section until this change created one

### 2026-10-16 — PM grooms issue #11 (final rubric impact)

- date: 2026-10-16
- task/issue: issue #11 — groom to task template; confront the missing verbatim criteria text; fix stale open-issue range
- agent role: PM (Product Manager subagent; entry appended by Orchestrator per the write-only-.scratch/ role limit)
- model: opencode/space-bunny-free
- prompt or instruction given (or link to a file in `_docs/prompts/`): orchestrator instruction to groom #11 per `_docs/agent-kit/team/pm.md`, with instructions to confront the placeholder text and the stale issue range; no key prompt file in `_docs/prompts/`
- files changed: none in working tree (draft in `.scratch/issue-11-groomed.md`)
- verification (tests run, reviewer verdict): none (no code changed); PM read all five planning documents named in the issue; PM confirmed `_docs/rubric.md` is not in `agent-kit.conf` PROTECTED and that #2 is closed and #10 is open
- human review (what I checked or corrected, or `none`): human supplied the full final Criteria text into the issue's Source section, answering the PM's blocker question; human corrected the PM's read of the source by updating the issue rather than the PM re-grooming it

### 2026-10-16 — Engineer implements issue #11 (commits 0604233, 2cfdf95)

- date: 2026-10-16
- task/issue: issue #11 — replace `_docs/rubric.md` with the final 12 criteria verbatim; write the impact report at `_docs/reviews/2026-10-16-final-rubric-impact.md`
- agent role: Software Engineer (subagent; entry appended by Orchestrator per the write-only-.scratch/ role limit)
- model: opencode/space-bunny-free
- prompt or instruction given (or link to a file in `_docs/prompts/`): orchestrator instruction to implement #11 from the filed body as amended by the PM comment, with an explicit state check that the interrupted prior run had committed nothing; no key prompt file in `_docs/prompts/`
- files changed: `_docs/rubric.md` (78 insertions, 36 deletions, commit 0604233); `_docs/reviews/2026-10-16-final-rubric-impact.md` (570 insertions, new, commit 2cfdf95); no PROTECTED path touched
- verification (tests run, reviewer verdict): `make verify` PASS WITH WARNINGS (no TEST_CMD: planning phase, no code exists; whitespace PASS; no test files changed); `git diff --check` clean; Engineer reported a scripted byte comparison of `_docs/rubric.md` line 2 onward against the criteria text in the issue Source section; counted 12 criteria, max points summing 24, "You need 10 points to pass". Not yet QA'd
- human review (what I checked or corrected, or `none`): human paused the session before QA, having uncommitted their own `AGENTS.md` and `opencode.json` changes; human also stopped the `.scratch/` script approach for GitHub issue data after the PM wrote `dump_issue11.py` and `extract_source.py` in place of `gh --json`/`--jq`, which was a process deviation caused by the orchestrator's role prompts

### 2026-10-17 — Orchestrator resumes issue #11: Engineer handover comment, model record

- date: 2026-10-17
- task/issue: issue #11 — pick up after the pause; post the Engineer handover; record which tool and model built #11
- agent role: Orchestrator (Claude Code main session)
- model: claude-opus-5-5 (Claude Code)
- prompt or instruction given (or link to a file in `_docs/prompts/`): human handover prompt (read the issue, latest summary, git state, then stop) and human instruction to run step 1, name the tool/model that built #11, record the model change, run QA in a different tool, and not close #11; no key prompt file in `_docs/prompts/`
- files changed: `_docs/ai-usage-log.md` (these entries); GitHub: posted Engineer handover comment 6227197431 on #11
- tool and model history for #11 (as far as the record shows): all #11 work recorded was done in OpenCode, none in Claude Code. The human states the model changed during #11 from Muse Spark 1.3 (`opencode/muse-spark-1.3-contributor-free`) to Space Bunny (`opencode/space-bunny-free`). Filing #11: not recorded. PM grooming: Space Bunny. First Engineer launch (interrupted, no commits): not recorded. Engineer commits 0604233 and 2cfdf95: Space Bunny. Orchestrator entries and summary (ad04f59): not recorded. Muse Spark 1.3's part in #11: not recorded. The human's commit c8dea47 pinned Muse Spark 1.3 in `opencode.json` after the Engineer work
- verification (tests run, reviewer verdict): `make assert-clean` PASS at c8dea47 before QA; `make verify` PASS WITH WARNINGS at c8dea47 (no TEST_CMD: planning phase, no code exists; whitespace PASS; no test files changed)
- human review (what I checked or corrected, or `none`): human confirmed the Orchestrator role for #11 and required QA in a tool other than the one that built it (OpenCode built it, so QA ran in Claude Code)

### 2026-10-17 — QA checks issue #11 at c8dea47 (PASS)

- date: 2026-10-17
- task/issue: issue #11 — full QA check against the filed body as amended by PM comment 6226692732, at commit c8dea47 (Engineer commits 0604233, 2cfdf95)
- agent role: QA Engineer (Claude Code subagent; entry appended by Orchestrator per the write-only-.scratch/ role limit)
- model: claude-opus-5-5 (Claude Code; the qa-engineer agent sets no model, so it inherits the main session's)
- prompt or instruction given (or link to a file in `_docs/prompts/`): orchestrator instruction to check #11 per `_docs/agent-kit/team/qa-engineer.md` at c8dea47, carrying the AGENTS.md rule on GitHub issue data; no key prompt file in `_docs/prompts/`
- files changed: none (QA wrote only to `.scratch/`: `qa11_check.py`, `qa-11-comment.md`)
- verification (tests run, reviewer verdict): verdict QA PASS, all criteria PASS, posted as issue comment 6227226075; QA ran `make verify` (PASS WITH WARNINGS, no TEST_CMD) and one `.scratch/` analysis script (byte comparison of `_docs/rubric.md` against the issue Source section and count checks). Orchestrator then ran `make assert-clean` PASS and confirmed HEAD unmoved at c8dea47. QA reported 8 risks outside the criteria (in the comment), none changing the verdict
- human review (what I checked or corrected, or `none`): none yet; human to read the report and record decisions on the two Decision needed items before #11 is closed

### 2026-10-17 — Engineer corrects #11 report for QA risks (commit ed05530)

- date: 2026-10-17
- task/issue: issue #11 follow-up — fix the six QA risks in `_docs/reviews/2026-10-16-final-rubric-impact.md` (US-12 before/after, E6 row, brief line number, #8 criteria count, §1 Totals deployment claim, GitHub Actions Docker VERIFY: tag, §9 counts) and add the source URL and a final newline to `_docs/rubric.md`
- agent role: Software Engineer (Claude Code subagent; entry appended by Orchestrator)
- model: claude-opus-5-5 (Claude Code). Ran in Claude Code, not OpenCode, because OpenCode was unavailable; the human asked for this
- prompt or instruction given (or link to a file in `_docs/prompts/`): human instruction listing the corrections, relayed by the Orchestrator; source URL supplied by the human (https://github.com/DataTalksClub/ai-dev-tools-zoomcamp/blob/main/project/README.md); no key prompt file in `_docs/prompts/`
- files changed: `_docs/reviews/2026-10-16-final-rubric-impact.md`, `_docs/rubric.md` (43 insertions, 22 deletions, commit ed05530); Engineer comment 6227407227 on #11
- verification (tests run, reviewer verdict): `make verify` PASS WITH WARNINGS (no TEST_CMD: planning phase, no code exists; whitespace PASS; no test files changed); Orchestrator `make assert-clean` PASS at ed05530 before QA
- human review (what I checked or corrected, or `none`): human supplied the source URL; the finalised date 2026-10-17 on rubric line 1 is left for the human to check against the live page

### 2026-10-17 — QA targeted re-check of #11 corrections at ed05530 (PASS)

- date: 2026-10-17
- task/issue: issue #11 — targeted re-check of the seven correction points only (six report points, rubric line 1 and final newline, scope)
- agent role: QA Engineer (fresh Claude Code subagent, separate from the Engineer's context; entry appended by Orchestrator per the write-only-.scratch/ role limit)
- model: claude-opus-5-5 (Claude Code). Ran in Claude Code, not OpenCode, because OpenCode was unavailable; the human asked for this. Engineer and QA ran in the same tool and model this time, as separate subagents
- prompt or instruction given (or link to a file in `_docs/prompts/`): orchestrator instruction to re-check the listed points against the files and `gh`, not the Engineer's comment; no key prompt file in `_docs/prompts/`
- files changed: none (QA wrote only to `.scratch/`: `qa11_recheck.py`, `qa11-recheck-comment.md`)
- verification (tests run, reviewer verdict): verdict QA PASS, all seven points PASS, posted as comment 6227431094; QA ran `make verify` (PASS WITH WARNINGS, no TEST_CMD) and one `.scratch/` script (byte comparison of the US-12 BEFORE block against `_docs/specs.md` lines 90-96 and of rubric lines 2 onward against e0a2470). Orchestrator then ran `make assert-clean` PASS, HEAD unmoved at ed05530. QA reported 4 risks outside these points, none changing the verdict
- human review (what I checked or corrected, or `none`): none yet

### 2026-10-17 — Orchestrator relays #11 decisions and applies brief change (commit 111b001)

- date: 2026-10-17
- task/issue: issue #11 decision point — post the human's decisions; apply the approved `_docs/project-brief.md` change from report §7.1
- agent role: Orchestrator (Claude Code main session)
- model: claude-opus-5-5 (Claude Code)
- prompt or instruction given (or link to a file in `_docs/prompts/`): human decisions of 2026-10-17 (target 24/24 built as Tier A/B/C milestones; all no-longer-scored items kept; scoring path first, then LLM brief, MCP server and n8n; US-12 keeps all three acceptance criteria) and human approval of §7.1 1b plus a CI/CD sentence of the human's wording; no key prompt file in `_docs/prompts/`
- files changed: `_docs/project-brief.md` (workflow step 8 "Watch and respond"; Fixed stack CI/CD item expanded to PR tests, auto deploy to dev, manual promotion of the same image to production; 7 insertions, 2 deletions, commit 111b001 with HUMAN_APPROVED=1); GitHub: posted the human's decisions verbatim as relayed Orchestrator comment 6228520087 on #11
- verification (tests run, reviewer verdict): `git diff --check` clean; final diff shown to the human
- human review (what I checked or corrected, or `none`): human rejected §7.1 1a (MCP server out of the MVP), approved 1b as written, and supplied the CI/CD sentence; human chose to apply all §7 changes before cleanup and closing #11

### 2026-10-17 — Orchestrator applies approved spec and brief changes (commits 701951d, 16e1ec0, b8792b3)

- date: 2026-10-17
- task/issue: issue #11 decision point — apply the approved `_docs/specs.md` changes from report §7.2 and a further brief change; relay the human's hosting decision to #9
- agent role: Orchestrator (Claude Code main session)
- model: claude-opus-5-5 (Claude Code)
- prompt or instruction given (or link to a file in `_docs/prompts/`): human decisions on §7.2 (reject 2a; accept US-13 and US-14; replace US-15 with the human's text; accept E6 naming Grafana), human edits (Grafana in US-13; US-15 via pull request, CI deploys to dev; open question 5 on the responder's credential and merge; shorten "fixes it with a test"), human's observability-stack sentence for the brief, and the human's hosting decision text for #9; no key prompt file in `_docs/prompts/`
- files changed: `_docs/specs.md` (US-13, US-14, US-15, edge case E6, open questions 4 and 5; 32 insertions, commit 701951d; one-line US-15 follow-up, commit 16e1ec0); `_docs/project-brief.md` (Fixed stack adds OpenTelemetry Collector, Prometheus, Loki, Tempo and Grafana; 3 insertions, 1 deletion, commit b8792b3); all three commits with HUMAN_APPROVED=1. GitHub: posted the human's hosting decision verbatim as relayed Orchestrator comment 6229681999 on #9. `opencode.json` (human's own uncommitted change) left out of all commits at the human's instruction
- verification (tests run, reviewer verdict): `git diff --check` clean before each commit; final diffs shown to the human before each commit (spec diff shown before the last two human edits, which were applied as instructed)
- human review (what I checked or corrected, or `none`): human rejected §7.2 2a (US-12 stays with all three acceptance clauses), rewrote US-15, named Grafana, added open question 5; Orchestrator numbered the US-14 window question 4 because question 3 already existed

### 2026-10-17 — AGENTS.md Layout and "Where to read more" (commit 4075318); issue #12 filed

- date: 2026-10-17
- task/issue: issue #11 decision point — apply report §7.0 to `AGENTS.md`; file the follow-up issue for `_docs/agent-team.md`
- agent role: Orchestrator (Claude Code main session)
- model: claude-opus-5-5 (Claude Code)
- prompt or instruction given (or link to a file in `_docs/prompts/`): human chose the Orchestrator's revised version of §7.0 (stale Layout fixed, Claude Code layer named, spec and brief added, `_docs/agent-team.md` left out until written) with the human's "when to read" wording for the spec, process and procedures entries; human asked for an issue to write `_docs/agent-team.md`; no key prompt file in `_docs/prompts/`
- files changed: `AGENTS.md` (Layout line updated; "Where to read more" list added; 13 insertions, 1 deletion; drafted by the Orchestrator, diff shown to the human, committed by the human as 4075318 with HUMAN_APPROVED=1). GitHub: filed issue #12 (Write `_docs/agent-team.md` for the Agent Team Specification criterion), not yet groomed by the PM
- verification (tests run, reviewer verdict): every path in the list checked to exist with `ls` before proposing; final diff shown to the human before commit
- human review (what I checked or corrected, or `none`): human chose option (a) with edits and ran the commit; the same-tool QA exception in #12's body is the Orchestrator's wording, flagged to the human for correction

### 2026-10-17 — Planning process and README updated for the final rubric (§7.3)

- date: 2026-10-17
- task/issue: issue #11 decision point — apply report §7.3, adjusted to the human's decisions, to `_docs/planning-process.md`; link the impact report from `README.md`
- agent role: Orchestrator (Claude Code main session)
- model: claude-opus-5-5 (Claude Code)
- prompt or instruction given (or link to a file in `_docs/prompts/`): Orchestrator's adjusted §7.3 proposal (items 1-4), accepted by the human with additions: Stage 3 file `_docs/api.md` and CI export of the generated OpenAPI document; Docker-capable dev environment and cost controls with teardown in the Stage 2 deployment bullet; deliberate, documented, removable responder defect in Stage 4; Stage 2 checklist line and component list; Stage 6 Reviewer reading list as a statement; no key prompt file in `_docs/prompts/`
- files changed: `_docs/planning-process.md` (Stage 2 components, observability and deployment bullets, checklist; Stage 3 API design; Stage 4 telemetry, alerting, responder and CI security scan; Stage 5 milestones; Stage 6 12 criteria and Reviewer list), `README.md` (impact report link); committed together (not protected). `opencode.json` and `.claude/settings.json` (changed outside this work, not read) left out of the commit
- verification (tests run, reviewer verdict): `git diff --check` clean; diff shown to the human before the final three additions, which were applied as instructed
- human review (what I checked or corrected, or `none`): human accepted items 1-4 and supplied the additions above; human dropped nothing

### 2026-10-17 — AI usage report header updated (§7.5, commit a535ff7)

- date: 2026-10-17
- task/issue: issue #11 decision point — apply report §7.5 to `_docs/ai-usage-report.md`
- agent role: Orchestrator (Claude Code main session)
- model: claude-opus-5-5 (Claude Code)
- prompt or instruction given (or link to a file in `_docs/prompts/`): human accepted the proposed header (not a scored criterion; kept for portfolio value and as supporting evidence) and the Orchestrator's change to section 2 (summarise and link `_docs/agent-team.md`, issue #12); no key prompt file in `_docs/prompts/`
- files changed: `_docs/ai-usage-report.md` (6 insertions, 4 deletions, commit a535ff7; not protected)
- verification (tests run, reviewer verdict): `git diff --check` clean
- human review (what I checked or corrected, or `none`): human approved both changes before they were made

### 2026-10-17 — Rubric Evidence Auditor regenerates rubric evidence for the 12 final criteria (§7.4, commit ad5b27d)

- date: 2026-10-17
- task/issue: issue #11 decision point — regenerate `_docs/rubric-evidence.md` for the final rubric (report §7.4)
- agent role: Rubric Evidence Auditor (Claude Code subagent; entry appended by Orchestrator, since the Orchestrator limited the auditor to editing `_docs/rubric-evidence.md` only)
- model: claude-opus-5-5 (Claude Code). Ran in Claude Code, not OpenCode, because OpenCode was unavailable; the human asked for this. An OpenCode re-audit is planned after Stage 2
- prompt or instruction given (or link to a file in `_docs/prompts/`): orchestrator instruction per the human's spec for the table (criterion, max points, full-marks condition quoted from `_docs/rubric.md`, status, evidence, gap), evidence only from what exists now, §7.4 mapping as a cross-check only; no key prompt file in `_docs/prompts/`
- files changed: `_docs/rubric-evidence.md` (12-row table, header with audit date and commit; 43 insertions, 21 deletions; committed by the Orchestrator as ad5b27d)
- verification (tests run, reviewer verdict): audited at a535ff7; 7 of 24 points evidenced (Problem Description PARTIAL 1; Product Specification, Agent Team Specification, Context Management MET 2 each; the other 8 MISSING). Auditor ran `make verify` (PASS WITH WARNINGS, no TEST_CMD) and opened the GitHub evidence with `gh --json/--jq`; no `.scratch/` scripts. Orchestrator checked `git status` showed only that file changed
- human review (what I checked or corrected, or `none`): none yet. Auditor findings for the human: the #11 commits are not pushed, so the public repo (at bd616a5) lacks the evidence for criteria 2-4; `.claude/agents/rubric-auditor.md` still says "14 criteria" and tells the auditor to append to the log (the #10 contradiction); a stray tracked `test.md` at the repo root; the local `origin/main` ref is stale (27d4760 vs remote bd616a5)

### 2026-10-17 — Orchestrator close-out of issue #11

- date: 2026-10-17
- task/issue: issue #11 close-out — clean scratch, session summary, close; plus human-requested housekeeping (fetch, remove `test.md`, #10 scope note, new README issue)
- agent role: Orchestrator (Claude Code main session)
- model: claude-opus-5-5 (Claude Code)
- prompt or instruction given (or link to a file in `_docs/prompts/`): human instruction to close #11 once `make assert-clean` passes, with an Orchestrator comment linking the decisions comment, and four extra items; no key prompt file in `_docs/prompts/`
- files changed: `_session-summaries/issue-011-final-rubric-impact.md` (updated, commit d013f00); `test.md` removed (0554a9f, human-approved). GitHub: comment 6230949666 on #10 (both rubric-auditor files: 12 criteria, same log-entry rule); filed #13 (README: Problem Description 1 → 2 points); closing Orchestrator comment on #11 linking decisions comment 6228520087; #11 closed. Local `origin/main` refreshed with `git fetch` (27d4760 → bd616a5); nothing pushed
- verification (tests run, reviewer verdict): `make assert-clean` PASS at d7f69a9 before close-out; `make clean-scratch` ran; QA PASS at c8dea47 and targeted re-check PASS at ed05530 stand
- human review (what I checked or corrected, or `none`): human committed their own `opencode.json` fix (d7f69a9) to unblock assert-clean and approved deleting `test.md`

### 2026-10-17 — Engineer implements issue #14 stages A and B (commits 7c12cd4, 6327f01)

- date: 2026-10-17
- task/issue: issue #14 stages A (Stage 3 process change) and B (DRAFT Lovable prompt) only, per PM grooming comment 6231923268
- agent role: Software Engineer (Claude Code subagent)
- model: claude-opus-5-5 (Claude Code)
- prompt or instruction given (or link to a file in `_docs/prompts/`): Orchestrator instruction to implement stages A and B as groomed, not C, D or E; no prompts index row (stage C); no key prompt file saved
- files changed: `_docs/planning-process.md` (§ Stage 3, one sentence, 3 lines added; 7c12cd4); `_docs/prompts/lovable-frontend.md` (new, Status: DRAFT, prompt 605 words; 6327f01). GitHub: Engineer comment 6232712832 on #14
- verification (tests run, reviewer verdict): `make verify BASE=ee0fcfe` PASS WITH WARNINGS (only warning: no TEST_CMD, no code exists); `.scratch/` check of the stage B criteria, including the secrets scan and its refused-case fixture, all PASS. QA not yet run
- human review (what I checked or corrected, or `none`): none yet; the draft awaits the human's approval (stage C)

### 2026-10-17 — Engineer revises the issue #14 Lovable prompt for Decision 3 (commit 2cbffa9)

- date: 2026-10-17
- task/issue: issue #14 stage B revision, applying the human's Decision 3 (build v1 now as discovery; richer model where unsure)
- agent role: Software Engineer (Claude Code subagent)
- model: claude-opus-5-5 (Claude Code)
- prompt or instruction given (or link to a file in `_docs/prompts/`): Orchestrator instruction quoting Decision 3 verbatim; no key prompt file saved
- files changed: `_docs/prompts/lovable-frontend.md` (still Status: DRAFT; header adds the discovery-build line, #3 ASSUMPTION now fixed versions per affected range with a "no fixed version" state, #6 ASSUMPTION now open / risk accepted / fixed / withdrawn with sources; prompt updates dashboard, detail, mock data and tests; prompt 698 words; 2cbffa9)
- verification (tests run, reviewer verdict): `make verify BASE=ee0fcfe` PASS WITH WARNINGS (only warning: no TEST_CMD, no code exists); updated `.scratch/check_issue14_b.py` (Decision 3 checks added) all PASS. QA not yet run
- human review (what I checked or corrected, or `none`): none yet; the draft awaits the human's approval (stage C)

### 2026-10-17 — Orchestrator runs issue #14 grooming and decisions; applies Decision 1 (commits f6add8a, 79b43e4)

- date: 2026-10-17
- task/issue: issue #14 (human chose it as next); PM grooming, Engineer stages A and B, human's Decisions 1-3; follow-up #15 filed
- agent role: Orchestrator (Claude Code main session), launching PM and Engineer subagents
- model: claude-opus-5-5 (Claude Code)
- prompt or instruction given (or link to a file in `_docs/prompts/`): human: "work on the next issue and follow process.md", then chose #14; Decisions 1-3 and notes given in session (quoted in PM comment 6232771876 on #14)
- files changed: `AGENTS.md` (protected, HUMAN_APPROVED=1; one line allowing a mocked frontend prototype in `frontend/` during planning; f6add8a); `_docs/planning-process.md` (same line, same wording; 79b43e4). GitHub, by PM subagent: grooming comment 6231923268 and approval request 6232722317 and decisions comment 6232771876 on #14; comment 6232771639 on #6; filed #15 (stages D-E)
- verification (tests run, reviewer verdict): human reviewed both diffs before they were applied; QA of stages A and B not yet run (human to run it in a fresh OpenCode session, per the #11 rule that QA doesn't run in the tool that built the work)
- human review (what I checked or corrected, or `none`): human approved Decision 1 wording and both diffs; accepted the Engineer's three choices (no "stale" status, dashboard status filter, a mock finding with no aliases); prompt approval to follow separately

### 2026-10-17 — Engineer applies the human's three edits to the issue #14 Lovable prompt (commit 67322c9)

- date: 2026-10-17
- task/issue: issue #14 stage B revision, the human's three edits before prompt approval (services-layer order with no re-sort and pre-ranked mock data; React with TypeScript and `npm test`; demo credentials on the login screen)
- agent role: Software Engineer (Claude Code subagent)
- model: claude-opus-5-5 (Claude Code)
- prompt or instruction given (or link to a file in `_docs/prompts/`): Orchestrator instruction quoting the human's three edits verbatim; no key prompt file saved
- files changed: `_docs/prompts/lovable-frontend.md` (still Status: DRAFT; screen 2 and first test use the human's wording; mock data pre-ranked by the `_docs/planning-process.md` § Stage 2 tie-breaks; Stage 2 header ASSUMPTION updated, including criticality higher first and missing EPSS last, which Stage 2 does not state; prompt 774 words, up from 698, all from these edits; 67322c9). GitHub: Engineer comment 6232991787 on #14
- verification (tests run, reviewer verdict): `make verify BASE=ee0fcfe` PASS WITH WARNINGS (only warning: no TEST_CMD, no code exists); updated `.scratch/check_issue14_b.py` (word limit is 698 plus the net words of these edits; new-text checks) all PASS. QA not yet run
- human review (what I checked or corrected, or `none`): none yet; the revised draft awaits QA and the human's approval

### 2026-10-17 — Engineer corrects the record for the issue #14 prompt edits (commit 67322c9)

- date: 2026-10-17
- task/issue: issue #14, fix for QA FAIL comment 6233025035 (record correction only)
- agent role: Software Engineer (Claude Code subagent)
- model: claude-opus-5-5 (Claude Code)
- prompt or instruction given (or link to a file in `_docs/prompts/`): Orchestrator instruction to correct the record after QA FAIL 6233025035, with the human's decision recorded in Orchestrator comment 6233052344; no key prompt file saved
- correction: the previous entry (commit 67322c9) and Engineer comment 6232991787 said all 76 added words (698 to 774) came from the human's three edits. That was inaccurate. 12 of the 76 words were the Engineer's own sentence, added after the human's demo-credentials line: "They are fictional; if the username is an email, it uses example.com." QA FAIL comment 6233025035 found this. The human accepted the sentence as part of edit 3 and waived the 700-word limit for this prompt, so 774 words stands (Orchestrator comment 6233052344)
- files changed: `_docs/ai-usage-log.md` (this entry only; the earlier entry is left as written). `_docs/prompts/lovable-frontend.md` not changed. GitHub: new Engineer comment on #14 with the same correction
- verification (tests run, reviewer verdict): `make verify BASE=ee0fcfe` run after this commit; result reported in the Engineer comment on #14. QA not yet re-run
- human review (what I checked or corrected, or `none`): the human decided to accept the sentence and waive the word limit (comment 6233052344); this entry itself not yet reviewed

### 2026-10-17 — Engineer marks the issue #14 Lovable prompt APPROVED and indexes it (commit efa250d)

- date: 2026-10-17
- task/issue: issue #14 stage C (approval and index entry)
- agent role: Software Engineer (Claude Code subagent)
- model: claude-opus-5-5 (Claude Code)
- prompt or instruction given (or link to a file in `_docs/prompts/`): Orchestrator instruction quoting the human's approval given in session: "I looked at the prompt and approve it, date approval today." Prompt file: `_docs/prompts/lovable-frontend.md`
- files changed: `_docs/prompts/lovable-frontend.md` (line 1 only, `Status: DRAFT` to `Status: APPROVED (human, 2026-10-17)`); `_docs/prompts/README.md` (one index row; "where executed" says Lovable, run by the human, not yet run, since the build is in #15 per Decision 2); efa250d, an amend of unpushed 7ba1140 that corrected the row's issue number from "stage D of #14" to #15. GitHub: Engineer comment on #14
- verification (tests run, reviewer verdict): `make verify BASE=ee0fcfe` PASS WITH WARNINGS (only warning: no TEST_CMD, no code exists); `git diff --stat` showed 2 files, 2 insertions, 1 deletion; `git log --follow` on the prompt lists 6327f01, 2cbffa9, 67322c9, 7ba1140 (re-run after the amend gives efa250d in its place). Decision 3 (approve before #3, #4, #6) was answered by the human, as recorded in PM comment 6232771876. QA of stage C not yet run
- human review (what I checked or corrected, or `none`): the human approved the prompt text; this commit not yet reviewed

### 2026-10-17 — PM re-grooms issue #15 for the Bolt build; issue parked

- date: 2026-10-17
- task/issue: issue #15, lifecycle step 2 (grooming), after the human's commit fea6fb7 added a Bolt-built frontend in `frontend-bolt/`
- agent role: PM (Claude Code subagent), launched by the Orchestrator
- model: claude-opus-5-5 (Claude Code)
- prompt or instruction given (or link to a file in `_docs/prompts/`): Orchestrator instruction to re-groom #15 for the Bolt build, read-only on `frontend-bolt/`, no npm runs; no key prompt file saved
- files changed: none in the repo (drafts in `.scratch/` only). GitHub: PM comments 6234073282 (re-grooming, three decision questions) and 6234079369 (marks Bolt as settled, quoting the human); Orchestrator comment 6234114564 (the human's answers; issue parked)
- verification (tests run, reviewer verdict): none; the PM read `frontend-bolt/` and grepped it, with nothing run or installed. Issue body not edited
- human review (what I checked or corrected, or `none`): the human explained the switch to Bolt ("I tried to build in lovable but hit a credit limit. I tried the same prompt in Bolt..."), confirmed the prompt was pasted verbatim with no follow-ups, kept `.bolt/` for now, and deferred the other decisions until the Lovable credits reset

### 2026-10-17 — PM grooms issue #12 (agent-team document)

- date: 2026-10-17
- task/issue: issue #12, lifecycle step 2 (grooming)
- agent role: PM (Claude Code subagent), launched by the Orchestrator
- model: claude-opus-5-5 (Claude Code)
- prompt or instruction given (or link to a file in `_docs/prompts/`): Orchestrator instruction to groom #12 per `task-template.md`; no key prompt file saved
- files changed: none in the repo. GitHub: PM comments 6234146060 (proposed body, two decision questions) and 6234208915 (the human's answers). The issue body was replaced with the groomed body (`gh issue edit 12`): the tool blocked the PM's run, and the Orchestrator ran the command after the human typed it in session
- verification (tests run, reviewer verdict): body length checked after the edit (9086 characters, against 1581 before)
- human review (what I checked or corrected, or `none`): the human chose option 1 for both decisions (the PM's wording for the QA same-tool exception; intent plus record for tool and model)

### 2026-10-17 — Engineer implements issue #12 (commit ede47bf)

- date: 2026-10-17
- task/issue: issue #12, lifecycle step 3: write `_docs/agent-team.md` and link it from `README.md`; propose the `AGENTS.md` line
- agent role: Software Engineer (Claude Code subagent, launched by the Orchestrator; entry appended by the Engineer, as its role file says while #10 is open)
- model: claude-opus-5-5 (Claude Code)
- prompt or instruction given (or link to a file in `_docs/prompts/`): Orchestrator instruction to implement the groomed #12 body with the human's answers in PM comment 6234208915 (option 1 for both decisions), base ccd13b6, and to return the `AGENTS.md` diff for approval rather than commit it; no key prompt file saved
- files changed: `_docs/agent-team.md` (new), `README.md` (one link line); 116 insertions, commit ede47bf. `AGENTS.md` not edited; the one-line diff is proposed in Engineer comment 6234459590 on #12
- verification (tests run, reviewer verdict): `make verify BASE=ccd13b6` PASS WITH WARNINGS (only warning: no TEST_CMD, no code exists; whitespace PASS; no test files changed); `.scratch/check_issue12.py` (relative links and anchors, 15 commits via `git cat-file -e`, cited issues and comment ids via `gh issue view --json`, verbatim exception and intent text, model ids, refused cases) PASS. QA not yet run
- human review (what I checked or corrected, or `none`): none yet

### 2026-10-18 — Orchestrator commits the approved AGENTS.md line for issue #12 (commit 948e332)

- date: 2026-10-18
- task/issue: issue #12, protected-file change
- agent role: Orchestrator (Claude Code main session)
- model: claude-opus-5-5 (Claude Code)
- prompt or instruction given (or link to a file in `_docs/prompts/`): the human's in-session answer "Approve as written" to the line proposed in Engineer comment 6234459590; no key prompt file saved
- files changed: `AGENTS.md` (one line in "Where to read more"), committed on its own with `HUMAN_APPROVED=1` as 948e332. GitHub: Orchestrator comment 6243691600 records the approval and the human's choice of QA tool
- verification (tests run, reviewer verdict): `git diff` showed the approved line only; `git diff --check` clean. QA checked it afterwards (next entry)
- human review (what I checked or corrected, or `none`): the human approved the exact line in session

### 2026-10-18 — QA checks issue #12 (PASS at 948e332)

- date: 2026-10-18
- task/issue: issue #12, lifecycle step 4
- agent role: QA Engineer (fresh Claude Code qa-engineer subagent, launched by the Orchestrator; entry appended by the Orchestrator after `make assert-clean`, as the QA role file says)
- model: claude-opus-5-5 (Claude Code). It ran in Claude Code, the same tool as the build, because OpenCode is unavailable and the human chose this (comment 6243691600), under the exception in comment 6234208915
- prompt or instruction given (or link to a file in `_docs/prompts/`): Orchestrator instruction to check every #12 criterion independently at 948e332, base ccd13b6; no key prompt file saved
- files changed: none in the repo (`.scratch/qa12_check.py`, `.scratch/qa12_hook_test.sh` and `.scratch/qa12-comment.md` only). GitHub: QA comment 6243727864
- verification (tests run, reviewer verdict): QA PASS, all 21 criteria. `make verify BASE=ccd13b6` PASS WITH WARNINGS (only warning: no TEST_CMD); QA's own link, commit, issue, quote and refused-case checks; a hook test in a throwaway repo under `.scratch/` (unapproved `AGENTS.md` staging refused, `HUMAN_APPROVED=1` allowed). The guard hook blocked one `git config core.hooksPath`; QA re-ran it as `git config --get core.hooksPath` (result `.githooks`). After QA, `make assert-clean` PASS and HEAD unchanged at 948e332
- human review (what I checked or corrected, or `none`): none yet; QA's risks go to the human at the decision point

### 2026-10-18 — Engineer fixes `_docs/agent-team.md` after the #12 decision point (commit 32ed2a3)

- date: 2026-10-18
- task/issue: issue #12, lifecycle step 7 back to step 3: apply the human's decision-point answers (Orchestrator comment 6243801494) to `_docs/agent-team.md`
- agent role: Software Engineer (Claude Code subagent, launched by the Orchestrator; entry appended by the Engineer, as its role file says while #10 is open)
- model: claude-opus-5-5 (Claude Code)
- prompt or instruction given (or link to a file in `_docs/prompts/`): Orchestrator instruction listing the human's four decisions (role "not recorded" where the log says so; `CLAUDE.md` claims match `6541893`; add the #12 Engineer and QA runs, QA under the same-tool exception; settings text consistent with the new `AGENTS.md` rule) and "Don't change anything else"; no key prompt file saved
- files changed: `_docs/agent-team.md` (history table gains a "not recorded" role row for the 2026-10-12 entries and `c631603`; #12 Engineer and QA added; third recorded exception use; handover bullets on `CLAUDE.md` and tracked settings files; 10 insertions, 9 deletions, commit 32ed2a3). GitHub: Engineer comment 6243814434 on #12
- verification (tests run, reviewer verdict): `make verify BASE=ccd13b6` PASS WITH WARNINGS (only warning: no TEST_CMD, no code exists; whitespace PASS; no test files changed); `git diff --check` clean. QA re-check not yet run
- human review (what I checked or corrected, or `none`): none yet

### 2026-10-18 — Orchestrator commits the approved settings and scratchpad change at the issue #12 decision point (commit 6541893)

- date: 2026-10-18
- task/issue: issue #12, lifecycle step 7 (decision point), protected-file change
- agent role: Orchestrator (Claude Code main session)
- model: claude-opus-5-5 (Claude Code)
- prompt or instruction given (or link to a file in `_docs/prompts/`): the human's in-session answers, recorded in Orchestrator comment 6243801494: the tracked-settings rule in the human's wording (only the missing spaces from line wrapping fixed, and backticks added); the scratchpad line moved from `CLAUDE.md` into `AGENTS.md`; "Approve as shown" for the exact diff
- files changed: `AGENTS.md` (scratch-files line extended; tracked-settings rule added; home-folder and environment-variables rule kept), `CLAUDE.md` (now only `@AGENTS.md`); committed with `HUMAN_APPROVED=1` as 6541893
- verification (tests run, reviewer verdict): `git diff` reviewed against the approved diff; `git diff --check` clean. QA re-check PASS (next entry)
- human review (what I checked or corrected, or `none`): the human approved the exact diff in session

### 2026-10-18 — QA re-checks the issue #12 decision-point changes (PASS at 92d9926)

- date: 2026-10-18
- task/issue: issue #12, lifecycle step 7: QA re-checks only what changed (6541893, 32ed2a3, 92d9926)
- agent role: QA Engineer (fresh Claude Code qa-engineer subagent, launched by the Orchestrator; entry appended by the Orchestrator after `make assert-clean`)
- model: claude-opus-5-5 (Claude Code). It ran in Claude Code, the same tool as the build, because OpenCode is unavailable and the human chose this (comment 6243691600), under the exception in comment 6234208915
- prompt or instruction given (or link to a file in `_docs/prompts/`): Orchestrator instruction to re-check the three commits against comments 6243801494 and 6243814434, and to re-confirm file scope over ccd13b6..HEAD; no key prompt file saved
- files changed: none in the repo (`.scratch/qa12_recheck.py` and `.scratch/qa12-recheck-comment.md` only). GitHub: QA comment 6243839013
- verification (tests run, reviewer verdict): QA PASS. `python3 .scratch/qa12_recheck.py`: 19 checks, 0 failed. `make verify BASE=ccd13b6` PASS WITH WARNINGS (only warning: no TEST_CMD). Scope note: `CLAUDE.md`, and the second `AGENTS.md` change, fall outside the criterion's file list; both come from the human-approved 6541893. After QA, `make assert-clean` PASS and HEAD unchanged at 92d9926
- human review (what I checked or corrected, or `none`): none yet

### 2026-10-18 — PM files four follow-up issues from #12 (#16 to #19)

- date: 2026-10-18
- task/issue: #12 follow-ups (lifecycle step 7). After #12 closed, the human asked for the QA risks to be filed as future issues. This replaces "none selected" in Orchestrator comment 6243801494 and in the #12 session summary
- agent role: PM (Claude Code subagent, launched by the Orchestrator; entry appended by the Orchestrator)
- model: claude-opus-5-5 (Claude Code)
- prompt or instruction given (or link to a file in `_docs/prompts/`): Orchestrator instruction to file one ungroomed issue per risk; no key prompt file saved. A first PM run stopped when the session ended, before filing anything (checked: no new issues or comments, clean tree); a fresh PM run did the task
- files changed: none in the repo. GitHub: #16 (agent-team.md history table upkeep), #17 (`_docs/agent-kit/scripts/check-staged.sh` doesn't enforce "committed alone"; a protected path), #18 (record approvals as exact text), #19 (`_docs/ai-usage-report.md` §2 TODO)
- verification (tests run, reviewer verdict): the PM checked open issues #3-#10, #13 and #15 for duplicates and found none. Not groomed yet
- human review (what I checked or corrected, or `none`): none yet
