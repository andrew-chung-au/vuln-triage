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

### 2026-10-18 — Orchestrator compares the Bolt and Lovable prototypes (#15)

- date: 2026-10-18
- task/issue: issue #15. The human asked for both prototypes (`frontend-bolt/` at fea6fb7, `frontend-lovable/` at 0dd108a) to be reviewed, one chosen and renamed `frontend/`, and follow-up issues drafted for course steps 3-6
- agent role: Orchestrator (Claude Code main session)
- model: claude-opus-5-5 (Claude Code)
- prompt or instruction given (or link to a file in `_docs/prompts/`): the human's in-session request; no key prompt file saved
- files changed: `_docs/reviews/2026-10-18-frontend-comparison.md` (51b477a). GitHub: Orchestrator comment 6244151098 on #15 recording the human's four decisions (Lovable chosen; `frontend-bolt/` deleted in its own commit; F0-F6 filed with F4-F6 gated on the phase line; `openapi.yaml` as contract plus a FastAPI conformance test)
- verification (tests run, reviewer verdict): static read only. Node.js and npm are not installed (`node --version`: command not found), so neither app was installed, built or tested. Read-only greps: every email in both `src/` trees uses example.com/.org/.net; network-call grep hits recorded in the review
- human review (what I checked or corrected, or `none`): the human chose the recommended option on all four decisions

### 2026-10-18 — PM re-grooms #15 for Lovable and files #20-#26

- date: 2026-10-18
- task/issue: issue #15 (lifecycle step 2, re-grooming) and follow-ups F0-F6 from the 2026-10-18 frontend comparison
- agent role: PM (Claude Code pm subagent, launched by the Orchestrator; entry appended by the Orchestrator)
- model: claude-opus-5-5 (Claude Code)
- prompt or instruction given (or link to a file in `_docs/prompts/`): Orchestrator instruction to re-groom #15 per the human's decisions and file F0-F6; the human's stage D values relayed during the run ("build completition date 18-10-2026. total credits used is 6. no follow up prompts used, only the resume function"); no key prompt file saved
- files changed: none in the repo. GitHub: #15 body and title rewritten (stage D run record; stage E split into E1, no Node needed, and E2, after #20), PM comment 6244224555; new issues #20 (dev container Node and uv), #21 (frontend clean-up), #22 (services layer ready for a real API), #23 (API contract), #24 (FastAPI in-memory backend), #25 (connect frontend and backend), #26 (SQLAlchemy persistence). #24-#26 are blocked until the human changes the AGENTS.md "Current phase" line
- verification (tests run, reviewer verdict): none; the issues are not yet implemented
- human review (what I checked or corrected, or `none`): none yet

### 2026-10-18 — Engineer records the frontend runs and moves Lovable to frontend/ (#15 stage D and part E1)

- date: 2026-10-18
- task/issue: issue #15, stage D (run record) and part E1 (move, delete, scan, document). Part E2 not started: Node.js is not installed and E2 waits for #20
- agent role: Software Engineer (Claude Code software-engineer subagent, launched by the Orchestrator)
- model: claude-opus-5-5 (Claude Code)
- prompt or instruction given (or link to a file in `_docs/prompts/`): Orchestrator instruction to implement #15 stage D and E1 only; no key prompt file saved
- run facts recorded (from the human, relayed by the Orchestrator; the agent never used either tool): the prompt was `_docs/prompts/lovable-frontend.md` `## Prompt`, pasted verbatim into both tools. Lovable first attempt 2026-10-17 stopped at the credit limit. Bolt, 2026-10-17: no follow-up prompts, credits not recorded, project https://bolt.new/~/sb1-fvxy4uq3, committed by the human in fea6fb7 under `frontend-bolt/` (compared, not chosen). Lovable, build completed 2026-10-18: 6 credits in total, no follow-up prompts (continued with Lovable's resume function), project https://lovable.dev/projects/f9cb1f93-46d1-4d9b-baa6-4e09b65a57f3, committed by the human in 0dd108a under `frontend-lovable/` (chosen)
- files changed: b566fb6 (`git mv frontend-lovable frontend`, 94 renames at 100%); cbe2123 (`git rm -r frontend-bolt`, 37 deletions, human-approved decision 2; code stays at fea6fb7); 73a70af (`frontend/.gitignore`: `.env`, `.env.*`, `!.env.example`); 4a9f328 (`_docs/prompts/lovable-frontend.md` run record and follow-ups line, `_docs/prompts/README.md` "Used with" row, `frontend/README.md` Services layer section); this entry. GitHub: Engineer comment on #15
- verification (tests run, reviewer verdict): `.scratch/issue15_scan.py` over the 94 files in `git ls-files frontend`: 1 hit, the fictional demo password `triage-demo` (harmless); fixture `.scratch/issue15_fixture.txt` flagged all 3 lines. `.scratch/issue15_prompt_check.py`: Status line and `## Prompt` section identical to 0dd108a. Network and backend-key greps run. `make verify`: FAIL on "test files deleted" (2 renamed Lovable tests, a false positive of the gate's `--no-renames` diff, and 4 Bolt tests in the approved deletion); referred to the human. No tests run: no Node.js
- human review (what I checked or corrected, or `none`): none yet

### 2026-10-18 — Orchestrator and PM act on the human's #15 install, Stage 3, n8n/MCP and spec answers

- date: 2026-10-18
- task/issue: issue #15 follow-ups (the human's answers to the PM's three questions and spec note)
- agent role: Orchestrator (Claude Code main session) and PM (Claude Code pm subagent, resumed; entry appended by the Orchestrator)
- model: claude-opus-5-5 (Claude Code)
- prompt or instruction given (or link to a file in `_docs/prompts/`): the human's in-session answers: E2 first install with `npm install --before=2026-10-18`; the Stage 3 wording in the human's own text (only the spaces lost to line wrapping restored), recorded on #11 as a change to its decision 2; file the n8n/MCP contract issue; add the owner assumption to `specs.md`
- files changed: `_docs/specs.md` (one Assumptions line, d3a8f11, `HUMAN_APPROVED=1`). GitHub: Orchestrator comment 6244293385 on #11; PM: #15 body (E2 install criterion), comment 6244314164; #23 body (approved Stage 3 text, human review of `openapi.yaml`), comment 6244314486; new issue #27 (n8n and MCP server endpoints, depends on #23)
- verification (tests run, reviewer verdict): `git diff` of the `specs.md` change matched the approved line; `git diff --check` clean
- human review (what I checked or corrected, or `none`): the human approved the `specs.md` line and the Stage 3 text in session

### 2026-10-18 — Engineer fixes the weakened-tests check for renames and approved deletions (#28)

- date: 2026-10-18
- task/issue: issue #28 (verify gate: test-file renames count as moves; `APPROVED_TEST_DELETIONS` in `agent-kit.conf`)
- agent role: Software Engineer (Claude Code software-engineer subagent, launched by the Orchestrator)
- model: claude-opus-5-5 (Claude Code)
- prompt or instruction given (or link to a file in `_docs/prompts/`): Orchestrator instruction to implement #28, run the fixture script and `make verify BASE=0dd108a`, and return the protected diff with an approval request before committing; no key prompt file saved
- files changed: `_docs/agent-kit/scripts/verify.sh` (rename-aware `-M` diff, R100 moves skipped, edited renames diffed old to new, exact-path approved deletions, glob entries fail) and `agent-kit.conf` (`APPROVED_TEST_DELETIONS` with the four `frontend-bolt/` test paths), both protected, committed alone in 035eafd with `HUMAN_APPROVED=1` (`git show --stat --format= 035eafd` lists only those two files); `lib.sh` unchanged; this entry; `_session-summaries/issue-028-verify-renames.md`. GitHub: Engineer comment on #28
- verification (tests run, reviewer verdict): `.scratch/issue-28-verify-fixtures.sh`: 24 passed, 0 failed (throwaway repos under `.scratch/issue-28-fixtures/`; this repository's HEAD and `git status --short` the same before and after). `make verify BASE=0dd108a` (uncommitted changes): weakened-tests section lists the four Bolt paths under "Deleted with approval", no deletion FAIL; result PASS WITH WARNINGS (only the no-TEST_CMD warning); same result after 035eafd. No QA yet
- human review (what I checked or corrected, or `none`): the human approved the exact diff of `verify.sh` and `agent-kit.conf` in session, 2026-10-18 ("Approve as shown (Recommended)", relayed by the Orchestrator, who checked the working-tree diff matched)

### 2026-10-18 — QA checks #28 (PASS at d32840c); decision point; #15 stage D/E1 QA (FAIL on commit scope)

- date: 2026-10-18
- task/issue: issue #28, lifecycle steps 4-7; issue #15, stage D and part E1, lifecycle step 4
- agent role: QA Engineer (two fresh Claude Code qa-engineer subagents, launched by the Orchestrator; entry appended by the Orchestrator after `make assert-clean`) and Orchestrator (decision point)
- model: claude-opus-5-5 (Claude Code)
- prompt or instruction given (or link to a file in `_docs/prompts/`): Orchestrator instructions to check #28 against its criteria with QA's own fixtures, and #15 stage D and E1 (E2 listed as not yet checked); no key prompt file saved
- files changed: none in the repo (QA scripts in `.scratch/` only). GitHub: QA PASS on #28 (comment 6246783716); QA FAIL on #15 D/E1 (comment 6246840624); Orchestrator decision comments 6247718969 (#28) and 6247719173 (#15)
- verification (tests run, reviewer verdict): #28: QA's `.scratch/qa-28-checks.sh` passed all 27 criteria checks; the Engineer's fixture script passed 24/24; `make verify BASE=0dd108a` PASS WITH WARNINGS (no TEST_CMD only). #15: every D/E1 check passed except E1 (c): `git log --grep="#15"` also matched d3a8f11 (`specs.md`, human-approved), which is outside the allowed paths. After each QA run, `make assert-clean` PASS and HEAD unchanged at d32840c
- human review (what I checked or corrected, or `none`): the human decided QA's risks: #28 risks 1 and 2 to be filed as follow-ups, risk 3 not filed ("bolt was not used"), with a note on #21; #15 E1 (c) to list commits explicitly, "(private)" markings added to #15, and the Lovable project "not linked" to this repo

### 2026-10-18 — Engineer marks the #15 project links "(private)" (new stage D criterion)

- date: 2026-10-18
- task/issue: issue #15, stage D, the new "(private)" criterion (Orchestrator decision comment 6247719173, decision 2; PM comment 6247739573). This entry adds to the d85632b entry, which is not edited
- agent role: Software Engineer (Claude Code software-engineer subagent, launched by the Orchestrator)
- model: claude-opus-5-5 (Claude Code)
- prompt or instruction given (or link to a file in `_docs/prompts/`): Orchestrator instruction to mark the links, replace the VERIFY line with the human's answer, and list every #15 Engineer commit for E1 (c); no key prompt file saved
- files changed: 26b8757 (`_docs/prompts/lovable-frontend.md`: "(private)" on the Bolt and Lovable link lines, the run record's VERIFY line replaced with the human's answer "both are private on gh" from comment 6246359512; `frontend/README.md`: "(private)" on the Lovable link line); this entry. GitHub: Engineer comment on #15
- verification (tests run, reviewer verdict): `grep -nE "bolt\.new/|lovable\.dev/projects/|VERIFY"` on both files lists 3 link lines, each with "(private)", and no VERIFY line. `.scratch/issue15_prompt_check.py`: Status line and `## Prompt` section identical to 0dd108a. `make verify BASE=0dd108a` result is in the Engineer comment
- human review (what I checked or corrected, or `none`): none yet

### 2026-10-18 — QA re-checks #15 stage D / part E1 (PASS at 3abcc65)

- date: 2026-10-18
- task/issue: issue #15, stage D and part E1, lifecycle step 4 re-check of what changed after QA FAIL 6246840624
- agent role: QA Engineer (fresh Claude Code qa-engineer subagent, launched by the Orchestrator; entry appended by the Orchestrator after `make assert-clean`)
- model: claude-opus-5-5 (Claude Code)
- prompt or instruction given (or link to a file in `_docs/prompts/`): Orchestrator instruction to re-check only the reworded E1 (c), the new "(private)" criterion, the prompt byte-check and `make verify`; no key prompt file saved
- files changed: none in the repo (`.scratch/qa15_recheck.py` and its comment body only). GitHub: QA PASS comment 6247797817
- verification (tests run, reviewer verdict): QA PASS for D/E1. All seven listed #15 Engineer commits touch only allowed paths; 3 link lines carry "(private)" and no VERIFY line is left; the usage log diff since d85632b removes no line; `## Prompt` byte-identical to 0dd108a; `make verify BASE=0dd108a` PASS WITH WARNINGS (no TEST_CMD only). E2 not yet checked (waits for #20). QA reported running one inline `python3 -c "print(1)"`, against the AGENTS.md rule; it changed nothing. After QA, `make assert-clean` PASS, HEAD unchanged at 3abcc65
- human review (what I checked or corrected, or `none`): none yet

### 2026-10-18 — PM grooms issue #20 (dev container Node.js + uv)

- date: 2026-10-18
- task/issue: issue #20 — first grooming; pin the open Node/uv values, correct the stale feature id, close the lockfile question, add refused cases
- agent role: PM (Product Manager subagent, launched by the Orchestrator; entry appended by the Orchestrator per the write-only-`.scratch/` role limit)
- model: opencode/deepseek-v4.1-flash-free
- prompt or instruction given (or link to a file in `_docs/prompts/`): Orchestrator instruction to groom #20 per `_docs/agent-kit/team/pm.md`; no key prompt file saved
- files changed: none in the repo (drafts in `.scratch/`). GitHub: PM grooming comment 6247960494; #20 body edited to the groomed text; PM decisions comment 6248923707; filed follow-up #31 (Docker/Compose), linked from #20 out-of-scope
- verification (tests run, reviewer verdict): none (no code changed). PM read `frontend/package.json` (vite 8.1.5), the devcontainers/features node feature, nodejs/Release schedule and PyPI/uv metadata to pin the values
- human review (what I checked or corrected, or `none`): the human answered the four grooming decisions (Node `24.22.0`; uv via `pipx install uv==0.13.1`; file #31; apply the body edits as drafted)

### 2026-10-18 — Engineer implements #20 (uncommitted, held for the human's gated commit)

- date: 2026-10-18
- task/issue: issue #20 — add pinned Node.js (`ghcr.io/devcontainers/features/node:2` at `24.22.0`, `pnpmVersion: none`), remove the duplicate `remoteEnv.PATH`, and add `pipx install uv==0.13.1`
- agent role: Software Engineer (opencode software-engineer subagent, launched by the Orchestrator; entry appended by the Orchestrator per the write-only-`.scratch/` role limit)
- model: opencode/deepseek-v4.1-flash-free
- prompt or instruction given (or link to a file in `_docs/prompts/`): Orchestrator instruction to implement #20 from the groomed body, not rebuild, and return the diff and approval request; no key prompt file saved
- files changed: `.devcontainer/devcontainer.json` and `.devcontainer/setup.sh` in the working tree only — UNCOMMITTED, because the pre-commit hook gates any `.devcontainer/` change behind `HUMAN_APPROVED=1`; the Engineer stopped and returned the approval request. `.scratch/issue-20-check.py`, `.scratch/issue-20-tooling.sh`, `.scratch/issue-20-pipx-writable.py` (git-ignored). Proposed (not edited) AGENTS.md Environment line. This entry and `_session-summaries/issue-020-node-uv-devcontainer.md`
- verification (tests run, reviewer verdict): `make verify BASE=HEAD` PASS WITH WARNINGS (only the no-`TEST_CMD` warning; project in planning, no code); `.scratch/issue-20-check.py` all static criteria PASS including the refused-case patterns. Runtime `node`/`npm`/`uv` not run (no Node or uv in this container; deferred to QA after the human rebuilds). `.devcontainer/devcontainer-lock.json` not regenerated (no devcontainer CLI here); raised as a decision question
- human review (what I checked or corrected, or `none`): the human chose to run the `.devcontainer/` commit commands themselves and chose lockfile option 1 with checks (show the regenerated-lock diff after the rebuild; only new feature entries; `github-cli` unchanged; if not updated, stop). The commit and rebuild are pending

### 2026-10-18 — Add `make tool-versions` target and document it (human instruction, no issue)

- date: 2026-10-18
- task/issue: add a `make tool-versions` target that prints the version of node, npm, uv, python3 and docker (or `<tool>: missing`), and add it to the AGENTS.md Commands section (human instruction, no issue)
- agent role: Orchestrator
- model: opencode/deepseek-v4.1-flash-free
- prompt or instruction given (or link to a file in `_docs/prompts/`): human instruction in-session ("Add a `tool-versions` target to the Makefile's project section (protected; show me the diff) that prints the version of node, npm, uv, python3 and docker, or \"<tool>: missing\" ... Add it to AGENTS.md's Commands section."); no key prompt file saved
- files changed: `Makefile` (new `tool-versions` target with `##` help text, in the project section; 3 insertions); `AGENTS.md` (Commands line "Tool versions:"; the whole file was committed, carrying the human's pre-existing uncommitted Project-rules additions); this entry
- verification (tests run, reviewer verdict): `make tool-versions` printed `node: missing`, `npm: missing`, `uv: missing`, `python3: Python 3.12.15`, `docker: missing`; `make help` lists `tool-versions`; `git diff --check` clean
- human review (what I checked or corrected, or `none`): the human approved committing `Makefile` and `AGENTS.md` with `HUMAN_APPROVED=1`, including the pre-existing AGENTS.md Project-rules edits

### 2026-10-18 — Engineer runs the post-rebuild runtime checks and Verify for #20 (lifecycle step 3)

- date: 2026-10-18
- task/issue: issue #20, lifecycle step 3 continued after the human rebuilt the container: the post-rebuild runtime checks (`node`/`npm`/`uv --version` exit 0, and the non-interactive `make`-shell criterion), run Verify, and post the Engineer comment
- agent role: Software Engineer (opencode software-engineer subagent, launched by the Orchestrator; entry appended by the Engineer, as its role file says)
- model: opencode/deepseek-v4.1-flash-free
- prompt or instruction given (or link to a file in `_docs/prompts/`): Orchestrator instruction to run the runtime checks the post-rebuild criteria need, run Verify with the appropriate BASE, post the Engineer `:` comment on #20, and append this entry; no key prompt file saved
- files changed: `.scratch/issue-020-runtime-check.sh` (git-ignored; read-only checks, no installs and no network); this entry. No repo file other than this entry changed. GitHub: Engineer comment 6249655264 on #20 (body drafted in `.scratch/issue-020-engineer-comment.md`)
- verification (tests run, reviewer verdict): `make verify BASE=dc843de` (the issue's own commits 4eb0485 and f3ed87d; 4 files, 35 insertions, 14 deletions) PASS WITH WARNINGS, and `make verify` (default, since `origin/main`) PASS WITH WARNINGS; the only warning in each is the no-`TEST_CMD` one (planning phase, no code exists; whitespace PASS; no test files changed). `.scratch/issue-020-runtime-check.sh` every check exit 0: `node --version` v24.22.0, `npm --version` 11.19.1, `uv --version` uv 0.13.1 (x86_64-unknown-linux-gnu); the same three in a non-interactive `sh -c`; `command -v` resolves node/npm to `/usr/local/share/nvm/versions/node/v24.22.0/bin/` and uv to `/usr/local/py-utils/bin/uv`; `make tool-versions` exit 0. Finding reported to the human: commit 4eb0485 also changes `opencode.json` (not in #20's Constraints). QA not run
- human review (what I checked or corrected, or `none`): none yet; the report raises two items for the human — the `opencode.json` change bundled into 4eb0485 (outside #20's Constraints, protected file, not touched) and the proposed AGENTS.md Environment line, which is not edited

### 2026-10-18 — QA checks #20 (PASS at abaed5d)

- date: 2026-10-18
- task/issue: issue #20 (dev container Node.js and uv), lifecycle step 4
- agent role: QA Engineer (fresh opencode qa-engineer subagent, launched by the Orchestrator; entry appended by the Orchestrator after `make assert-clean` per the role's write-only-`.scratch/` limit)
- model: opencode/deepseek-v4.1-flash-free
- prompt or instruction given (or link to a file in `_docs/prompts/`): Orchestrator instruction to check every criterion in #20 against the rebuilt container and the committed diff (`git diff dc843de..HEAD -- .devcontainer` for the refused cases), run `node`/`npm`/`uv --version` and the non-interactive `make`-shell check, run Verify itself, and post a `QA:` verdict; no key prompt file saved
- files changed: none in the repo (`.scratch/issue-020-qa-check.py` and `.scratch/qa-comment-20.md` only). GitHub: QA PASS comment 6249711806
- verification (tests run, reviewer verdict): QA PASS, all nine criteria. `node --version` v24.22.0, `npm --version` 11.19.1, `uv --version` uv 0.13.1; both `sh -c` and `make tool-versions` resolve all three; `remoteEnv` has exactly one `PATH` with all three segments; `git diff dc843de..HEAD -- .devcontainer` shows no refused pattern; the lockfile adds one `node:2` entry and leaves `github-cli:1` byte-identical. The AGENTS.md Environment criterion was treated as PASS (deferred): the issue words it as a protected `HUMAN_APPROVED=1` commit applied at the post-PASS decision point, so QA checked the Engineer's proposed text. `make verify BASE=dc843de` and `make verify` both PASS WITH WARNINGS (only the no-`TEST_CMD` warning). After QA, `make assert-clean` PASS and HEAD unchanged at abaed5d
- human review (what I checked or corrected, or `none`): none yet; risks outside the criteria reported for the decision point — the `opencode.json` change bundled into 4eb0485 (protected, outside #20's Constraints) and the #20 session summary committed at 4bfa89c before QA PASS (candid, no false completion claim)

### 2026-10-18 — Engineer implements #15 stage E2 (install, run, test; protected targets proposed)

- date: 2026-10-18
- task/issue: issue #15, stage E2 (install, run, test), lifecycle step 3, after #20 closed
- agent role: Software Engineer (opencode software-engineer subagent, launched by the Orchestrator; entry appended by the Engineer, as its role file says)
- model: opencode/deepseek-v4.1-flash-free
- prompt or instruction given (or link to a file in `_docs/prompts/`): Orchestrator instruction to work the "E2. Install, run, test" and Constraints sections exactly; run `node`/`npm --version`, run `npm install --before=2026-10-18` in `frontend/` (pre-approved), add and verify the make targets, re-run the E1 scan, run Verify, commit non-protected changes only, and post an `Engineer:` comment; no key prompt file saved
- files changed: `frontend/package-lock.json` (new, 9130 insertions) committed in 71e5103; `frontend/README.md` ("Make targets" section and dev-server host/port; Services layer untouched) committed in 99781ee; this entry. Protected `Makefile` (frontend-install/start/stop/test plus the all-tests `test` target), `agent-kit.conf` (`TEST_CMD="make test"`) and `AGENTS.md` (Install/Run/Test/Verify lines) edited in the working tree only — NOT committed; their exact diffs are in the Engineer comment on #15. Git-ignored: `.scratch/issue15-e2-smoke.py`, `.scratch/issue15-e2-engineer-comment.md`. GitHub: Engineer comment on #15
- verification (tests run, reviewer verdict): `node --version` v24.22.0, `npm --version` 11.19.1. `npm install --before=2026-10-18` exit 0 (523 packages; `--before` accepted as written, no fallback). `git diff 0dd108a:frontend-lovable/package.json HEAD:frontend/package.json` prints nothing. `make frontend-install` (`npm ci`) exit 0; `make frontend-test` and `make test` exit 0 with 2 files / 10 tests passed; `.scratch/issue15-e2-smoke.py` `/login` and `/` both HTTP 200 with no backend; `make frontend-stop` stopped only the recorded PID and with no PID file printed "frontend is not running" and stopped nothing; no vite process left (`pgrep -af vite`). E1 scan `.scratch/issue15_scan.py` over 95 committed `frontend/` files: 1 hit, the fictional demo password `triage-demo` at `mockData.ts:3` (harmless; the fixture with `owner@gmail.com`, `ghp_`+36, `sk-`+32 is flagged). `make verify` (default, since origin/main; with the working-tree `TEST_CMD`) PASS, no warnings: tests 10/10, whitespace PASS, weakened tests none (the four `frontend-bolt/` paths are the approved E1 deletions). QA not run
- human review (what I checked or corrected, or `none`): none yet; the decision point covers the three protected diffs and the choices named in the comment (all-tests target named `test`; `npm --prefix frontend test`; direct Vite binary with explicit `--host 127.0.0.1 --port 5173`; port 5173; the extra Verify-line update)

### 2026-10-18 — QA checks #15 stage E2 (first run PASS discarded; clean re-run PASS at 352ff95)

- date: 2026-10-18
- task/issue: issue #15, stage E2 (install, run, test), lifecycle steps 4-5, two runs
- agent role: QA Engineer (two fresh opencode qa-engineer subagents, launched by the Orchestrator; entries appended by the Orchestrator after `make assert-clean` per the role's write-only-`.scratch/` limit) and Orchestrator (`opencode.json` decision)
- model: opencode/deepseek-v4.1-flash-free
- prompt or instruction given (or link to a file in `_docs/prompts/`): Orchestrator instruction to check the E2 criteria and Constraints at `e3de014`, then (after the tree was dirtied) a second instruction to re-check at `352ff95` with the tree kept clean; no key prompt file saved
- files changed: none in the repo by QA (`.scratch/` scripts only). GitHub: QA PASS comments 6250209261 (first run, discarded) and 6250305366 (kept re-run). `opencode.json` (protected) gained two allow rules (`git ls-files*`, `pgrep *`) during the first run — the tool persisted them; the human approved keeping them and they were committed as `352ff95` with `HUMAN_APPROVED=1`
- verification (tests run, reviewer verdict): first run QA PASS at `e3de014` (10/10 tests, `/login` HTTP 200 on `127.0.0.1:5173`, secrets scan clean), but `make assert-clean` then FAILED on ` M opencode.json`, so the verdict was discarded per process step 5. Re-run at `352ff95`: QA PASS, all E2 criteria — node v24.22.0, npm 11.19.1, `make frontend-install` (`npm ci`) exit 0, `make frontend-test` and `make test` 10/10, `frontend-start` recorded PID 47104 and `frontend-stop` stopped only it, `/login` and `/` HTTP 200 on port 5173 with no backend, `package.json` unchanged since `0dd108a`, 95-file secrets scan clean and its fixture flagged, no path outside the allowed list for any #15 commit (`352ff95` is the unrelated opencode.json commit). `make verify` and `make verify BASE=0dd108a` both PASS, no warnings. After the re-run `make assert-clean` PASS and HEAD unchanged at `352ff95`
- human review (what I checked or corrected, or `none`): the human chose "Keep and commit" for the two `opencode.json` allow rules (they were the tool persisting an approved read-only check); committed with `HUMAN_APPROVED=1` as `352ff95`

### 2026-10-18 — #15 E2 decision point, follow-up comment, and close

- date: 2026-10-18
- task/issue: issue #15, lifecycle steps 7-9 (decision point, cleanup and summary, close)
- agent role: Orchestrator; Software Engineer (one follow-up comment)
- model: opencode/deepseek-v4.1-flash-free
- prompt or instruction given (or link to a file in `_docs/prompts/`): human decisions at the E2 decision point (post the Engineer follow-up comment naming the remaining E2 commits; then update the summary, clean up and close); no key prompt file saved
- files changed: this entry; `_session-summaries/issue-015-frontend-choice.md` (updated for E2). GitHub: Engineer follow-up comment 6250367523 naming `c95643b` and `e3de014` (and noting `352ff95` is the unrelated `opencode.json` commit). No code changed
- verification (tests run, reviewer verdict): QA PASS at `352ff95` stands; `make assert-clean` PASS; `make clean-scratch` run (`.scratch/` emptied; no process was running)
- human review (what I checked or corrected, or `none`): the human chose to post the Engineer follow-up comment (recommended) rather than accept QA's judgement on the strict E1(c) reading

### 2026-10-18 — Independent review of OpenCode's work on #20 and #15 stage E2

- date: 2026-10-18
- task/issue: issues #20 and #15 (stage E2 and close-out), independent review at HEAD `ac06c02`
- agent role: Reviewer (independent review, asked by the human)
- model: Claude Code, claude-opus-5-5
- prompt or instruction given (or link to a file in `_docs/prompts/`): the human's request for an independent review of OpenCode's work on #20 and #15; exact text not recorded
- files changed: `_docs/reviews/2026-10-18-review-issues-15-20.md` (new; committed 2026-10-19 with the entry below)
- verification (tests run, reviewer verdict): no tests run; read the issues, comments, diffs, Makefile, devcontainer recipe, push check, `verify.sh`, log entries and session summaries; checked the built container. Findings: 1 High (the push check will fail: no `install` target, and the `python:3.12` image has no Node), 2 Medium (corepack shims and unpinned nvm in the rebuilt container; QA ran in the build tool with no recorded exception), 4 Low, 8 not-recommended choices, 4 decisions for the human
- human review (what I checked or corrected, or `none`): none yet; the review's four decisions are open. Finding 3 was overtaken by the 2026-10-19 QA rule change (entry below)

### 2026-10-19 — QA independence rule changed

- date: 2026-10-19
- task/issue: no issue; process rule change in `_docs/agent-team.md` § QA independence
- agent role: Orchestrator
- model: Claude Code, claude-opus-5-5
- prompt or instruction given (or link to a file in `_docs/prompts/`): the human's instruction to replace the QA rule with: "QA always runs in a fresh, isolated context—either in a separate session or via an isolated subagent, never within the context that performed the build. A different tool or model is preferred; when it isn't available, QA proceeds anyway and the QA comment and log entry record which tool and model did the build and the QA."
- files changed: `_docs/agent-team.md` (new rule quoted word for word; the earlier rule, its #12 exception and the three recorded uses kept under "Earlier rule (until 2026-10-19)"; fresh-run and Assert-clean paragraph moved under the new rule); this entry; `_docs/reviews/2026-10-18-review-issues-15-20.md` committed unchanged
- verification (tests run, reviewer verdict): `git diff --check` clean; grep confirmed the rule appears in no role file, `process.md`, `AGENTS.md` or other protected file
- human review (what I checked or corrected, or `none`): the human set the rule wording and approved this commit

### 2026-10-19 — File issue #32 from review errors 1 and 2

- date: 2026-10-19
- task/issue: issue #32 (new), from errors 1 and 2 of `_docs/reviews/2026-10-18-review-issues-15-20.md`
- agent role: Orchestrator
- model: Claude Code, claude-opus-5-5
- prompt or instruction given (or link to a file in `_docs/prompts/`): the human asked for an issue covering the two errors that the OpenCode agent can work, with priority and order assessed
- files changed: this entry. GitHub: issue #32 created (body edited once to replace an issue-number placeholder with #32). Not groomed; the PM grooms it first
- verification (tests run, reviewer verdict): none; read the push check (`pre-push` lines 23, 29 and 45), the Makefile and `verify.sh` to confirm the facts in the issue
- human review (what I checked or corrected, or `none`): none yet

### 2026-10-19 — Implement issue #32 Part A proposal and Part B devcontainer fix

- date: 2026-10-19
- task/issue: issue #32, Part A (push check `install` target and `frontend-test` guard; protected-file diffs proposed) and Part B (pin nvm, remove corepack shims)
- agent role: Software Engineer
- model: opencode/deepseek-v4.1-flash-free
- prompt or instruction given (or link to a file in `_docs/prompts/`): Orchestrator instruction to read `AGENTS.md`, the Engineer role file and issue #32, implement Part A as protected-file diffs (not edits) and Part B with option (b) `corepack disable`, commit only non-protected paths, run `make frontend-install`/`make test`/`make verify`, and post an `Engineer:` comment; no key prompt file saved
- files changed: `.devcontainer/devcontainer.json` (adds `"nvmVersion": "0.40.8"`) and `.devcontainer/setup.sh` (pins the node bin path and runs `corepack disable`), edited and staged; the commit needs `HUMAN_APPROVED=1` and was left for the orchestrator/human. `_docs/ai-usage-log.md` (this entry) and `_session-summaries/issue-032-push-check-and-devcontainer.md`. `Makefile` and `AGENTS.md` (protected) were not edited; their exact proposed diffs are in the `Engineer:` comment on #32. `.devcontainer/devcontainer-lock.json` unchanged. Git-ignored `.scratch/issue-32.json`, `.scratch/issue32-makefile-test/`, `.scratch/proposed-AGENTS.md`
- verification (tests run, reviewer verdict): `make frontend-install` (`npm ci`) exit 0, 518 packages, `frontend/package-lock.json` unchanged; `make test` 2 files / 10 tests passed; `make verify` PASS, no warnings (tests 10/10, whitespace PASS, weakened tests none; the four `frontend-bolt/` deletions are approved). Scratch guard test with the proposed Makefile and no `frontend/node_modules` printed `frontend/node_modules is missing: run make install first` and exited 1; `grep -E '^install[[:space:]]*::?'` matched the proposed target; `make help` listed `install`; `jq . .devcontainer/devcontainer.json` valid; `bash -n .devcontainer/setup.sh` clean. Current container: the four corepack shims still exist, `corepack --version` 0.36.0, node bin dir `drwxrwsr-x vscode nvm`, `nvm --version` 0.40.8. Post-rebuild checks not run; QA not run
- human review (what I checked or corrected, or `none`): none yet; the `.devcontainer/` commit is pending human approval and rebuild, and the protected diffs are pending the Orchestrator's approved commit

### 2026-10-19 — Close out issue #32 after QA PASS and the human's gated push

- date: 2026-10-19
- task/issue: issue #32, lifecycle steps 4-9 (QA, assert-clean, decision point, cleanup and close)
- agent role: Orchestrator; QA engineer (fresh isolated subagent)
- model: opencode/deepseek-v4.1-flash-free (build and QA; QA ran in a fresh isolated subagent, per the 2026-10-19 QA rule)
- prompt or instruction given (or link to a file in `_docs/prompts/`): the human's "check issues and continue", then the gate output pasted into the session; no key prompt file saved
- files changed: `_session-summaries/issue-032-push-check-and-devcontainer.md` (final state); this entry. GitHub: Orchestrator comments 6270008516 and 6271319915; issue #32 closed at the end of this close-out
- verification (tests run, reviewer verdict): QA PASS at `eb2e64b`, all Part A and Part B criteria (rebuilt-container checks: no `yarn`/`yarnpkg`/`pnpm`/`pnpx`, nvm `0.40.8`, node `v24.22.0`, npm `11.19.1`, uv `0.13.1`, `make install verify` PASS). `make assert-clean` PASS before the close-out edits and HEAD unchanged at `eb2e64b`. Human gate in the clean clone: `sandbox/main` and HEAD at `eb2e64b`; `node:24.22.0-bookworm` pulled (digest `sha256:14078204b6bb268c107ceff6d3c43f45a888105e5c2b18b14c32b3409d93a1b0`); `command -v bash git make node npm` printed `/usr/bin/bash`, `/usr/bin/git`, `/usr/bin/make`, `/usr/local/bin/node`, `/usr/local/bin/npm`; the gated push ran `make -C . install verify` (npm ci 518 packages, 10/10 tests, whitespace PASS, weakened tests none), printed `VERIFY: PASS`, and pushed `c1896e4..eb2e64b main -> main`. `make verify` after the close-out edits; `make assert-clean` and `make clean-scratch` at close-out
- human review (what I checked or corrected, or `none`): the human approved the protected diffs and the `.devcontainer/` commit, rebuilt the container, set `AGENT_PUSH_CHECK_IMAGE=node:24.22.0-bookworm`, and ran the real gated push

### 2026-10-19 — Groom issue #21 and resolve the `.npmrc` ownership decision

- date: 2026-10-19
- task/issue: issue #21 (grooming only)
- agent role: PM (subagent); Orchestrator relaying the human's decision
- model: opencode/deepseek-v4.1-flash-free
- prompt or instruction given (or link to a file in `_docs/prompts/`): Orchestrator instructions to groom #21 against the task template and to apply the human's option 1 for `frontend/.npmrc`; no key prompt file saved
- files changed: none in the repo. GitHub: issue #21 body rewritten twice; PM comments 6270448389 and 6271129779
- verification (tests run, reviewer verdict): read-only checks only: `git status --short` clean at `eb2e64b`; `make tool-versions` (node `v24.22.0`, npm `11.19.1`, uv `0.13.1`, python3 `3.12.15`, `docker: missing`); `make frontend-test` 2 files / 10 tests passed; a `.scratch/` audit found 46 `frontend/src/components/ui/` files, exactly 4 imported outside that folder, and 10 `it(` tests; Lovable, network and lockfile greps. No product code changed; no implementation
- human review (what I checked or corrected, or `none`): the human chose option 1: #21 adds `frontend/.npmrc` with `min-release-age=1`; #33 hardening D later appends `ignore-scripts=true`

### 2026-10-19 — Implement issue #21 frontend clean-up

- date: 2026-10-19
- task/issue: issue #21
- agent role: Software Engineer
- model: opencode/deepseek-v4.1-flash-free
- prompt or instruction given (or link to a file in `_docs/prompts/`): Orchestrator instruction to read `AGENTS.md`, the Engineer role file and issue #21, implement the clean-up, gather build evidence for the three render-mode options, propose (not edit) the protected-file diffs, run `make verify` and return the render-mode decision question; no key prompt file saved
- files changed: commits `c816d51` and `e65448e`. Removed `frontend/bun.lock`, `frontend/bunfig.toml`, `frontend/AGENTS.md`, `frontend/.lovable/project.json`, `frontend/src/lib/lovable-error-reporting.ts` and 42 unused `frontend/src/components/ui/*.tsx`; added `frontend/.npmrc` (`min-release-age=1`); rewrote `frontend/vite.config.ts` (explicit plugins, interim render target), `frontend/package.json`, `frontend/package-lock.json` (pruned), `frontend/README.md`, `frontend/src/routes/__root.tsx` (Lovable error reporting, `twitter:site` and Google Fonts links out) and `frontend/src/styles.css` (system font stacks). `Makefile` and `AGENTS.md` were not edited; the proposed `frontend-build` diff is in the `Engineer:` comment. `_docs/ai-usage-log.md` (this entry), `_session-summaries/issue-021-frontend-cleanup.md`. Git-ignored `.scratch/audit_frontend.py`, `.scratch/issue-21.json`, `.scratch/issue-21-comment.md`, `.scratch/node-build-{start,stop}.sh`
- verification (tests run, reviewer verdict): `make frontend-install` (`npm ci`) exit 0 (390 packages, down from 518) and leaves the lockfile unchanged; `npm --prefix frontend config get min-release-age` prints `1`; `make frontend-test` 2 files / 10 tests passed (unchanged baseline); `make verify` PASS (tests 10/10, whitespace PASS, weakened tests none); Lovable refused-case grep has exactly one hit (README provenance); `npm i`/`npm install` grep in README has no hits; network grep hits only `src/services/mockData.ts` and `src/server.ts` (kept while the render mode is undecided). Build evidence: SPA mode (`spa: { enabled: true }` + `preview.host`) builds `dist/client` 548K (shell `_shell.html`) + `dist/server` 196K; nitro `node-server` builds `.output` 2.0M (`server/index.mjs` + `public` 544K) and served the app on `127.0.0.1:3100` (title `Findings — VulnTriage`); plain TanStack Router + Vite builds `dist` 512K with `index.html` (main bundle 305 kB vs 342 kB). All three spike configs and outputs were deleted; `git status --short` clean. QA not run
- human review (what I checked or corrected, or `none`): none yet; the render-mode decision, the protected `Makefile` diff and QA are open

### 2026-10-19 — Finalize issue #21 render mode: plain TanStack Router + Vite

- date: 2026-10-19
- task/issue: issue #21 — apply the human's render-mode decision (option 3: plain TanStack Router + Vite, Orchestrator comment 6276301196) on top of `25c9b68`
- agent role: Software Engineer
- model: opencode/deepseek-v4.1-flash-free
- prompt or instruction given (or link to a file in `_docs/prompts/`): Orchestrator instruction to read `AGENTS.md`, the Engineer role file, issue #21 and the human's decision comment, then implement exactly: `tanstackRouter` in `vite.config.ts`, add `frontend/index.html` and `frontend/src/main.tsx`, delete the server files, remove unused dependencies, keep the 10 tests, verify the build serves from `frontend/dist/` and return the final state; no key prompt file saved
- files changed: commit `e367e49`. `frontend/vite.config.ts` (`tanstackStart` → `tanstackRouter({ target: "react", autoCodeSplitting: true })`, other plugins/aliases/dedupe/env/lightningcss/tailwind/tsconfig paths kept); added `frontend/index.html` and `frontend/src/main.tsx`; deleted `frontend/src/server.ts`, `frontend/src/lib/error-capture.ts`, `frontend/src/lib/error-page.ts`, `frontend/src/start.ts`; removed `@tanstack/react-start` and `nitro` from `frontend/package.json` and pruned `frontend/package-lock.json`; `frontend/src/routeTree.gen.ts` regenerated (dropped the `@tanstack/react-start` module augmentation); `frontend/README.md` records the render mode and the `frontend/dist/` output. `frontend/src/routes/__root.tsx` and the route files were not changed. `Makefile`, `AGENTS.md`, `agent-kit.conf` and `opencode.json` not touched. `_docs/ai-usage-log.md` (this entry), `_session-summaries/issue-021-frontend-cleanup.md`
- verification (tests run, reviewer verdict): `npm --prefix frontend run build` exit 0, writes `frontend/dist/index.html` (963 bytes) and `frontend/dist/assets/` (main bundle `index-Mqk3KKZ8.js` 305233 bytes), git-ignored; `.scratch/serve_check.py` served `frontend/dist` with `python3 -m http.server` on `127.0.0.1:8137` and `GET /` returned HTTP 200 (963 bytes, `#root` present) and the main JS asset returned HTTP 200 (305233 bytes), then it stopped only its own server process; `make install` (`npm ci`) exit 0, 351 packages, lockfile stable across two runs (sha256 unchanged); `make frontend-test` 2 files / 10 tests passed; `make test` 10 passed; `make verify` PASS (tests 10/10, whitespace PASS, weakened tests none). Refused cases re-checked: no `@lovable.dev` in `frontend/src`/`vite.config.ts`/`vitest.config.ts`/`package.json`; `grep -rni lovable frontend` has exactly one hit (README provenance); no `npm i`/`npm install` in `frontend/README.md`; `frontend/.npmrc` is exactly `min-release-age=1` and `npm --prefix frontend config get min-release-age` prints `1`; no dependency added (only the two removed); network grep now hits only `frontend/src/services/mockData.ts` (the `src/server.ts` exception has ended). QA not run
- human review (what I checked or corrected, or `none`): none yet; the Orchestrator applies the approved `Makefile` and `AGENTS.md` diffs after this confirmation, then QA runs

### 2026-10-19 — Apply the approved #21 protected changes, run QA and close #21

- date: 2026-10-19
- task/issue: issue #21, lifecycle steps 7-9 (decision point, protected-change commit, QA, cleanup and close)
- agent role: Orchestrator; QA engineer (fresh isolated subagent)
- model: opencode/deepseek-v4.1-flash-free (build and QA; QA ran isolated, per the 2026-10-19 QA rule)
- prompt or instruction given (or link to a file in `_docs/prompts/`): the human's decisions — render mode option 3, approve the `Makefile` `frontend-build` target and the one `AGENTS.md` Build line, record the decision on #21, note `frontend/dist/` in `frontend/README.md`, end the session after #21 without starting #22, and do not use `uptime` unless a task requires it; no key prompt file saved
- files changed: commit `682c69f` (protected `Makefile` `frontend-build` target + `.PHONY` entry, and the one `AGENTS.md` Build line; committed alone with `HUMAN_APPROVED=1`); this entry; `_session-summaries/issue-021-frontend-cleanup.md` finalized. GitHub: Orchestrator comments 6276301196 (decisions) and the close comment; issue #21 closed
- verification (tests run, reviewer verdict): `make frontend-build` exit 0 and writes `frontend/dist/index.html` (963 bytes); `make verify` PASS at `682c69f` (10/10 tests, whitespace PASS, weakened tests none); QA PASS at `682c69f` (all acceptance criteria and refused cases; `frontend/dist` served HTTP 200; the source app rendered in jsdom from login through demo sign-in to findings; protected diff only the approved two files; `agent-kit.conf` unchanged); `make assert-clean` PASS and HEAD unchanged at `682c69f`; `make clean-scratch` run. QA risks outside the criteria: `__root.tsx` `shellComponent` renders `<html>` inside `#root` (React hydration warning); the built `index.html` has no stylesheet link (runtime-injected CSS, FOUC without JS); `vite-tsconfig-paths` Vite 8 warning; `package.json` name `tanstack_start_ts`; `682c69f` bundles two protected files in one commit
- human review (what I checked or corrected, or `none`): the human approved the render mode (option 3) and the protected changes, directed that `frontend/README.md` record the `frontend/dist/` path, and asked to end the session after #21 (no #22) and not to use `uptime` again unless a task requires it

### 2026-10-19 — Senior-engineer review of #21 and #32; review #34; file #35

- date: 2026-10-19
- task/issue: review of the opencode work on closed issues #21 and #32; review of follow-up #34; file the push-check plan-mode follow-up (#35)
- agent role: Orchestrator (senior-engineer review at the human's request)
- model: Claude Code / claude-opus-5-5
- prompt or instruction given (or link to a file in `_docs/prompts/`): the human asked for a senior-engineer review of the opencode agent's work on #21 and #32, scaled down to save usage; then to review the follow-up issues; then approved posting the review and filing the missing follow-up; no key prompt file saved
- files changed: this entry only. GitHub: review comment on #34 (6277799291), new issue #35 ("Push check: plan mode (AGENT_PUSH_CHECK_PLAN=1) completes the push without checking"), link comment on #32 (6277802711). Git-ignored `.scratch/issue-21.json`, `.scratch/issue-32.json`, `.scratch/issue-34-review.md`, `.scratch/issue-prepush-plan.md`
- verification (tests run, reviewer verdict): read-only review; no build, test or `make verify` run. Read the #21 and #32 issue bodies and comments, the #32 diffs (`7207911`, `eb2e64b`), `frontend/src/routes/__root.tsx`, `frontend/index.html` and `frontend/src/main.tsx` at HEAD, and `pre-push` lines 120-140. Verdicts: #32 sound (minor: `setup.sh` repeats the Node version in a hardcoded path); #21 clean-up sound, but the render-mode switch left the Start `shellComponent` (`<html>` inside `#root`) and no stylesheet link in `index.html`, which QA noted and the close-out deferred (now #34). Found `pre-push` plan mode exits 0 after printing the plan, so the push goes through unchecked (now #35). #34 review: six points, mainly the `head()`/`HeadContent` contradiction, the leftover `?url` CSS import, and no check method for the React warning criterion. Permission review: rule deviations in this session were two inline `python3 -I -c` commands (to print issue JSON) and raw `sed`/`tail` reads instead of the read tool; whether any stopped for approval was not recorded
- human review (what I checked or corrected, or `none`): the human approved posting the #34 review and filing #35

### 2026-10-19 — Check the #21/#32 permission reviews; build the permission review into the agent kit

- date: 2026-10-19
- task/issue: check whether the opencode sessions for #21 and #32 followed the AGENTS.md permission review rule (added in `fbc2a5b`), then make the rule part of the role and close-out steps
- agent role: Orchestrator (review at the human's request)
- model: Claude Code / claude-opus-5-5
- prompt or instruction given (or link to a file in `_docs/prompts/`): the human asked whether the opencode agent did the permission review, then asked to build it into the process now for long-term efficiency; no key prompt file saved
- files changed: commit `d0884f6` (protected, `HUMAN_APPROVED=1`, approved by the human in this session): `_docs/agent-kit/templates/session-summary.md` (new Permission review section), `_docs/agent-kit/procedures/session-summary.md`, `_docs/agent-kit/process.md` (step 8 bullet, step 9 close condition, definition of done), `_docs/agent-kit/team/pm.md`, `_docs/agent-kit/team/qa-engineer.md`, `_docs/agent-kit/team/software-engineer.md` (a "commands that stopped for approval" line in each role comment). This entry. Git-ignored `.scratch/perm_notes.py` (read-only)
- verification (tests run, reviewer verdict): read-only check with `.scratch/perm_notes.py` over the #21 and #32 issue comments, plus grep of both session summaries. #21: PM and Engineer comments had permission notes; QA and Orchestrator comments did not; the summary section (`eab3ee9`) had the three groups but no settings proposal, and left out the PM's report that `gh issue edit 21` ran without a prompt although `opencode.json:49` sets it to `ask` (cause not found; `.opencode/agents/pm.md` sets no bash rule). #32: no role comment or summary section had a permission review; the session likely started before `fbc2a5b`. The rule appeared nowhere in `_docs/agent-kit/` before `d0884f6`. `git diff --check` clean; `make verify` not run (documentation-only change)
- human review (what I checked or corrected, or `none`): the human said the `4895a12` `rg` allow rule was their own change, not the agent's; the human approved the exact protected diff before the commit

### 2026-10-19 — Implement issue #22 services layer

- date: 2026-10-19
- task/issue: issue #22, "Frontend services layer ready for a real API" (groomed; human decisions: services-owned persisted session, idempotent `logout`, two optional owner fields)
- agent role: Software Engineer
- model: opencode/deepseek-v4.1-flash-free
- prompt or instruction given (or link to a file in `_docs/prompts/`): Orchestrator instruction to read `AGENTS.md`, `_docs/agent-kit/team/software-engineer.md`, `_docs/agent-kit/procedures/verify.md`, issue #22 and its PM comment, implement every acceptance criterion and refused case, commit at logical milestones, run `make verify`, post an `Engineer:` comment, and return the commits, verify result, criteria evidence, choices, proposed AGENTS.md changes, spec notes and approval-stopped commands; no key prompt file saved
- files changed: commit `759735a` (14 files): `frontend/src/services/{types,index,mockService,mockData}.ts`; `frontend/src/components/vt/AuditTrail.tsx` (new) and `Badges.tsx`; `frontend/src/routes/{login,_authed,_authed.assets.index,_authed.assets.new,_authed.findings.$findingId,_authed.findings.$findingId_.accept}.tsx`; `frontend/src/test/vulntriage.test.tsx`; `frontend/README.md`. This entry in `_docs/ai-usage-log.md` (the issue expected `frontend/**` only; the log is the project rule's record). No `Makefile`, protected file, `package.json` or lockfile change. Git-ignored `.scratch/issue-22.json`
- verification (tests run, reviewer verdict): `make frontend-test` 2 files / 35 tests passed; `make frontend-build` exit 0 (`frontend/dist/`, git-ignored); `frontend/node_modules/.bin/tsc --noEmit -p frontend/tsconfig.json` exit 0 (not a configured project check); `make verify` at `759735a` PASS WITH WARNINGS: tests 35/35, whitespace PASS, weakened tests 7 rewritten assertions, each replaced by a stronger typed assertion (2-arg `acceptRisk`; `ServiceError` code instead of generic throw; non-null `getFinding`; `isOwnerless` instead of `owner === null`; wire value `risk_accepted` instead of `risk accepted`). Refused cases re-checked: no `mockData`/`mockService` import in `routes/`, `components/`, `lib/`; only type-only deep imports of `@/services/...`; no `fetch(`/`axios`/`XMLHttpRequest`/`WebSocket` in `src/services`; `acceptRisk(` has only 2-arg calls; no `owner:` property in `src/`; no dependency added. QA not run
- human review (what I checked or corrected, or `none`): none yet; issue left open for QA. Commands that stopped for approval: none

### 2026-10-19 — Orchestrate issue #22 from grooming to close

- date: 2026-10-19
- task/issue: issue #22, "Frontend services layer ready for a real API" (PM grooming, Engineer implementation, QA check, decision point, cleanup and close)
- agent role: Orchestrator; PM, Software Engineer and QA Engineer (fresh isolated subagents)
- model: opencode/deepseek-v4.1-flash-free
- prompt or instruction given (or link to a file in `_docs/prompts/`): the human asked to check the issues and start #22 following `_docs/agent-kit/process.md`; answered the three grooming decisions (persisted service-owned session, idempotent `logout`, two optional owner fields) and the decision-point questions (approve both spec notes, the 10 → 35 test-count updates, no partial-owner follow-up, keep a session after a failed login). No key prompt file saved
- files changed: commit `9f742d2` (protected `_docs/specs.md`, human-approved, committed alone); commit `c85c6e8` (protected `AGENTS.md` and `agent-kit.conf`, human-approved, committed alone); this entry; `_session-summaries/issue-022-services-layer.md`. GitHub: PM comment 6278909287, Engineer comment 6279079561, QA PASS comment 6279190817, issue #22 closed
- verification (tests run, reviewer verdict): `make frontend-test` 35/35; `make verify` PASS WITH WARNINGS at `759735a` (7 changed-contract assertions rewritten stronger, each justified); QA independently PASS at `f790ddc` for all 34 criteria and refused cases; `make assert-clean` PASS and HEAD unchanged at `f790ddc`; `make clean-scratch` run
- human review (what I checked or corrected, or `none`): the human chose the three grooming options and approved the spec and protected test-count changes at the decision point

### 2026-10-19 — Senior review of closed issue #22

- date: 2026-10-19
- task/issue: issue #22, "Frontend services layer ready for a real API" (review after close)
- agent role: Orchestrator (senior engineering review)
- model: Claude Code, claude-opus-5-5
- prompt or instruction given (or link to a file in `_docs/prompts/`): the human asked for a review of opencode's finished #22 "as a senior engineer who still has a lot more review work this week to complete", then approved posting the follow-ups and this log entry. No key prompt file saved
- files changed: this entry. GitHub: comment on #25 (6279525860: an auth failure shows up as an empty findings/assets list; suggested redirect to `/login`, error states, no retry, one UI test) and on #23 (6279526319: the order in which errors are checked; whether owner fields are always present). Git-ignored `.scratch/issue-22.json`, `.scratch/comment-25.md`, `.scratch/comment-23.md`
- verification (tests run, reviewer verdict): read the diffs of `759735a`, `9f742d2`, `c85c6e8`, the current `frontend/src/services/{types,index,mockService}.ts`, and the PM, Engineer, QA and Orchestrator comments on #22; grep of the list routes' error handling. Verdict: approve, no reopen. Tests and `make verify` not re-run (QA and the orchestrator ran them at `f790ddc`)
- human review (what I checked or corrected, or `none`): the human approved posting both follow-up comments. Commands that stopped for approval: none

### 2026-10-19 — Review opencode's status analysis and record the roadmap

- date: 2026-10-19
- task/issue: no issue; review of opencode's project status and priority analysis, recorded as `_docs/roadmap.md`
- agent role: Orchestrator
- model: Claude Code, claude-opus-5-5
- prompt or instruction given (or link to a file in `_docs/prompts/`): the human pasted opencode's analysis and asked for agreements, disagreements and proposed changes, then asked to record the result as a working plan to review progress against. No key prompt file saved
- files changed: `_docs/roadmap.md` (new), `README.md` (link), this entry
- verification (tests run, reviewer verdict): checked opencode's claims against `_docs/planning-process.md`, `_docs/agent-kit/process.md`, `_docs/rubric.md`, `_docs/rubric-evidence.md`, `agent-kit.conf`, `.github/workflows/verify.yml`, the open issue list, #9, #26, #34 and recent CI runs (`55ad78c` success). Found the scope decision already made (2026-10-17) and the 7-point audit likely stale (Testing 1 and CI/CD 1 unconfirmed). No auditor run; tests not run
- human review (what I checked or corrected, or `none`): the human asked for the roadmap; the four open decisions in it are not yet answered. Commands that stopped for approval: none

### 2026-10-19 — Keep deadlines out of the roadmap

- date: 2026-10-19
- task/issue: no issue; follow-up to the roadmap entry above
- agent role: Orchestrator
- model: Claude Code, claude-opus-5-5
- prompt or instruction given (or link to a file in `_docs/prompts/`): the human decided that timelines and dates stay out of agent-facing docs because they can adversely affect the agents; the human controls timing. No key prompt file saved
- files changed: `_docs/roadmap.md` (deadline line replaced by "timing and scope trade-offs are the human's"; the deadline decision row removed), this entry
- verification (tests run, reviewer verdict): `git diff --check` clean; no tests run (docs only)
- human review (what I checked or corrected, or `none`): the human declined a proposed deadline edit, then approved this wording. Commands that stopped for approval: none

### 2026-10-19 — Link the roadmap from AGENTS.md

- date: 2026-10-19
- task/issue: no issue; follow-up to the roadmap entries above
- agent role: Orchestrator
- model: Claude Code, claude-opus-5-5
- prompt or instruction given (or link to a file in `_docs/prompts/`): the human approved the proposed one-line addition to `AGENTS.md` "Where to read more". No key prompt file saved
- files changed: protected `AGENTS.md` (commit `2efa508`, committed alone with `HUMAN_APPROVED=1`), this entry
- verification (tests run, reviewer verdict): `git diff --check` clean; no tests run (docs only)
- human review (what I checked or corrected, or `none`): the human approved the exact line shown in the session before it was written. Commands that stopped for approval: the `HUMAN_APPROVED=1 git commit` (intended)

### 2026-10-19 — Implement issue #13 README problem, functionality and expected behaviour

- date: 2026-10-19
- task/issue: issue #13, "README: describe the problem, functionality and expected behaviour (Problem Description, 1 → 2 points)" (groomed; PM comment made no repo changes and asked whether to file a follow-up for post-implementation README work)
- agent role: Software Engineer
- model: opencode/deepseek-v4.1-flash-free
- prompt or instruction given (or link to a file in `_docs/prompts/`): Orchestrator instruction to read `AGENTS.md`, `_docs/agent-kit/team/software-engineer.md`, `_docs/agent-kit/procedures/verify.md`, issue #13 and its latest PM comment, change only `README.md`, run Verify, commit with explicit paths, and append this entry; no key prompt file saved
- files changed: commit `1a000c2` (`README.md` only): added "The problem", "What VulnTriage does" and "Expected behaviour" sections, an explicit planning/not-implemented note, and expanded OSV.dev, CISA KEV, FIRST EPSS, LLM, MCP and n8n on first use; kept the planning and AI-workflow index. This entry in `_docs/ai-usage-log.md` (project rule). Git-ignored `.scratch/issue-13.json`, `.scratch/check_readme_13.py`
- verification (tests run, reviewer verdict): `make verify` before the log entry (README diff identical to `1a000c2`) PASS WITH WARNINGS: tests 2 files / 35 tests passed, whitespace PASS, weakened tests 7 rewritten assertions that predate this task (issue #22 test changes already in the unpushed range; this task changed no test). `.scratch/check_readme_13.py` PASS: every relative link resolves and all three required headings and fixed names are present. No QA run
- human review (what I checked or corrected, or `none`): none yet; issue left open for QA. Commands that stopped for approval: none

### 2026-10-20 — Close out issue #13

- date: 2026-10-20
- task/issue: issue #13, "README: describe the problem, functionality and expected behaviour (Problem Description, 1 → 2 points)"
- agent role: Orchestrator
- model: opencode/deepseek-v4.1-flash-free
- prompt or instruction given (or link to a file in `_docs/prompts/`): the human asked to check `_docs/roadmap.md` and start the next issue following `_docs/agent-kit/process.md`; no key prompt file saved
- files changed: `_session-summaries/issue-013-readme-problem-description.md` (new), `_docs/roadmap.md` (step 2 status and check-in line), this entry. Implementation `1a000c2` and the Engineer's log entry `e46fadf` were made by the Engineer
- verification (tests run, reviewer verdict): PM grooming, Engineer implementation and QA PASS were separate subagent runs. QA ran `make verify BASE=1be4f95` PASS (35 tests, whitespace PASS, no test files changed) and `make assert-clean` PASS at `e46fadf`. The orchestrator re-ran `make assert-clean` and confirmed HEAD stayed `e46fadf`. No auditor run
- human review (what I checked or corrected, or `none`): the human answered the decision point: do not file a README follow-up now, and no action on QA's minor findings. The roadmap records that step 2 started ahead of step 1 at the human's request. Commands that stopped for approval: none

### 2026-10-20 — Rubric evidence re-audit (roadmap step 1)

- date: 2026-10-20
- task/issue: roadmap step 1, "Refresh the rubric evidence"; re-audit `_docs/rubric.md` at HEAD `74e9cfc`
- agent role: Rubric Evidence Auditor
- model: opencode/deepseek-v4.1-flash-free
- prompt or instruction given (or link to a file in `_docs/prompts/`): Orchestrator instruction to read `AGENTS.md` and `.opencode/agents/rubric-auditor.md`, re-audit at HEAD `74e9cfc`, confirm Testing 1 (35 cases and passing), CI/CD 1 (`verify.yml` runs the tests on every PR) and Problem Description 2 (README after #13), open every linked file or output, update only `_docs/rubric-evidence.md` and append this entry; no key prompt file saved
- files changed: `_docs/rubric-evidence.md` (rewritten with the 2026-10-20 audit), this entry. No code or other file changed; not committed (orchestrator reviews and commits)
- verification (tests run, reviewer verdict): opened `_docs/rubric.md`, `README.md` at `74e9cfc`, `_docs/specs.md`, `_docs/agent-team.md`, `_docs/agent-kit/process.md`, `AGENTS.md`, `Makefile`, `agent-kit.conf`, `.github/workflows/verify.yml`, both frontend test files, `frontend/src/services/index.ts` and `mockService.ts`. Ran `make test`: 2 files / 35 tests passed (34 in `vulntriage.test.tsx` + 1 in `app-routing.test.tsx`). `gh run view 39344215807 --log` showed the verify workflow ran `make verify`, then "Tests (make test)", 35 passed and "VERIFY: PASS"; the run at `1be4f95` concluded `success`. `gh repo view`, `gh issue list`, `gh issue view 1`, `gh issue view 2`, `gh issue view 13`, `git ls-files`, `git show` and `gh pr list` confirmed the public tracker, the acceptance criteria and role comments, no backend/database/container/deploy/telemetry/alert/responder files, and no pull requests. Audited score 10/24 (was 7). Verdicts: Testing 1 CONFIRMED (PARTIAL 1); CI/CD 1 CONFIRMED (PARTIAL 1, no CD); Problem Description 2 CONFIRMED (MET 2). Criteria changed since 2026-10-17: Testing 0 -> 1, CI/CD 0 -> 1, Problem Description 1 -> 2. Other criteria unchanged: Application 0, Containerization 0, Deployment 0, Observability 0, Alerting 0, On-Call 0; Product Specification, Agent Team and Context Management remain 2
- human review (what I checked or corrected, or `none`): none yet; orchestrator to review and commit. Commands that stopped for approval: none

### 2026-10-20 — Roadmap check-in; groom #35 and #33

- date: 2026-10-20
- task/issue: roadmap steps 1, 2 and 6; grooming of #35 and #33. The roadmap step 6 grooming (#3-#8) was already posted before this session and was verified, not redone
- agent role: Orchestrator, with a Rubric Evidence Auditor subagent and two PM subagents
- model: opencode/deepseek-v4.1-flash-free
- prompt or instruction given (or link to a file in `_docs/prompts/`): the human asked whether #13 and step 6 were done, then approved starting step 1, grooming #35/#33 in parallel and updating the step 6 roadmap status. No key prompt file saved
- files changed: `_docs/roadmap.md` (commit `c15e4db`: steps 1-2 `done`, step 6 `doing` pending the batched decision, check-in line). Auditor commit `639b9a9` (`_docs/rubric-evidence.md`, `_docs/ai-usage-log.md`); the auditor's entry says "not committed", which its own commit `639b9a9` supersedes. Session summary `_session-summaries/planning-2026-10-20-rubric-refresh-and-grooming.md` and this entry. GitHub: PM rewrote and commented on #35 and #33; PM filed #36 (top-level agent-kit duplicate) and #37 (Claude Code settings asks). #17/#18 were groomed by another session at 00:29 UTC, not by this one
- verification (tests run, reviewer verdict): auditor ran `make test` (2 files, 35 tests passed) and read CI run 39344215807 (`success`); audited score 10/24 and confirmed Testing 1, CI/CD 1 and Problem Description 2. Orchestrator ran `make verify` after the roadmap edit: PASS WITH WARNINGS (35 tests, whitespace PASS, 7 pre-existing assertion rewrites from #22). `git diff --check` clean. No QA run for the grooming
- human review (what I checked or corrected, or `none`): none yet. Open: the batched #3-#8 decision, PM's two questions on #35 and one on #33, and whether PM should have filed #36/#37 before asking. Commands that stopped for approval: none

### 2026-10-20 — Implement issue #35 push-check plan mode

- date: 2026-10-20
- task/issue: issue #35, "Push check: plan mode (AGENT_PUSH_CHECK_PLAN=1) completes the push without checking (High)". Grooming answers applied: Q1 fix only `_docs/agent-kit` (top-level duplicate left to #36); Q2 plan mode blocks every push, including no-op, deletion-only and no-project pushes
- agent role: Software Engineer
- model: opencode/deepseek-v4.1-flash-free
- prompt or instruction given (or link to a file in `_docs/prompts/`): Orchestrator instruction to read `AGENTS.md`, `_docs/agent-kit/team/software-engineer.md`, `_docs/agent-kit/procedures/verify.md`, issue #35 and its comments (PM grooming plus the human's answers), implement the acceptance criteria, leave the protected changes uncommitted for human approval, run Verify, post an Engineer comment and append this entry; no key prompt file saved
- files changed: protected `_docs/agent-kit/environments/local-sandbox/pre-push` and `_docs/agent-kit/environments.md`, left uncommitted pending the human's approval of the exact diff; this entry in `_docs/ai-usage-log.md`. Git-ignored `.scratch/test-push-check-plan.sh` (evidence harness), `.scratch/pre-push-original` (pre-change hook for the non-plan comparison) and `.scratch/push-check-plan-results.txt` (harness output)
- verification (tests run, reviewer verdict): `make verify` PASS WITH WARNINGS: 2 test files / 35 tests passed, whitespace PASS, weakened tests 7 removed assertion lines that predate this issue (earlier unpushed frontend test changes; this issue changed no test files). `.scratch/test-push-check-plan.sh`: 10 cases, 0 failures (plan line per project, install/install::/none/comment/reinstall detection, working tree versus pushed commit, root fallback, no-new-commits, deletion-only, no-project, removed config, and non-plan byte-for-byte comparison against the original hook for unset/0/other and a failing gate). The sandbox denies `git push`, so the harness invoked the hook directly with git's pre-push stdin and recorded the local bare remote's refs before and after
- human review (what I checked or corrected, or `none`): none yet; the protected diff and its commit await the human's approval, and the human still needs to reinstall the hook in the clean clone and confirm with `cmp`. Commands that stopped for approval: none

### 2026-10-20 — Engineer proposal for issue #17 committed-alone check

- date: 2026-10-20
- task/issue: issue #17, "Pre-commit check: HUMAN_APPROVED=1 does not enforce \"committed alone\" for protected changes"; propose-only because `_docs/agent-kit/scripts/check-staged.sh` is protected
- agent role: Software Engineer
- model: opencode/deepseek-v4.1-flash-free
- prompt or instruction given (or link to a file in `_docs/prompts/`): Orchestrator instruction to read `AGENTS.md`, `_docs/agent-kit/team/software-engineer.md`, `_docs/agent-kit/procedures/verify.md` and #17, write the exact diff without editing protected files, test a copy in `.scratch/`, and post an Engineer comment; no key prompt file saved
- files changed: no tracked file; the proposed diff was returned to the orchestrator and is posted in Engineer comment 6280738052. Git-ignored `.scratch/test-check-staged.sh` and `.scratch/issue-17-repo` held the harness. This entry was appended by the orchestrator
- verification (tests run, reviewer verdict): throwaway-repo matrix 9/9 PASS (six required cases, both rename directions, forbidden `.env`, whitespace); `make verify BASE=1d31aac` PASS (35 tests, whitespace PASS) on the unmodified tree. The proposal was not applied by this role
- human review (what I checked or corrected, or `none`): the human approved the exact diff in this session; the orchestrator applied it and committed `64308d7`. Commands that stopped for approval: none

### 2026-10-20 — QA for issue #17

- date: 2026-10-20
- task/issue: issue #17, committed state
- agent role: QA Engineer
- model: opencode/deepseek-v4.1-flash-free
- prompt or instruction given (or link to a file in `_docs/prompts/`): Orchestrator instruction to check #17 against its criteria at the committed state, run Verify and the throwaway matrix, and post a QA verdict; a re-check was requested after a concurrent session moved HEAD; no key prompt file saved
- files changed: none. QA comments 6281018092 (at `64308d7`) and 6281387668 (re-check at `df72298`). This entry was appended by the orchestrator
- verification (tests run, reviewer verdict): PASS at both commits. `make verify BASE=1d31aac` PASS (35 tests, whitespace PASS, no weakened tests); matrix 12/12 in `.scratch/qa-17-recheck.sh`; `make assert-clean` PASS at `df72298`; script blob unchanged `3712882`
- human review (what I checked or corrected, or `none`): the human chose to file follow-ups #39 (quoted filenames) and #40 (repo-root paths). Commands that stopped for approval: none

### 2026-10-20 — Orchestrator close-out for issue #17

- date: 2026-10-20
- task/issue: issue #17, protected change commit and close-out
- agent role: Orchestrator
- model: opencode/deepseek-v4.1-flash-free
- prompt or instruction given (or link to a file in `_docs/prompts/`): the human chose roadmap step 6, answered the batched #3-#8 decisions, chose script-only enforcement for #17, and approved the exact protected diff; no key prompt file saved
- files changed: `_docs/agent-kit/scripts/check-staged.sh` (commit `64308d7`, protected, committed alone with `HUMAN_APPROVED=1` after approval); approval record comment 6280810952; `_session-summaries/issue-017-committed-alone.md` (commit `199f4b7`); this entry; issues #38, #39 and #40 filed by PM. No other repository change
- verification (tests run, reviewer verdict): QA PASS at `df72298`; `make verify BASE=1d31aac` PASS; `make assert-clean` PASS; approval record matches `git show` and blob `3712882`. The first QA run overlapped with the concurrent #35 session and was re-run at the stable HEAD after the human paused that session
- human review (what I checked or corrected, or `none`): the human approved the exact diff, chose script-only enforcement, chose to leave the duplicate folder for #38, approved filing #39/#40, and paused the concurrent orchestration. Commands that stopped for approval: none

### 2026-10-20 — Engineer proposal for issue #18 approval record

- date: 2026-10-20
- task/issue: issue #18, "Record human approvals of protected changes so the exact approved text can be confirmed"; propose-only because all four changed files are protected
- agent role: Software Engineer
- model: opencode/deepseek-v4.1-flash-free
- prompt or instruction given (or link to a file in `_docs/prompts/`): Orchestrator instruction to read `AGENTS.md`, the engineer role, `verify.md`, #18 and its comments, draft the exact diffs without editing tracked files, check them against the criteria, and post Engineer comments; no key prompt file saved
- files changed: no tracked file; diffs returned to the orchestrator and posted in comments 6281798553 (three files) and 6281870795 (the template, after the human chose to include it). Drafts and checks in `.scratch/propose/`. This entry was appended by the orchestrator
- verification (tests run, reviewer verdict): `git apply --check` passed; all four paths match `PROTECTED`; `make verify BASE=ea257c9` PASS (35 tests, whitespace PASS); no docs tests exist, so the criterion check was a read of the drafted text
- human review (what I checked or corrected, or `none`): the human chose to include the template in the same protected commit and approved the exact four-file text; the orchestrator applied it and committed `efae1ea`. Commands that stopped for approval: none

### 2026-10-20 — QA for issue #18

- date: 2026-10-20
- task/issue: issue #18, committed state and its first approval record
- agent role: QA Engineer
- model: opencode/deepseek-v4.1-flash-free
- prompt or instruction given (or link to a file in `_docs/prompts/`): Orchestrator instruction to check every criterion at `efae1ea`, compare the posted record with the stated `git show`, check paths/blob IDs/parent, run Verify and assert-clean, and post a QA verdict; no key prompt file saved
- files changed: none. QA comment 6282208055. This entry was appended by the orchestrator
- verification (tests run, reviewer verdict): PASS. `make verify BASE=ea257c9` PASS (35 tests, whitespace PASS, no weakened tests); posted diff and `git show` output both 8394 bytes and `cmp` clean; `Paths` and all four blob IDs match; single parent; all four paths `PROTECTED`; refused cases rejected by the written rule; `make assert-clean` PASS at `efae1ea`
- human review (what I checked or corrected, or `none`): the QA notes outside the criteria are the documented documentation-only limit and an `index`-line difference in draft snippets; no action requested. Commands that stopped for approval: none

### 2026-10-20 — Orchestrator close-out for issue #18

- date: 2026-10-20
- task/issue: issue #18, protected docs commit and close-out
- agent role: Orchestrator
- model: opencode/deepseek-v4.1-flash-free
- prompt or instruction given (or link to a file in `_docs/prompts/`): the human approved the four protected paths (including the template) and approved the exact diff; no key prompt file saved
- files changed: `AGENTS.md`, `_docs/agent-kit/procedures/asking-the-human.md`, `_docs/agent-kit/process.md`, `_docs/agent-kit/templates/AGENTS.md.template` (commit `efae1ea`, protected, committed alone with `HUMAN_APPROVED=1`); approval record comment 6282041221; `_docs/roadmap.md` (commit `8bc389e`: step 5 done, step 6 answers recorded, decisions 1 and 3 resolved); `_session-summaries/issue-018-approval-record.md` (commit `6b953f5`); this entry. No other repository change
- verification (tests run, reviewer verdict): QA PASS at `efae1ea`; `make verify BASE=ea257c9` PASS; `make assert-clean` PASS; its own approval record passed the diff, path, blob, parent and `PROTECTED` checks
- human review (what I checked or corrected, or `none`): the human chose to include the template and approved the exact diff; QA's outside-criteria notes need no action. Commands that stopped for approval: none

### 2026-10-20 — Engineer drafts for spec issues #3-#8

- date: 2026-10-20
- task/issue: issues #3, #6, #4, #5, #7, #8 (roadmap step 6), drafted as cumulative `_docs/specs.md` patches
- agent role: Software Engineer
- model: opencode/deepseek-v4.1-flash-free (project default in `opencode.json`)
- prompt or instruction given (or link to a file in `_docs/prompts/`): orchestrator instruction to draft each issue's spec change from its recorded batched answers without editing tracked files; no key prompt file saved
- files changed: no tracked file; patches in `.scratch/spec-draft/`; Engineer comments 6284843229 (#3), 6284856636 (#6), 6284857967 (#4), 6284859024 (#5), 6284863547 (#7), 6284865043 (#8). This entry was appended by the Claude Code orchestrator from those comments
- verification (tests run, reviewer verdict): each comment reports the patch applies cleanly in order and the cumulative scratch spec passes its checks
- human review (what I checked or corrected, or `none`): the human approved each exact diff before its commit. Commands that stopped for approval: none (all six comments)

### 2026-10-20 — Orchestrator commits for spec issues #3-#8

- date: 2026-10-20
- task/issue: roadmap step 6, six protected spec commits and approval records
- agent role: Orchestrator
- model: opencode/deepseek-v4.1-flash-free
- prompt or instruction given (or link to a file in `_docs/prompts/`): the human's approval of each exact spec diff; no key prompt file saved
- files changed: `_docs/specs.md` in `45f6fa6` (#3), `999fd88` (#6), `e52a07c` (#4), `e0a60ac` (#5), `b03539b` (#7), `fdc7b51` (#8), each committed alone with `HUMAN_APPROVED=1`; approval records 6285069644, 6285087536, 6285106147, 6285123424, 6285146604, 6285163520. This entry was appended by the Claude Code orchestrator; the OpenCode session stopped before logging
- verification (tests run, reviewer verdict): the record for #8 was compared with `git show` by a `.scratch/` script (PASS); every record was later re-checked by QA
- human review (what I checked or corrected, or `none`): approved each diff. Commands that stopped for approval: not collected, because the session was interrupted

### 2026-10-20 — QA for spec issues #3, #6 and #4

- date: 2026-10-20
- task/issue: issues #3, #6, #4
- agent role: QA Engineer
- model: opencode/deepseek-v4.1-flash-free
- prompt or instruction given (or link to a file in `_docs/prompts/`): orchestrator instruction to check each issue's criteria and approval record at its commit and post a verdict; no key prompt file saved
- files changed: none. QA comments 6285218980 (#3), 6285234570 (#6), 6286250358 (#4). This entry was appended by the Claude Code orchestrator
- verification (tests run, reviewer verdict): PASS for all three; `make verify` PASS (35 tests); approval records byte-identical to `git show`; each reports `make assert-clean` PASS at `fdc7b51`
- human review (what I checked or corrected, or `none`): outside-criteria risks went to the step 6 decision point (option 1, #41). Commands that stopped for approval: none

### 2026-10-20 — QA reruns for spec issues #5, #7 and #8

- date: 2026-10-20
- task/issue: issues #5, #7, #8; the OpenCode QA runs stopped before posting, so these are fresh runs
- agent role: QA Engineer
- model: claude-opus-5-5 (Claude Code `qa-engineer` subagent)
- prompt or instruction given (or link to a file in `_docs/prompts/`): orchestrator instruction to check criteria and approval record, run Verify, not reuse the partial `.scratch/qa-5/`, and post a verdict; no key prompt file saved
- files changed: none. QA comments 6286739493 (#5), 6286726338 (#7), 6286723784 (#8)
- verification (tests run, reviewer verdict): PASS for all three; `make verify` with each parent as `BASE` PASS (35 tests); records byte-identical to `git show`; orchestrator `make assert-clean` PASS, HEAD `fdc7b51` unchanged
- human review (what I checked or corrected, or `none`): outside-criteria risks went to the step 6 decision point (option 1, #41). Commands that stopped for approval: none

### 2026-10-20 — PM follow-up #41 from the #3-#8 QA risks

- date: 2026-10-20
- task/issue: step 6 decision point, option 1
- agent role: PM
- model: claude-opus-5-5 (Claude Code `pm` subagent)
- prompt or instruction given (or link to a file in `_docs/prompts/`): orchestrator instruction to file one groomed issue for the spec contradictions and gaps, list the Stage 2 details as step 7 inputs, and comment once on #23; no key prompt file saved
- files changed: no tracked file; created #41; comment 6286808327 on #23
- verification (tests run, reviewer verdict): none; #41 asks the human decisions D1-D4 before implementation
- human review (what I checked or corrected, or `none`): the human chose option 1. Commands that stopped for approval: none

### 2026-10-20 — Orchestrator close-out for spec issues #3-#8

- date: 2026-10-20
- task/issue: roadmap step 6 close-out after the OpenCode orchestrator stopped
- agent role: Orchestrator
- model: claude-opus-5-5 (Claude Code)
- prompt or instruction given (or link to a file in `_docs/prompts/`): the human asked to finish the interrupted task; no key prompt file saved
- files changed: `_session-summaries/planning-2026-10-20-spec-review-3-8.md`, `_docs/roadmap.md` (step 6 done, #41 noted, check-in line), this log; closed #3-#8
- verification (tests run, reviewer verdict): checked the state left behind (clean tree, HEAD `fdc7b51`, no verdict on #5/#7/#8, no PID files); `make assert-clean` PASS after the QA reruns
- human review (what I checked or corrected, or `none`): the human chose option 1 at the decision point. Commands that stopped for approval: none

### 2026-10-20 — QA for issue #35 (first run)

- date: 2026-10-20
- task/issue: issue #35, committed state `df72298`
- agent role: QA Engineer
- model: opencode/deepseek-v4.1-flash-free
- prompt or instruction given (or link to a file in `_docs/prompts/`): orchestrator instruction to check every criterion and post a verdict; no key prompt file saved
- files changed: none. QA comment 6281291470. This entry was appended by the Claude Code orchestrator
- verification (tests run, reviewer verdict): FAIL on criterion 10 only (no approval comment); criteria 1-9, 11, 12 PASS; independent 83-check harness 0 failures; `make verify BASE=4454518` PASS
- human review (what I checked or corrected, or `none`): none. Commands that stopped for approval: none

### 2026-10-20 — Orchestrator close-out for issue #35

- date: 2026-10-20
- task/issue: issue #35 (roadmap step 3), after the OpenCode orchestrator stopped
- agent role: Orchestrator, with a QA Engineer re-check and a PM follow-up as Claude Code subagents
- model: claude-opus-5-5 (Claude Code); the earlier commit `df72298` and free-form note 6281324989 were made by the OpenCode orchestrator (opencode/deepseek-v4.1-flash-free)
- prompt or instruction given (or link to a file in `_docs/prompts/`): the human asked to finish the interrupted session; no key prompt file saved
- files changed: approval record 6287006555 (built and checked by a `.scratch/` script against the approval request and `git show`); correction comment 6287127239; QA PASS 6287037242; PM created #42; `_session-summaries/issue-035-push-check-plan-mode.md`, `_docs/roadmap.md` (step 3 done, check-in line), this log; `make clean-scratch` ran; closed #35
- verification (tests run, reviewer verdict): QA re-check PASS (34 record checks, 0 failures; #35 paths unchanged since `df72298`; `make verify BASE=4454518` PASS); `make assert-clean` PASS at `48cbb9d`
- human review (what I checked or corrected, or `none`): the human approved the diff before `df72298` and chose option 1 at the decision point. Commands that stopped for approval: none

### 2026-10-20 — Review of the step 3/6 close-out commits and roadmap check-in

- date: 2026-10-20
- task/issue: roadmap check-in after `48cbb9d` and `b1ab1e5`
- agent role: Orchestrator
- model: claude-opus-5-5 (Claude Code)
- prompt or instruction given (or link to a file in `_docs/prompts/`): the human asked to review the recent commits and update the roadmap; no key prompt file saved
- files changed: `_docs/roadmap.md` (unscheduled follow-ups #36-#40 and #42 placed under "Later", #38/#36 note, decision 4, score table from the 2026-10-20 audit, check-in line), this log
- verification (tests run, reviewer verdict): compared the roadmap with `gh issue list --state all`; `make verify` PASS WITH WARNINGS at `b1ab1e5` (35 tests; the removed-assertion warning comes from earlier frontend commits since `origin/main`)
- human review (what I checked or corrected, or `none`): none yet. Commands that stopped for approval: none

### 2026-10-20 — Roadmap reprioritised toward product work

- date: 2026-10-20
- task/issue: roadmap reshuffle after the human said the project was sidetracked by safeguards
- agent role: Orchestrator
- model: claude-opus-5-5 (Claude Code)
- prompt or instruction given (or link to a file in `_docs/prompts/`): the human asked to weigh priorities toward VulnTriage itself, not the agent kit or dev container, and reshuffle the roadmap; no key prompt file saved
- files changed: `_docs/roadmap.md` (priority rule, `deferred` status, step 4 (#33) deferred to "Later", #41 opens step 7, decision 4 withdrawn, new off-track signal, check-in line), this log
- verification (tests run, reviewer verdict): none (documentation only)
- human review (what I checked or corrected, or `none`): the human set the direction; the edited roadmap is not yet reviewed. Commands that stopped for approval: none

### 2026-10-20 — Decisions for #41 and roadmap decision 2

- date: 2026-10-20
- task/issue: #41 D1-D4 and roadmap decision 2 (#31)
- agent role: Orchestrator
- model: claude-opus-5-5 (Claude Code)
- prompt or instruction given (or link to a file in `_docs/prompts/`): the human asked for more context to make the decisions; no key prompt file saved
- files changed: comments 6287579005 (#41) and 6287579525 (#31); `_docs/roadmap.md` (decision 2 resolved, step 16 unblocked, check-in line), this log
- verification (tests run, reviewer verdict): none (decisions recorded only)
- human review (what I checked or corrected, or `none`): the human chose option 1 for D1, D2, D3 and decision 2 in a multiple-choice question; D4 unanswered. Commands that stopped for approval: none
- follow-up, same day: the human chose D4 option 1 (the recommended status line); recorded in #41 comment 6287964999

### 2026-10-20 — #41 step 3: proposed spec diff

- date: 2026-10-20
- task/issue: #41 lifecycle step 3 (implementation as a proposed diff to the protected `_docs/specs.md`)
- agent role: Engineer (subagent of the orchestrator)
- model: claude-opus-5-5 (Claude Code)
- prompt or instruction given (or link to a file in `_docs/prompts/`): the orchestrator's step 3 task: draft D1-D4 (option 1 each) and D5 option 1 against the PM's groomed criteria (comment 6288008663) in a scratch copy, without editing or committing the spec; no key prompt file saved
- files changed: none tracked except this log. Scratch only: `.scratch/spec-41/specs.md` (draft), `.scratch/spec-41/specs-41.patch` (headers retargeted to `_docs/specs.md`), `.scratch/spec-41/check_41.py` (read-only check), `.scratch/spec-41/comment-41.md`; Engineer comment 6288084947 on #41 with the full diff
- verification (tests run, reviewer verdict): `check_41.py` 61/61 automated checks pass, plus a manual read of the status-setting sentences and external-claim lines it prints; `git apply --check` on the patch passes; `make verify` PASS WITH WARNINGS (35 tests; the removed-assertion warning comes from earlier frontend commits since `origin/main`). No QA or human review yet
- human review (what I checked or corrected, or `none`): none yet; D5 (`repository unavailable`) awaits the human at diff approval. Commands that stopped for approval: none

### 2026-10-20 — #41 protected spec commit and approval record

- date: 2026-10-20
- task/issue: #41, after the human approved the exact diff
- agent role: Orchestrator
- model: claude-opus-5-5 (Claude Code)
- prompt or instruction given (or link to a file in `_docs/prompts/`): the human approved the diff as shown and chose D5 option 1; no key prompt file saved
- files changed: `_docs/specs.md` in `1445ca5`, committed alone with `HUMAN_APPROVED=1`; approval record comment 6288541138; this log
- verification (tests run, reviewer verdict): the applied diff was compared byte for byte with the approved patch before staging (`cmp`, identical), and again after the commit by `.scratch/spec-41/build_record.py` (one parent, only `_docs/specs.md`, `git show` identical to the patch); QA not yet run
- human review (what I checked or corrected, or `none`): approved the exact diff and D5 option 1. Commands that stopped for approval: none

### 2026-10-20 — QA and close-out for #41

- date: 2026-10-20
- task/issue: #41 lifecycle steps 4-9
- agent role: QA Engineer (Claude Code `qa-engineer` subagent), then Orchestrator
- model: claude-opus-5-5 (Claude Code)
- prompt or instruction given (or link to a file in `_docs/prompts/`): orchestrator instruction to check the groomed criteria and the approval record, run Verify with `BASE=c77a437`, and post a verdict; no key prompt file saved
- files changed: QA comment 6288587511; decision-point comment 6289212246; `_session-summaries/issue-041-spec-fixes-from-qa-risks.md` (`71aa176`); `_docs/roadmap.md` (step 7 doing, check-in line), this log; `make clean-scratch` ran; closed #41
- verification (tests run, reviewer verdict): QA PASS (own script 81/82, the one miss a gap in its prefix list, cross-checked); `make verify BASE=c77a437` PASS (35 tests); `make assert-clean` PASS at `6a33ba0`, HEAD unchanged
- human review (what I checked or corrected, or `none`): at the decision point the human chose to send QA risks 1-3 to the step 7 issue. Commands that stopped for approval: none

### 2026-10-20 — Plan for Claude Code cloud sessions

- date: 2026-10-20
- task/issue: none (human request: plan how to use Claude Code cloud sessions for this project)
- agent role: Orchestrator
- model: claude-opus-5-5 (Claude Code), with a `web-fetch` subagent reading the Claude Code on the web and cloud environments docs
- prompt or instruction given (or link to a file in `_docs/prompts/`): the human asked for the most efficient method, the repo adjustments and step-by-step instructions in `_docs`; no key prompt file saved
- files changed: `_docs/cloud-sessions.md` (new; proposal, protected-file changes listed but not made), this log
- verification (tests run, reviewer verdict): none; the doc marks undocumented details `VERIFY:` for a trial session. Repo facts checked: `.claude/settings.json` denies `git push *`, `guard_git.py` blocks push, `make issue-dump` uses `gh issue view`, CI uses the runner's default Node
- human review (what I checked or corrected, or `none`): none yet. Commands that stopped for approval: none
- follow-up, same day: the human chose not to depend on cloud credit; `_docs/cloud-sessions.md` is marked an optional, deferred reference

### 2026-10-20 — Docker options and the human-in-the-loop runbook

- date: 2026-10-20
- task/issue: none directly (feeds step 7 D1 and #31); human request for the cost of Docker in the sandbox, then step-by-step instructions for the human
- agent role: Orchestrator
- model: claude-opus-5-5 (Claude Code)
- prompt or instruction given (or link to a file in `_docs/prompts/`): the human asked for a technical cost breakdown, chose option A (Compose service containers, agent has no Docker control), and asked for instructions for the human who runs containers outside the sandbox; no key prompt file saved
- files changed: `_docs/docker-runbook.md` (new), `_docs/cloud-sessions.md` (status line), this log
- verification (tests run, reviewer verdict): none (documentation). Facts checked: the repo is public (`gh repo view`), the agent token can read Actions runs (`gh run list`), `verify.yml` runs on every push. Setup hours are estimates, not measured
- human review (what I checked or corrected, or `none`): the human chose option A. Commands that stopped for approval: none
