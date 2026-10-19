# Issue #021: Frontend clean-up — remove Lovable coupling and unused code

**Date:** 2026-10-19
**Spec version:** d3a8f11

## What changed and why

- The frontend no longer depends on the app-builder platform: `frontend/src/lib/lovable-error-reporting.ts` and its call site are gone, along with `frontend/AGENTS.md`, `frontend/.lovable/`, the `twitter:site` meta and the two Google Fonts links (replaced by system font stacks).
- `frontend/vite.config.ts` is an explicit config (tailwindcss, vite-tsconfig-paths, `tanstackRouter`, react; `VITE_*` injection, `@` alias, dedupe, `lightningcss`); the shared preset import is gone. Render mode is plain TanStack Router + Vite (client-only SPA), built to `frontend/dist/`.
- 42 unused `src/components/ui/*.tsx` files and the packages only they used are removed; `frontend/bun.lock` and `frontend/bunfig.toml` are gone, and `frontend/.npmrc` carries `min-release-age=1` (review item E).
- The three server-only files (`src/server.ts`, `src/lib/error-capture.ts`, `src/lib/error-page.ts`) and `src/start.ts` are removed; `frontend/index.html` and `frontend/src/main.tsx` mount the plain router. `@tanstack/react-start` and `nitro` are removed and the lockfile pruned.
- `frontend/README.md` is rewritten (what the app is, make targets, render mode and `frontend/dist/` output, provenance, architecture notes, the services methods list unchanged from #15).

## Files created or modified

- Commits `c816d51` (clean-up), `e65448e` (refused-case grep fixes) and `e367e49` (render mode: plain TanStack Router + Vite).
- Removed: `frontend/bun.lock`, `frontend/bunfig.toml`, `frontend/AGENTS.md`, `frontend/.lovable/project.json`, `frontend/src/lib/lovable-error-reporting.ts`, 42 `frontend/src/components/ui/*.tsx`, `frontend/src/server.ts`, `frontend/src/lib/error-capture.ts`, `frontend/src/lib/error-page.ts`, `frontend/src/start.ts`.
- Added: `frontend/.npmrc`, `frontend/index.html`, `frontend/src/main.tsx`. Modified: `frontend/README.md`, `frontend/vite.config.ts`, `frontend/package.json`, `frontend/package-lock.json`, `frontend/src/routes/__root.tsx` (Lovable coupling only), `frontend/src/styles.css` (fonts), `frontend/src/routeTree.gen.ts` (regenerated, Start augmentation dropped).
- Protected files were not edited. The approved `Makefile` `frontend-build` diff and the approved `AGENTS.md` Build line are for the Orchestrator to apply and commit (`HUMAN_APPROVED=1`) after this confirmation.

## Decisions made by the human

- `frontend/.npmrc` ownership (2026-10-19, option 1): #21 adds `min-release-age=1`; #33 hardening D later appends `ignore-scripts=true`.
- Render mode (2026-10-19, Orchestrator comment 6276301196): **option 3, plain TanStack Router + Vite**, production output `frontend/dist/` with `frontend/dist/index.html`. This ends the `src/server.ts` network-grep exception.
- Protected `Makefile` `frontend-build` target approved as proposed; protected `AGENTS.md` gets one Build line. The Orchestrator applies both after the Engineer confirms the output path (it is `frontend/dist/`, unchanged from the proposal).

## Mismatches with the spec or design docs

None. `_docs/specs.md` covers product behaviour; render mode, npm configuration and frontend tooling are not in it, and no spec change is proposed.

## Commands to validate

- **Install:** `make install` / `make frontend-install`: `npm ci`, 351 packages, lockfile stable (sha256 unchanged across two `npm ci` runs). `npm --prefix frontend config get min-release-age` prints `1`.
- **Test:** `make test` and `make frontend-test`: 2 files, 10 tests passed (baseline unchanged).
- **Verify:** `make verify`: PASS (tests 10/10, whitespace PASS, weakened tests none).
- **Build:** `npm --prefix frontend run build` exits 0 and writes `frontend/dist/index.html` (963 bytes) plus `frontend/dist/assets/` (main bundle 305233 bytes). The approved `make frontend-build` wraps it and is not applied yet.
- **Serve:** `.scratch/serve_check.py` served `frontend/dist` with `python3 -m http.server` on `127.0.0.1:8137`; `GET /` returned HTTP 200 (963 bytes, `#root` present) and the main JS asset returned HTTP 200 (305233 bytes); the script stopped only its own server.
- **Run:** `make frontend-start`, then `/login` returns HTTP 200 with the sign-in form and demo credential hint; `make frontend-stop` stops only the recorded PID.
- Refused-case greps: `grep -rni lovable frontend --exclude=package-lock.json` → one hit (README provenance); `grep -rn "@lovable.dev" frontend/src frontend/vite.config.ts frontend/vitest.config.ts frontend/package.json` → none; `grep -nE "npm i([[:space:]]|$)|npm install" frontend/README.md` → none; network grep → `src/services/mockData.ts` only (the `src/server.ts` exception has ended).

## Proposed AGENTS.md changes

One approved Build line for the Commands list, to be applied by the Orchestrator with `HUMAN_APPROVED=1`:

- **Build frontend:** `make frontend-build`: builds the production output to `frontend/dist/`.

## Temporary changes

- Render-mode spike configs `frontend/vite.spa-evidence.config.ts`, `frontend/vite.node-evidence.config.ts`, `frontend/vite.router-evidence.config.ts` and the build outputs `frontend/.output`, `frontend/node_modules/.nitro` were created for evidence and deleted. The final `frontend/index.html`, `frontend/src/main.tsx` and `frontend/dist` are now part of the chosen build.
- `.scratch/node-build-start.sh`/`node-build-stop.sh` served the nitro Node build on `127.0.0.1:3100`; the process was stopped by its own stop script. `.scratch/serve_check.py` served `frontend/dist` on `127.0.0.1:8137` and stopped only its own process. `make frontend-start`/`frontend-stop` was likewise started and stopped by the agent.
- No system configuration changed and nothing was installed outside `frontend/node_modules`.

## Interruptions

None. QA has not run yet.

## Unrelated problems noticed but not fixed

- `vite-tsconfig-paths` logs "Vite now supports tsconfig paths resolution natively via the `resolve.tsconfigPaths` option" on every build. Vite `8.1.5` could use the native option and drop the plugin; not changed here because the issue keeps `vite-tsconfig-paths` as a build tool.
- `nitro` was removed with the option 3 decision (nothing imports it now); `@tanstack/router-plugin` is imported directly by `frontend/vite.config.ts`, so it stays.
- `frontend/package.json` still has no `packageManager` field; left as it is per the issue edge case.

## Follow-ups for the next session

- The Orchestrator applies the approved protected `Makefile` `frontend-build` diff and the approved `AGENTS.md` Build line, each committed with `HUMAN_APPROVED=1`, before QA. The output path is `frontend/dist/`, so the approved diff is unchanged; if the Makefile `frontend-build` recipe differs from `npm --prefix frontend run build`, say so before QA.
- QA then checks the static `frontend/dist/index.html` output (HTTP 200 serve), the absent-backend run and the remaining #21 criteria, and re-runs the refused-case greps.
- #22 (services interface and README methods list) and #23 (API contract) remain out of scope for #21.
- `frontend/package.json` still carries the leftover name `tanstack_start_ts`; renaming it is cosmetic and was left out of #21's scope (noting it, not fixing it).
