# Issue #020: Dev container: Node.js and uv available to agents (blocks #15 part E2)

**Date:** 2026-10-18
**Spec version:** d3a8f11

## What changed and why

- Session check: no `_docs/specs.md` commits since the last summary's version (`d3a8f11`), so no backlog review was needed.
- PM groomed #20 (its first grooming) and pinned the previously-open values. It found the filer's example feature id `node:1` was stale (current major is `node:2`), that Node 20 is EOL so it can't be the "LTS line" criterion 1 wants, and that the lockfile behaviour was open.
- The human answered four grooming decisions in-session; the PM applied the approved body edits to #20 and filed the Docker/Compose follow-up #31, linked from #20's out-of-scope.
- The Engineer implemented the recipe and stopped before the `.devcontainer/` commit: the pre-commit hook gates `.devcontainer/` behind `HUMAN_APPROVED=1`. The change is staged in the working tree, uncommitted.
- The Engineer could not regenerate `.devcontainer/devcontainer-lock.json`: this container has no devcontainer CLI (nor node/npx/docker). Raised as a decision question instead of committing a stale digest.
- Mid-session, on a direct human instruction (no issue), the Orchestrator added a `make tool-versions` target (node, npm, uv, python3, docker, or `<tool>: missing`) and a "Tool versions" line in AGENTS.md's Commands section. Committed in its own protected commit, which also carried the human's pre-existing AGENTS.md Project-rules edits.

## Files created or modified

- `.devcontainer/devcontainer.json` (uncommitted, working tree): adds `"ghcr.io/devcontainers/features/node:2": { "version": "24.22.0", "pnpmVersion": "none" }`; removes the duplicate `remoteEnv.PATH`, keeping `${containerEnv:PATH}:/home/vscode/.local/bin:/home/vscode/.opencode/bin`.
- `.devcontainer/setup.sh` (uncommitted, working tree): adds `pipx install uv==0.13.1`.
- `AGENTS.md` (protected): proposed Environment-line change, not edited, not committed (below).
- GitHub: #20 body edited to the groomed text; PM comment 6247960494 (grooming) and 6248923707 (decisions applied); new issue #31.
- `.scratch/` (git-ignored): `issue-20-check.py`, `issue-20-tooling.sh`, `issue-20-pipx-writable.py`, and the PM's drafts. Kept for the post-rebuild work.
- `Makefile` (protected): new `tool-versions` target. `AGENTS.md` (protected): Commands "Tool versions" line; committed with the human's pre-existing Project-rules edits.
- This summary.

## Decisions made by the human

- Node pin `24.22.0` (Active LTS; option 1 of 3).
- uv installed with `pipx install uv==0.13.1` in `setup.sh` (option 1; no third-party feature).
- File the Docker/Compose follow-up now: #31.
- Apply the PM's proposed body edits to #20 as drafted.
- The human runs the `.devcontainer/` commit commands themselves (keeps `HUMAN_APPROVED=1` with the human), then rebuilds.
- Approved committing the `tool-versions` change (`Makefile` + `AGENTS.md`) with `HUMAN_APPROVED=1`, including the pre-existing AGENTS.md Project-rules edits.
- Lockfile (criterion 4): option 1 with checks — after the rebuild, show the `devcontainer-lock.json` diff before committing; it must add only the new feature entries with their versions and digests and leave `github-cli` unchanged. If the rebuild did not update it, stop and tell the human, who will regenerate it with the devcontainer CLI on their machine (option 2).

## Mismatches with the spec or design docs

- None. `_docs/specs.md` does not cover toolchain versions; this is infrastructure that makes the lockfiles named in US-2 producible.

## Commands to validate

- **Verify:** `make verify BASE=HEAD` — PASS WITH WARNINGS, the only warning being the no-`TEST_CMD` one (project still in planning, no code). Also PASS over all unpushed work since `origin/main`.
- Static check: `python3 .scratch/issue-20-check.py` — all criteria PASS on the working-tree diff, including the refused-case patterns.
- Runtime (after the human rebuilds): `node --version` (`v24.22.0`), `npm --version` (`11.19.1`), `uv --version` (`uv 0.13.1`) — QA's job, not yet run.

## Proposed AGENTS.md changes

One line, protected, not yet approved or applied:

```
- **Environment:** local sandbox (dev container; no Docker). The recipe installs Node.js `24.22.0` and uv `0.13.1`. GitHub token: read-only code (you can't push); read and write issues (you can post comments and close issues). See `_docs/agent-kit/environments.md`.
```

## Temporary changes

None by the agent. The Engineer installed nothing and started nothing. The `.devcontainer/` change is a system change the human applies: they run the commit and then rebuild the container. Undo: revert the commit and rebuild.

## Interruptions

None. The Engineer stopped on purpose before the gated commit and returned an approval request plus the lockfile decision question (relayed to the human).

## Unrelated problems noticed but not fixed

- The issue's own example feature id `node:1` was stale (current `node:2`); corrected in the applied body.
- #31 was filed without a priority/blocked label because the repo has no such labels; its status lives in the title and body.

## Follow-ups for the next session

- The human commits `.devcontainer/devcontainer.json` and `.devcontainer/setup.sh` with `HUMAN_APPROVED=1`, then rebuilds the container.
  - `git add .devcontainer/devcontainer.json .devcontainer/setup.sh`
  - `HUMAN_APPROVED=1 git commit -m "Issue #20: install pinned Node.js 24.22.0 and uv 0.13.1 in the dev container"`
- After the rebuild: inspect the `devcontainer-lock.json` diff (only the new node entries added, `github-cli` unchanged) and show it to the human before committing it; if the rebuild did not update it, stop and tell the human (they will regenerate it with the CLI).
- Then append the usage-log entries, post the Engineer comment, and run QA: `node --version`, `npm --version`, `uv --version`, and the non-interactive `make`-shell check.
- Only after QA PASS, the decision point applies the AGENTS.md Environment line with `HUMAN_APPROVED=1`.
- `make clean-scratch` was **not** run: #20 is still open and the `.scratch/` check scripts are needed after the rebuild.
