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
