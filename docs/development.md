# Development guide

How to install VulnTriage, run it locally, and run its tests. Everything is a `make` target; run `make help` for the full list.

There are three ways to run it:

| Path | Needs | Database | Use it for |
|---|---|---|---|
| `make dev` / `make demo` | Python, uv, Node | SQLite | Day-to-day work and the quickest look at the app |
| `make compose-up` | Docker | Postgres | The containerised stack, the same shape as the deployment |
| `make test-compose JOB=…` | Docker | Postgres | The observability, alert and responder journeys |

## Prerequisites

| Tool | Version | Check |
|---|---|---|
| Python | 3.12 | `python3 --version` |
| uv | 0.13.1 or newer | `uv --version` |
| Node.js / npm | 24.x / 11.x | `node --version` |
| GNU Make | any recent | `make --version` |
| Docker + Compose | only for the container paths | `docker compose version` |

`make tool-versions` prints all of them at once.

```sh
git clone https://github.com/andrew-chung-au/vuln-triage.git
cd vuln-triage
make install        # frontend: npm ci · backend and responder: uv sync --locked
```

## Run it locally (no Docker)

### The demo (recommended first look)

```sh
make demo           # migrates, creates a user, starts backend + frontend, registers four demo repositories
# open http://127.0.0.1:5173 and sign in as  lead / demo-password-local
make dev-stop       # stop it
make demo-reset     # stop and delete the dev database
```

`make demo` runs the real app on SQLite against **recorded** copies of four public repositories and of the OSV, KEV and EPSS feeds (`VT_FEEDS=fixtures`), so the KEV and EPSS values are fixture values, not live data. `VT_FEEDS=fixtures` is refused unless `DEPLOYMENT_ENVIRONMENT` is `dev` or `test`, so it cannot run in production.

Expected: four assets; one with two ranked findings (P1 `urllib3` CVE-2023-43804 and P2 `pyyaml` CVE-2020-14343); one scan marked incomplete; one asset shown as ownerless. Running `make demo` twice registers the repositories twice; use `make demo-reset` to start over.

### Your own data

```sh
cp .env.example .env           # set GITHUB_READ_TOKEN to register real repositories
make dev                       # backend on 127.0.0.1:8000, frontend on 127.0.0.1:5173; Ctrl-C stops both
```

There is **no sign-up**, by design. Create a login with the operator command (it prompts for the password, never takes it on the command line):

```sh
cd backend && uv run python -m vulntriage.manage create-user \
  --username lead --display-name "Security Lead" --email lead@example.com --role "security lead"
```

Registering an asset takes any public `https://github.com/<owner>/<repo>` that has a `uv.lock`, `requirements.txt` or `package-lock.json`.

The SPA and the API share one origin: the API lives under `/api` and the proxy (Vite in dev, nginx in Compose) strips the prefix, so there is no CORS setup and the session cookie is first-party. Background form: `make dev-start` / `make dev-stop` (logs in `.scratch/`).

## Run the full stack in Docker

```sh
cp .env.example .env           # set POSTGRES_PASSWORD (the rest may stay blank to start)
make compose-up                # builds and starts db, migrations, backend and frontend, waiting until each is healthy
# app at http://localhost:8080
make compose-down              # stop, keep the Postgres volume
make compose-down CLEAN=1      # stop and remove the volume
```

Services start in dependency order: `db` (Postgres 16.4, named volume), `migrations` (one-shot `alembic upgrade head`), `backend` (health-checked at `/health`), `frontend` (nginx on port 8080, health-checked at `/healthz`). Only the frontend is published to the host.

Quick checks: sign in, register an asset and see findings; open `/findings` and hard-refresh (you must get the SPA, not raw API JSON); `make compose-down` then `make compose-up` and confirm the data survived.

> **Docker Desktop on Windows (WSL) reports `ports are not available … /forwards/expose … 500`?** Another Windows program already holds that host port; VS Code's automatic port forwarding has been the culprit. In VS Code's **Ports** panel stop forwarding the port and untick `remote.autoForwardPorts`. To find an owner from WSL: `netstat.exe -ano | grep :<port>`, then `tasklist.exe /FI "PID eq <pid>"`.

## Tests

```sh
make test                  # frontend (vitest) + backend (pytest) + responder (pytest)
make verify                # the gate CI runs: tests, frontend type check, whitespace and weakened-test checks
make openapi-validate      # validate docs/openapi.yaml
```

Run one layer: `make frontend-test`, `make backend-test`, `make responder-test`, `make frontend-typecheck`.

**Network guard.** The test harness forbids outbound HTTP: any live network call during a test fails it (cases `U-NET` and `I-NET`). The only accepted modes are the stubs `LLM_MODE=stub` and `RESPONDER_MODE=stub`. If those cases fail, something is trying to reach the network; fix the code, not the test.

**Postgres integration.** The integration cases also run on real Postgres:

```sh
make test-integration      # starts only `db` in a throwaway `vt-test` Compose project, runs the cases, tears it down
```

The `E-GUARD` check refuses to run unless the target is the `vt-test` database, so the suite can never touch a dev or real database.

**Compose journeys.** `make test-compose JOB=<telemetry|alert|responder>` runs the observability journey, the alert, and the responder wiring against a real Compose stack. No secrets or live feeds are needed; `ci/test-compose.sh` sets throwaway values and runs the backend on `VT_FEEDS=fixtures`. These cases are marked `compose` and deselected by `make test`, so a machine without Docker never runs or skips them silently (`tests/test_marker_hygiene.py` guards the marker).

| Job | What it proves |
|---|---|
| `telemetry` | The Collector drops excluded attributes (`T-REFUSE`); one scan-to-notification journey shares a trace id across metric, trace and log, and the owner email reaches MailHog (`T-JOURNEY-BE`) |
| `alert` | A top-tier job in stored state fires exactly one Grafana alert, to the owner's email and the responder sink (`A-FIRE`), and a removed rule fires nothing |
| `responder` | The responder refuses production, receives the real Grafana body, and rejects a bad bearer token |

Run these on a Docker host with the relevant ports free (8000, 3000, 4317, 8025, 9090, 9099, 9100, and the database port). The first run builds images, so allow a few minutes; the responder job takes about 20 minutes. The two Compose stacks publish the same host ports, so stop one before starting the other. If a job fails, keep the output and inspect it with `docker compose -p <project> ps` and `docker compose -p <project> logs <service>` before the script's cleanup removes the stack. The test strategy and the full case list are in [testing.md](testing.md).

Two alert checks have no automated test; run them after changing the alert rule:

1. **NoData gap (`A-GAP`, part 2).** With a finding alert firing, stop the Collector for about three minutes, then start it. MailHog gets one NoData email with no `finding_id`, and the webhook sink gets no new request.
2. **Resolution (`A-RESOLVE`, Grafana half).** Set the job to `sent` (`manage.py alert-set --finding-id <id> --state sent`). Within a few minutes the webhook sink records one `resolved` request and no second `firing` one.

## Clean up

```sh
make dev-stop          # if make dev-start is still running
make compose-down      # if the Compose stack is up
make clean-scratch     # empty .scratch/
```

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `backend/.venv is missing` or `frontend/node_modules is missing` | Dependencies not installed | `make install` |
| `U-NET` / `I-NET` fail | A test tried to reach the network | Find and stub the outbound call |
| Dashboard empty after `make dev` | Backend not reached | Check `.scratch/dev-backend.log`; set `VITE_API_TARGET` if the backend is not on `127.0.0.1:8000` |
| `make dev-start` says "already running" | A previous run is still up | `make dev-stop` |
| `make compose-up`: `.env is missing` | No `.env` | `cp .env.example .env` and set `POSTGRES_PASSWORD` |
| `/findings` returns JSON on refresh | nginx prefix-strip or SPA fallback misconfigured | Check `frontend/nginx.conf` (`location /api/` and `try_files … /index.html`) |
| Data gone after a restart | Stack stopped with `CLEAN=1` | Use plain `make compose-down` |
| A service never becomes healthy | A dependency failed its health check | `docker compose ps`, then `docker compose logs <service>` |

## Related

- [testing.md](testing.md): test strategy, case names and fixtures
- [architecture.md](architecture.md): design and decisions
- [deployment.md](deployment.md): running it on AWS
- [`observability/README.md`](../observability/README.md): the Grafana stack
