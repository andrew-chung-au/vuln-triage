# Issues #60, #37 and #61: permission settings (Engineer part)

**Date:** 2026-10-22
**Spec version:** 97893c1

This summary covers the Engineer step only. The PM grooming, the human's approvals, the protected commits, QA and the closing are the orchestrator's and are not recorded here.

## What changed and why

- #60 and #37 (one proposed `.claude/settings.json` diff): remove `Bash(gh api repos/*)` from `allow`, add `Bash(gh api *)` to `ask`, add `Edit(/.devcontainer/**)`, `Edit(/.githooks/**)`, `Edit(/.github/**)` and `Edit(/.vscode/**)` to `ask`. Not applied; the diff is in the #60 comment.
- #61 (proposed protected diffs, not applied): a read-only `make permission-report SINCE=<commit>` target and `_docs/agent-kit/scripts/permission-report.py`; the `AGENTS.md` Commands line and Permission review rule; the session-summary template and procedure no longer ask for per-session settings proposals; a new `_docs/agent-kit/procedures/permission-sweep.md`; one sentence in `process.md` step 8.
- Unprotected files edited or created: `_docs/cloud-sessions.md` (line 46), `_docs/permission-sweeps.md` (new).

## Files created or modified

- `_docs/cloud-sessions.md`: line 46 only (uncommitted).
- `_docs/permission-sweeps.md`: new (uncommitted).
- `_docs/ai-usage-log.md`: one entry appended (uncommitted).
- This summary (uncommitted).
- GitHub: Engineer comments 6330334016 (#60), 6330335550 (#37, pointer), 6330334233 (#61).
- Proposed, not applied: `.claude/settings.json`, `Makefile`, `_docs/agent-kit/scripts/permission-report.py` (new), `AGENTS.md`, `_docs/agent-kit/process.md`, `_docs/agent-kit/templates/session-summary.md`, `_docs/agent-kit/procedures/session-summary.md`, `_docs/agent-kit/procedures/permission-sweep.md` (new).

## Decisions made by the human

- Per the Orchestrator comment 6330251791: #60 option 2; one commit for #60 and #37; #61 limited to the target and template/rule change; three-session threshold; last sweep recorded in `_docs/permission-sweeps.md`; summaries only. The exact protected diffs were not yet approved when this was written.

## Mismatches with the spec or design docs

- none

## Commands to validate

- **Verify:** `make verify` was not run in this step; no committed file changed and the protected diffs are not applied yet. Run it after the approved commits.
- Scratch checks (read-only): `python3 -m json.tool` on the proposed settings; a rule-shape script (`.scratch/check_rules.py`); `git apply --check` on all three diff files; the regression script `.scratch/test_permission_report.py` (all refusal, allow and fixture cases passed; output in the #61 comment).
- Not verified: a live Claude Code prompt for the `gh api` and `Edit` rules (needs a session started after the settings commit).

## Proposed AGENTS.md changes

- The Commands line and Permission review rule in the #61 comment.

## Temporary changes

- Scratch copies and scripts under `.scratch/`; `make clean-scratch` was not run (the orchestrator needs them for the proposed diffs until the commits are made).
- No processes started; no system configuration changed.

## Permission review

- Read-only (propose allowing): none known; no command stopped for approval.
- Writes to the record (keep asking): `make issue-comment` on #60, #37 and #61 (allowed target under `make *`).
- Risky (propose denying): none

## Interruptions

- none

## Unrelated problems noticed but not fixed

- The #60 comment contains one stray duplicated output line in the rule-check block (a filtered line left a repeated `by ['gh api *']`); comments cannot be edited.

## Follow-ups for the next session

- Orchestrator: get the human's approval for the diffs, apply them, and commit with `HUMAN_APPROVED=1` (suggested: settings alone; `Makefile` + script; rule and docs), then post the approval records on #60/#37 (same commit) and #61.
- Human: after the settings commit, in a new session, run the live prompt checks for #60 and #37.
- File the first-sweep issue after #60 and #37 land, and put its number in `_docs/permission-sweeps.md`.
