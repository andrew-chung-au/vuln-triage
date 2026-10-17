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
