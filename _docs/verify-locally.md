# Verifying the end-to-end flow locally

A step-by-step guide for independently checking the VulnTriage build on your own
machine: install the dependencies, run the test suites (`make test`), and bring
the application up locally (frontend + backend) for a manual end-to-end check.

This covers the **Tier A (phase S1)** build: the FastAPI backend on SQLite, the
React/Vite frontend, and the unit + SQLite-integration tests. Docker, Postgres,
deployment and observability are later phases (S2+) and are out of scope here.

> Status note (2026-10-23): `make test` runs both test suites, and `make dev`
> starts the backend and frontend together with one command (issue #133). The
> frontend talks to the real backend over one origin (the Vite dev server
> proxies the API paths), so this exercises the end-to-end path.

## 1. Prerequisites

You need a machine with real network access to PyPI and the npm registry (the
install step downloads packages). Install these tool versions, which match the
dev-container recipe in `_docs/agent-kit/environments.md`:

| Tool | Version | Check |
|---|---|---|
| Python | 3.12.x | `python3 --version` |
| uv | 0.13.1 (or newer) | `uv --version` |
| Node.js | 24.22.0 | `node --version` |
| npm | 11.x | `npm --version` |
| GNU Make | any recent | `make --version` |

A quick way to see them all at once:

```sh
make tool-versions
```

Docker is **not** required for this guide (it is only needed for the S2 Compose
stack).

## 2. Get the code

```sh
git clone https://github.com/andrew-chung-au/vuln-triage.git
cd vuln-triage
```

Everything below is run from the repository root.

## 3. Install dependencies

One command installs both halves — the frontend via `npm ci` (from
`frontend/package-lock.json`) and the backend via `uv sync --locked` (from
`backend/uv.lock`):

```sh
make install
```

If you want to do them separately:

```sh
make frontend-install   # npm ci in frontend/
make backend-install    # uv sync --locked in backend/
```

`make install` must finish cleanly before the test or run steps; the test
targets fail early with a clear message if `frontend/node_modules` or
`backend/.venv` is missing.

## 4. Run the tests (`make test`)

This is the single command that runs the frontend unit tests (vitest) and then
the backend unit + SQLite-integration tests (pytest):

```sh
make test
```

What it does, in order:

1. `make frontend-test` — `npm --prefix frontend test` (vitest, the cases in
   `frontend/src/test/`).
2. `make backend-test` — `backend/.venv/bin/pytest -c backend/pyproject.toml tests`
   (the backend unit and SQLite-integration cases in `tests/`, starting with the
   smoke test and the network-guard cases `U-NET` / `I-NET`).

Expected result: both runners report all tests passing. The exact case counts are
whatever each runner prints (they are intentionally not pinned in the docs).

### Network guard

The test harness forbids outbound HTTP: any live network call made during a test
**fails** that test (cases `U-NET` and `I-NET`). The only accepted modes are the
stubs `LLM_MODE=stub` and `RESPONDER_MODE=stub`. If you see `U-NET`/`I-NET`
failing, something is trying to reach the network during tests — that is the
guard working, not a flaky test.

### Run one layer at a time (optional)

```sh
make frontend-test       # frontend vitest only
make backend-test        # backend pytest only
make frontend-typecheck  # tsc --noEmit (vite build does not type-check)
```

## 5. Full verification gate (optional but recommended)

To run exactly what CI runs — both test suites plus the frontend type check,
whitespace and weakened-test checks:

```sh
make verify
```

`make verify` needs `make install` to have run first. The procedure behind it is
`_docs/agent-kit/procedures/verify.md`. A green `make verify` is the project's
definition of "done" for a task.

You can also validate the API contract on its own:

```sh
make openapi-validate
```

## 6. Run the application end to end (manual check)

The goal of the manual check is to confirm the stack runs end to end: the
frontend talks to the backend over one origin, the backend persists to SQLite,
and you can sign in and see assets and ranked findings.

### Start everything with one command

```sh
cp .env.example .env    # fill in GITHUB_READ_TOKEN if you will register assets
make dev
```

`make dev` first applies the SQLite migrations (`alembic upgrade head`, so the
schema exists on a fresh checkout), then starts:

- the backend (FastAPI on SQLite) on `http://127.0.0.1:8000`, and
- the frontend Vite dev server on `http://127.0.0.1:5173`.

They share one origin: the Vite dev server proxies the API paths
(`/auth`, `/findings`, `/assets`, `/signals`, `/scans`, `/health`) to the
backend, so there is no CORS and the `vt_session` cookie is first-party. The
frontend calls the real backend — the in-memory mock is no longer used at
runtime (it remains only as a vitest fixture).

Press `Ctrl-C` to stop both. The schema is created by the `dev-migrate` step
(`alembic upgrade head`, migrations in `backend/migrations/`, config
`backend/alembic.ini`); run `make dev-migrate` on its own to apply migrations
without starting the servers.

> `VERIFY:` if your backend ASGI entry point or port differs from
> `vulntriage.main:app` on `127.0.0.1:8000`, set `VITE_API_TARGET` for the proxy
> and adjust the Makefile target. The defaults match `backend/vulntriage/main.py`
> and `frontend/vite.config.ts`.

### Background form

To run both in the background (for scripted checks) instead of the foreground:

```sh
make dev-start   # logs: .scratch/dev-backend.log, .scratch/dev-frontend.log
make dev-stop    # stops only the processes dev-start recorded
```

### Create a sign-in user

There is no sign-up. Create a dashboard user with the backend's operator command
(task 9); it reads the password from a prompt, never the command line. Check
`backend/vulntriage/` for the exact command name (`VERIFY:` the invocation), then
run it to create a user with a role of `security lead` so you can register assets.

### What to look for (end-to-end acceptance)

1. Open `http://127.0.0.1:5173` — the sign-in page loads.
2. Sign in with the user you created; the login call reaches `POST /auth/login`
   on the backend and the session cookie is set.
3. As a `security lead`, register an asset (`POST /assets`); the first scan reads
   its lockfiles and creates findings.
4. The dashboard lists assets and ranked findings with status, KEV/EPSS values,
   dependencies and the rank reason — all served by the real backend, not the
   mock (the mock remains only as a vitest fixture).
5. Accept risk on a finding with a reason, request a re-scan, and confirm the
   audit trail shows who, when and the previous value.

This exercises the full Tier A path: frontend → backend → SQLite, with the
session cookie and CSRF header, matching the Application and Testing criteria for
phase S1.

## 7. Clean up

```sh
make frontend-stop     # if the dev server is still running
make clean-scratch     # remove .scratch/ working files
```

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `backend/.venv is missing: run make install first` | deps not installed | `make install` |
| `frontend/node_modules is missing: run make install first` | deps not installed | `make install` |
| `U-NET` / `I-NET` tests fail | a test tried to reach the network | that is the guard; find and stub the outbound call |
| Install step fails to download | no network / restricted registry access | run on a machine with real PyPI + npm access |
| Dashboard shows no data after `make dev` | backend not reached (proxy target or port) | check `.scratch/dev-backend.log`; set `VITE_API_TARGET` if the backend is not on `127.0.0.1:8000` |
| `make dev-start` says "already running" | a previous run is still up | `make dev-stop` first |

## Related docs

- `README.md` — the project in one page, planning-document index
- `_docs/tasks.md` — the numbered build tasks (task 11 defines `make dev`)
- `_docs/roadmap.md` — phases S1..S5 and what each banks
- `_docs/testing.md` — the full test strategy, case names and fixtures
- `_docs/agent-kit/environments.md` — which environment runs where
- `_docs/agent-kit/procedures/verify.md` — the `make verify` gate
