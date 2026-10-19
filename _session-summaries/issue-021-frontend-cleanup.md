# Issue #021: Frontend clean-up — remove Lovable coupling and unused code

**Date:** 2026-10-19
**Spec version:** d3a8f11

## What changed and why

- The frontend no longer depends on the app-builder platform: `frontend/src/lib/lovable-error-reporting.ts` and its call site are gone, along with `frontend/AGENTS.md`, `frontend/.lovable/`, the `twitter:site` meta and the two Google Fonts links (replaced by system font stacks).
- `frontend/vite.config.ts` is an explicit config (tailwindcss, vite-tsconfig-paths, tanstackStart, react; `VITE_*` injection, `@` alias, dedupe, `lightningcss`); the shared preset import is gone. The production render target is left out until the human picks one of the three options.
- 42 unused `src/components/ui/*.tsx` files and the packages only they used are removed; `frontend/bun.lock` and `frontend/bunfig.toml` are gone, and `frontend/.npmrc` carries `min-release-age=1` (review item E).
- `frontend/README.md` is rewritten (what the app is, make targets, provenance, architecture notes, the services methods list unchanged from #15).

## Files created or modified

- Commits `c816d51` (clean-up) and `e65448e` (refused-case grep fixes).
- Removed: `frontend/bun.lock`, `frontend/bunfig.toml`, `frontend/AGENTS.md`, `frontend/.lovable/project.json`, `frontend/src/lib/lovable-error-reporting.ts`, 42 `frontend/src/components/ui/*.tsx`.
- Added: `frontend/.npmrc`. Modified: `frontend/README.md`, `frontend/vite.config.ts`, `frontend/package.json`, `frontend/package-lock.json`, `frontend/src/routes/__root.tsx`, `frontend/src/styles.css`.
- Protected files were not edited. The proposed `Makefile` `frontend-build` diff is in the `Engineer:` comment on #21.

## Decisions made by the human

- `frontend/.npmrc` ownership (2026-10-19, option 1): #21 adds `min-release-age=1`; #33 hardening D later appends `ignore-scripts=true`.
- Render mode: **open**. The Engineer sent the three-option question with build evidence; the human has not answered.

## Mismatches with the spec or design docs

None. `_docs/specs.md` covers product behaviour; render mode, npm configuration and frontend tooling are not in it, and no spec change is proposed.

## Commands to validate

- **Install:** `make frontend-install`: `npm ci`, 390 packages, leaves `frontend/package-lock.json` unchanged. `npm --prefix frontend config get min-release-age` prints `1`.
- **Test:** `make test` and `make frontend-test`: 2 files, 10 tests passed (baseline unchanged).
- **Verify:** `make verify`: PASS (tests 10/10, whitespace PASS, weakened tests none).
- **Run:** `make frontend-start`, then `/login` returns HTTP 200 with the sign-in form and demo credential hint; `make frontend-stop` stops only the recorded PID.
- **Build (interim config):** `npm --prefix frontend run build` exits 0. The proposed `make frontend-build` wraps it; it is not applied yet.
- Refused-case greps: `grep -rni lovable frontend --exclude=package-lock.json` → one hit (README provenance); `grep -rn "@lovable.dev" frontend/src frontend/vite.config.ts frontend/vitest.config.ts frontend/package.json` → none; `grep -nE "npm i([[:space:]]|$)|npm install" frontend/README.md` → none; network grep → `src/services/mockData.ts` and `src/server.ts` only.

## Proposed AGENTS.md changes

None. The Run and Install commands are unchanged; the new `frontend-build` target is proposed to the `Makefile` only (`AGENTS.md` has no Build slot).

## Temporary changes

- Render-mode spike configs `frontend/vite.spa-evidence.config.ts`, `frontend/vite.node-evidence.config.ts`, `frontend/vite.router-evidence.config.ts`, `frontend/index.html`, `frontend/src/main.tsx` and the build outputs (`frontend/dist`, `frontend/.output`, `frontend/node_modules/.nitro`) were created for evidence and deleted; `git status --short` is clean.
- `.scratch/node-build-start.sh`/`node-build-stop.sh` served the nitro Node build on `127.0.0.1:3100`; the process was stopped by its own stop script. `make frontend-start`/`frontend-stop` was likewise started and stopped by the agent.
- No system configuration changed and nothing was installed outside `frontend/node_modules`.

## Interruptions

None. QA has not run yet.

## Unrelated problems noticed but not fixed

- `vite-tsconfig-paths` logs "Vite now supports tsconfig paths resolution natively via the `resolve.tsconfigPaths` option" on every build. Vite `8.1.5` could use the native option and drop the plugin; not changed here because the issue keeps `vite-tsconfig-paths` as a build tool.
- `nitro` and `@tanstack/router-plugin` are in `devDependencies` but no config file imports them. The issue names them as build tools to keep while the render mode is undecided; `nitro` is unused by the interim config and unused entirely if option 3 is chosen.
- `frontend/package.json` still has no `packageManager` field; left as it is per the issue edge case.

## Follow-ups for the next session

- The human must answer the render-mode decision on #21; then the `vite.config.ts` target and (if server rendering is dropped) `src/server.ts`, `src/lib/error-capture.ts`, `src/lib/error-page.ts` and `src/start.ts` follow, and the #15 network-grep exception for `src/server.ts` ends.
- The Orchestrator applies the proposed protected `Makefile` `frontend-build` diff and commits it alone with `HUMAN_APPROVED=1` before QA.
- QA then checks the build output for the chosen mode (static `index.html` or a documented Node start command) and the absent-backend run.
