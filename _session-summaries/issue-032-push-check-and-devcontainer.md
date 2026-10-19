# Issue #032: Push check install target and dev container corepack/nvm fixes

**Date:** 2026-10-19
**Spec version:** d3a8f11

## What changed and why

- Part A (protected, proposed only): the Engineer did not edit `Makefile` or `AGENTS.md`. The exact diffs are in the `Engineer:` comment on #32. They add `install: frontend-install`, add `install` to `.PHONY`, add the `frontend-test` guard with the fixed message, replace the stale `Makefile:2` wording, and update the AGENTS.md Install line, Dependencies line and one Project gotcha.
- The guard was tested in `.scratch/issue32-makefile-test/` with a copy of the proposed Makefile and `frontend/package.json` but no `frontend/node_modules`: it printed the fixed message and exited 1. `grep -E '^install[[:space:]]*::?'` matches, and `make help` lists `install`.
- Part B: `.devcontainer/devcontainer.json` adds `"nvmVersion": "0.40.8"` to the node feature options. `.devcontainer/setup.sh` prepends the pinned node bin directory to `PATH` and runs `corepack disable` once Node is on it, without `sudo`. `.devcontainer/devcontainer-lock.json` is unchanged. The container rebuild is the human's step.
- Runtime checks in the current (pre-rebuild) container: the four corepack shims still exist in `/usr/local/share/nvm/versions/node/v24.22.0/bin/`, `corepack` resolves there (version 0.36.0), the directory is `drwxrwsr-x vscode nvm`, and `nvm --version` is `0.40.8`. The post-rebuild checks (shims gone, pinned versions) are not claimed.

## Files created or modified

- `.devcontainer/devcontainer.json` (edited; commit needs `HUMAN_APPROVED=1`, left staged for the orchestrator/human).
- `.devcontainer/setup.sh` (edited; same commit condition).
- `.devcontainer/devcontainer-lock.json` (unchanged, confirmed with `git diff`).
- `_docs/ai-usage-log.md` (this task's entry).
- `_session-summaries/issue-032-push-check-and-devcontainer.md` (this file).
- `Makefile` and `AGENTS.md` (protected; not edited; exact proposed diffs in the #32 comment).
- `.scratch/` (git-ignored): `issue-32.json`, `issue32-makefile-test/` and `proposed-AGENTS.md`.
- GitHub: `Engineer:` comment on #32.

## Decisions made by the human

- Part B: option (b), `corepack disable` in `.devcontainer/setup.sh`, recorded in the PM comment on 2026-10-19.
- Follow-up #33 was filed for the remaining #15/#20 review findings and hardening items B–D.
- The Orchestrator applies the approved protected `Makefile`/`AGENTS.md` diffs with `HUMAN_APPROVED=1`; the human reviews the `.devcontainer/` diff, commits it with `HUMAN_APPROVED=1`, and rebuilds.

## Mismatches with the spec or design docs

- None. #32 is tooling/process, and `_docs/specs.md` does not cover it.

## Commands to validate

- **Install:** `make frontend-install` — exit 0 (518 packages); `make install` does not exist until the protected Makefile diff is applied, and then runs the same `npm --prefix frontend ci`.
- **Test:** `make test` — 2 files, 10 tests passed.
- **Verify:** `make verify` — PASS, no warnings (tests 10/10, whitespace PASS, weakened tests none; the four `frontend-bolt/` deletions are approved).
- Guard test: `make -C .scratch/issue32-makefile-test frontend-test` — printed `frontend/node_modules is missing: run make install first`, exit 1.
- Static checks: `jq . .devcontainer/devcontainer.json` — valid; `bash -n .devcontainer/setup.sh` — clean; `grep` for the install target — matches.
- Post-rebuild (QA, not run): each of `yarn`, `yarnpkg`, `pnpm`, `pnpx` absent in a fresh non-interactive `sh`; `node --version` `v24.22.0`; `npm --version` `11.19.1`; `uv --version` `uv 0.13.1`; `nvm --version` `0.40.8`; `make install` and `make verify` pass.

## Proposed AGENTS.md changes

Protected, not edited. The exact diff:

```diff
--- a/AGENTS.md
+++ b/AGENTS.md
@@ -25,7 +25,7 @@

 <!-- Every slot is a make target or "none". To be filled in when the project is scaffolded. -->

-- **Install:** `make frontend-install`: installs the frontend dependencies from `frontend/package-lock.json` (`npm ci` in `frontend/`).
+- **Install:** `make install`: installs all dependencies; today that's the frontend's `npm ci` from `frontend/package-lock.json`.
 - **Run:** `make frontend-start` / `make frontend-stop`: starts/stops the frontend Vite dev server on `127.0.0.1:5173` (log: `.scratch/frontend.log`; `frontend-stop` stops only the PID `frontend-start` recorded).
 - **Test (all):** `make test`: runs the frontend tests (`make frontend-test`, vitest, the 10 cases in `frontend/src/test/`).
 - **Test (one file):** `none`
@@ -40,7 +40,7 @@

 - **Environment:** local sandbox (dev container; no Docker). The recipe installs Node.js `24.22.0` and uv `0.13.1`. GitHub token: read-only code (you can't push); read and write issues (you can post comments and close issues). See `_docs/agent-kit/environments.md`.
 - **Branching:** commit directly to `main`; the human reviews and pushes from the clean clone.
-- **Dependencies:** no stack scaffolded yet; ask before adding any dependency.
+- **Dependencies:** the frontend's dependencies are locked in `frontend/package-lock.json`; adding one still needs asking.
 - **Session summaries:** `_session-summaries/`, named `issue-<NNN>-<short-name>.md` for issue work and `planning-<YYYY-MM-DD>-<short-name>.md` for planning.

## Project rules
@@ -73,6 +73,7 @@
 ## Project gotchas

- There is no Docker in this container, so anything needing Docker Compose must wait for a codespace or a Compose-based container recipe (see `_docs/agent-kit/environments.md`).
+- `make verify` needs `make install` first. The push check needs an image with Node (set `AGENT_PUSH_CHECK_IMAGE`; see #32).

 <!-- SHARED: from _docs/agent-kit/templates/AGENTS.md.template. Change it there first, then copy it here. -->

```

## Temporary changes

- None by the Engineer beyond the repo edits: no rebuild, no `sudo`, no global configuration change, no package manager change. `make frontend-install` created the git-ignored `frontend/node_modules`.
- The `.devcontainer/` commit is held for the pre-commit hook's `HUMAN_APPROVED=1` gate; undo is to revert the commit and rebuild.

## Interruptions

- None.

## Unrelated problems noticed but not fixed

- `opencode.json` already had a working-tree change before this task (`"rg *": "allow"`). It was not made by this run, not edited further, and not staged or committed. It must not be bundled into the #32 commits.

## Follow-ups for the next session

- Orchestrator: apply the approved `Makefile` and `AGENTS.md` diffs with `HUMAN_APPROVED=1`, in their own protected commit(s), before QA.
- Human: review the `.devcontainer/` diff against the clean clone's copy, commit it with `HUMAN_APPROVED=1`, and rebuild the container.
- QA after the rebuild: run the running-container checks for the four shims, `node`/`npm`/`uv`, `nvm --version`, and `make install verify`.
- Then run `make clean-scratch`; `.scratch/` files are not kept.
