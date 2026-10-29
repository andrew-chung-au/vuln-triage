# Permission tooling verification (#271)

**Date:** 2026-10-29
**Scope:** the permission-tooling change tracked by issue #271: safe read-only allows, guarded issue writes, the five-group permission review, the optional cloud-session push module, and the top-level `agent-kit/` mirror.
**Commits:** `e174151` (settings and guarded Make targets), `8778092` (docs, guard and kit copy), and the unprotected mirror commit that adds this file.

## What was checked

- `make check-scripts`: PASS. Bash syntax for the kit scripts, hooks and `pre-push`; Python parse for the hooks and scripts; `jq empty` for `.claude/settings.json` and `opencode.json`.
- `make verify BASE=51bcf57`: PASS. 89 frontend tests, 563 backend tests (14 deselected), 1638 responder tests; frontend type check PASS; whitespace PASS; no test files changed.
- `.scratch/check-guard.sh`: the mirrored `guard_git.py` allowed `git push -u origin claude/test` only with `AGENT_KIT_CLOUD_PUSH=1`, `CLAUDE_CODE_REMOTE=true` and the checked-out `claude/test` branch. The other three cases exited 2: no module, module outside a cloud session, and a push form other than `-u origin <current branch>`.
- `make permission-report SINCE=9eb4071` and `SINCE=51bcf57`: ran read-only during the change; the five groups and the older three-group summaries were read, and the prompt log was read when present. No settings change was proposed from the counts.
- `make branches`, `make ci LIMIT=3`, `make file-at`, and the `make issue-comment` path: validated wrappers ran; `DRY_RUN=1` posted nothing; the secret scan refused a test body with a match; invalid `CONTAINS`, `LIMIT`, `REF`, `FILE`, dash-led and single-quote values were refused. Details and the comment links are in the approval records on #271.

## What is not checked

- A real `git push` from a Claude Code cloud session. The guard's four decision paths are checked against a scratch repository; no push, remote or cloud session was used.
- The live OpenCode prompt behaviour. OpenCode loads permission rules at session start, so the rules changed in `opencode.json` are not active in the session that wrote them. The human must restart OpenCode and check the rules in its permissions view.
- The top-level `agent-kit/` mirror is for comparison, not a second executable kit. It carries the permission docs, the guard, the settings, the cloud-session module and `scan-issue-body.sh`, but not `permission-report.py` or the earlier project-only differences in `check-staged.sh`, `verify.sh`, `pre-push`, `asking-the-human.md` and `verify.md`. The project copy in `_docs/agent-kit/` is the one `make` targets run. The duplication remains tracked by #36 and #38.

## Human steps

1. Restart OpenCode so the new `opencode.json` rules load.
2. Read the settings and Makefile diff, then merge and push from the clean clone.
3. The next permission sweep runs `make permission-report SINCE=9eb4071` (sweep 1's baseline) and decides the recorded approvals; this issue's approvals are in its session summary.
