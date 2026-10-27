# On-call drill — granular command-by-command companion (owner-run)

Companion to [`_docs/drill-runbook.md`](drill-runbook.md) for issue
[#163](https://github.com/andrew-chung-au/vuln-triage/issues/163) (task 39).
The parent runbook is the checklist and the *why*; this file is the exact
commands and the *how*, including the screen recording. Run everything on a
Docker host that is **not** the agent sandbox, as the user whose Claude login
you want the agent to use.

> Everything below is grounded in the code on `main`: the responder env surface
> (`responder/vt_responder/config.py`), the CLI preflight
> (`responder/vt_responder/cli_session.py`), the compose wiring
> (`compose.yaml` + `compose.telemetry.yaml` + `compose.alert.yaml`), and the
> backend demo-defect gate (`backend/vulntriage/ingest/settings.py`). Lines
> flagged `VERIFY:` are confirmed only by the first live run.

## Conventions used below

- `$REPO` = the repo root of a clone where **you are the committer and the git
  hooks are installed** (`make hooks`). The responder agent runs in its *own*
  fresh checkout, not this one.
- Ports published to the host by the stack: backend `127.0.0.1:8000`, Grafana
  `127.0.0.1:3000`, Prometheus `127.0.0.1:9090`, MailHog UI `127.0.0.1:8025`.
  The real responder you start listens on `0.0.0.0:9100`.
- Docker bridge gateway (host as seen from a container): `172.17.0.1` on Linux
  default bridge; `host.docker.internal` on Docker Desktop. The exact value for
  the Compose project network is a `VERIFY:` in step 1.4.

---

## Step 0 — Preflight (do this before recording; ~15 min)

### 0.1 Confirm prerequisites from the parent runbook

```sh
# Claude Code is installed, recent, and logged in with a SUBSCRIPTION login.
claude --version
claude auth status            # must exit 0; authMethod must be claude.ai or oauth_token
claude auth status | jq .     # inspect authMethod / loggedIn explicitly
echo "exit: $?"

# Check your plan allowance is fresh (do not start a drill near a limit).
claude usage 2>/dev/null || echo "run /usage inside an interactive 'claude' session"
```

If `authMethod` is `api_key`, `api_key_helper`, `third_party`, or a cloud
provider, the responder will refuse to start. Fix with `claude auth login` using
your Claude account.

### 0.2 Confirm the tooling the stack needs

```sh
cd "$REPO"
make tool-versions            # docker must be present; node/uv/python3 for local bits
docker compose version
git log --oneline -1          # note the commit you are drilling from
```

### 0.3 Prepare `.env` (never committed)

```sh
cd "$REPO"
test -f .env || cp .env.example .env
```

Edit `.env` and set at least:

```ini
POSTGRES_PASSWORD=<any-local-value>
GRAFANA_ADMIN_PASSWORD=<any-local-value>
RESPONDER_API_TOKEN=<any-local-value>         # backend <-> responder share this
RESPONDER_MODE=stub                           # the Compose backend/responder stay stub
RESPONDER_RUNTIME=                            # empty or 'cli'
# The host responder you start in step 1.3 reads its own env, not this file.
```

The real responder you launch in step 1.3 takes its secrets from exported shell
variables, **not** from `.env` (uvicorn run by hand does not load `.env`). Keep
the GitHub token out of your shell history (step 1.3 reads it from a file).

### 0.4 Install the responder project venv on the host (for the real run)

```sh
cd "$REPO"
make responder-install        # creates responder/.venv from responder/uv.lock
test -x responder/.venv/bin/uvicorn && echo "uvicorn present" || \
  (cd responder && uv run python -c "import uvicorn" && echo "uvicorn via uv run")
```

> `responder/pyproject.toml` has `package = false` and no console script, so you
> invoke uvicorn as a module. Either `responder/.venv/bin/python -m uvicorn ...`
> or `uv run --directory responder python -m uvicorn ...` works; both are shown
> in step 1.3.

### 0.5 Close the demo-defect passthrough gap (one small override file)

The backend only honors `VT_DEMO_DEFECT` if it is in the **backend container's**
environment. In the recorded stack you run **without** `compose.responder.yaml`
(see the parent runbook), and `compose.yaml`'s backend does **not** pass
`VT_DEMO_DEFECT` through — only `compose.responder.yaml` does. So add a tiny
drill-only override that passes it through (and nothing else), so you do not
have to bring up the port-9100-holding responder service:

```sh
cd "$REPO"
cat > .scratch/compose.drill-defect.yaml <<'YAML'
# Drill-only override (task 39 / #163): pass VT_DEMO_DEFECT through to the
# backend when running WITHOUT compose.responder.yaml. Not committed; lives in
# .scratch/ and is removed by `make clean-scratch` after the sitting.
services:
  backend:
    environment:
      VT_DEMO_DEFECT: ${VT_DEMO_DEFECT:-}
YAML
echo "wrote .scratch/compose.drill-defect.yaml"
```

> The backend already receives `DEPLOYMENT_ENVIRONMENT=test` from
> `compose.telemetry.yaml`, so the `require_demo_defect_allowed()` gate
> (`backend/vulntriage/ingest/settings.py`) permits the defect. Without that
> label the backend would refuse to start — this is why you keep the telemetry
> override in the file list.

### 0.6 Start the screen recording

Record **Part 1 in full**; screenshots alone are fine for Parts 2–3.

- Linux (X11), whole screen with the mic off, into a timestamped file:
  ```sh
  mkdir -p "$REPO/.scratch/recordings"
  OUT="$REPO/.scratch/recordings/drill-$(date +%Y%m%d-%H%M%S).mp4"
  # Replace 1920x1080 / :0.0 with your resolution and display.
  ffmpeg -y -f x11grab -framerate 25 -video_size 1920x1080 -i :0.0 \
    -c:v libx264 -preset veryfast -pix_fmt yuv420p "$OUT" &
  echo $! > "$REPO/.scratch/recordings/ffmpeg.pid"
  echo "recording to $OUT (pid $(cat "$REPO/.scratch/recordings/ffmpeg.pid"))"
  ```
  Stop it later with:
  ```sh
  kill "$(cat "$REPO/.scratch/recordings/ffmpeg.pid")"; sleep 1; echo stopped
  ```
- macOS: ⌘⇧5 → *Record Entire Screen* (or OBS). Docker Desktop users: remember
  the gateway is `host.docker.internal`, not `172.17.0.1` (step 1.4).
- Either OS: [OBS Studio](https://obsproject.com/) is the robust fallback.

Say the date and the commit sha out loud (or show `git log --oneline -1`) at the
start so the recording is self-dating.

---

## Part 1 — the recorded alert-to-fix drill

> **Project name used throughout: `vt-drill`.** Keep the same `-p vt-drill` and
> the same `-f` file list on every `docker compose` call so they all target one
> project/network. Define them once:
>
> ```sh
> cd "$REPO"
> export COMPOSE_PROJECT_NAME=vt-drill
> DRILL=(docker compose -p vt-drill \
>   -f compose.yaml -f compose.telemetry.yaml -f compose.alert.yaml \
>   -f .scratch/compose.drill-defect.yaml)
> ```

### 1.1 Export the Grafana/alert wiring (throwaway values, not real secrets)

These are read by the alert provisioning inside Grafana and by
`compose.alert.yaml`. The webhook URL points Grafana at the **host** responder
you start in 1.3 — not at any container.

```sh
export GRAFANA_ADMIN_PASSWORD="$(grep -E '^GRAFANA_ADMIN_PASSWORD=' .env | cut -d= -f2-)"
export POSTGRES_PASSWORD="$(grep -E '^POSTGRES_PASSWORD=' .env | cut -d= -f2-)"
export RESPONDER_API_TOKEN="$(grep -E '^RESPONDER_API_TOKEN=' .env | cut -d= -f2-)"

export VT_ALERT_HUMAN_EMAIL="oncall@drill.test"
export VT_RESPONDER_WEBHOOK_TOKEN="drill-webhook-$(openssl rand -hex 8)"  # the bearer secret
# Filled in after step 1.4 confirms the gateway address:
# export VT_RESPONDER_WEBHOOK_URL="http://172.17.0.1:9100/webhook/grafana"
export DEPLOYMENT_ENVIRONMENT=test          # lets the defect gate pass
export RESPONDER_MODE=stub                  # the COMPOSE backend stays stub; your host responder is real
```

> `VT_RESPONDER_WEBHOOK_TOKEN` is the single shared secret: Grafana presents it
> as `Authorization: Bearer <token>`, and your host responder checks it against
> `RESPONDER_WEBHOOK_SECRET` (set to the same value in step 1.3).

### 1.2 Bring the stack up with the defect ON, minus the responder service

```sh
export VT_DEMO_DEFECT=notify_no_fix

# Grafana last, after the metric heartbeat, exactly as ci/test-compose.sh does,
# so NoData does not fire a spurious start-up alert.
"${DRILL[@]}" up -d --wait \
  db migrations otel-collector prometheus tempo loki mailhog webhook-sink backend

# Wait for the overdue gauge to appear in Prometheus before starting Grafana.
for i in $(seq 1 60); do
  curl -fsS 'http://localhost:9090/api/v1/query?query=vt_top_tier_notification_overdue' \
    | grep -q '"result":\[{' && break
  sleep 5
done

"${DRILL[@]}" up -d --wait grafana
"${DRILL[@]}" ps                        # ✓ screenshot: all containers healthy

# Confirm the defect really reached the backend container.
"${DRILL[@]}" exec -T backend sh -c 'printf %s "$VT_DEMO_DEFECT"'; echo
# -> must print: notify_no_fix
```

### 1.3 Seed the security-lead user and register the failing asset

The no-fixed-version finding comes from registering `fixture-owner/pip-app`
(the #233 fixture): its flask 2.3.3 finding has no fixed version and ranks top
tier, so the owner-notification formatter hits the demo defect and the delivery
job fails.

```sh
# Create the login user INSIDE the backend container (password piped on stdin).
printf '%s\n' 'drill-not-a-secret' | "${DRILL[@]}" run -T --rm backend \
  python -m vulntriage.manage create-user \
  --username drill-lead --display-name "Drill Lead" \
  --email lead@drill.test --role "security lead"
```

Register `fixture-owner/pip-app` over the published backend port. The backend
uses a **session cookie** (`vt_session`, set by `/auth/login`) plus a **CSRF
header** (`X-Requested-With: XMLHttpRequest`) on every write — not a bearer
token. The asset body is the one the #233 case uses (camelCase,
`repositoryUrl`). `/assets` returns **201** on success:

```sh
# 1) Log in; keep the vt_session cookie in a jar.
curl -fsS -c .scratch/drill-cookies.txt -X POST http://127.0.0.1:8000/auth/login \
  -H 'content-type: application/json' \
  -d '{"username":"drill-lead","password":"drill-not-a-secret"}'

# 2) Register the failing asset (cookie + CSRF header, exact #233 body).
curl -fsS -b .scratch/drill-cookies.txt -X POST http://127.0.0.1:8000/assets \
  -H 'content-type: application/json' \
  -H 'X-Requested-With: XMLHttpRequest' \
  -d '{
        "name": "pip-app",
        "ownerName": "Owner",
        "ownerEmail": "pip-owner@team.example",
        "criticality": "high",
        "internetFacing": true,
        "repositoryUrl": "https://github.com/fixture-owner/pip-app"
      }'
# -> HTTP 201 with the created asset JSON; registration enqueues the scan.
```

> Why this asset: `fixture-owner/pip-app` pins flask 2.3.3, which the #233
> fixture advisory (`tests/fixtures/osv/vulns/GHSA-fixture-nofix-0001.json`)
> covers with an open-ended range, so the finding has **no fixed version** and,
> internet-facing + KEV-listed, ranks top tier. The owner-notification
> formatter then hits the `notify_no_fix` demo defect and the delivery job
> fails — which drives the metric to 1. The exact body and flow are copied from
> `tests/test_compose_demo_be.py` and `tests/compose_telemetry.py`
> (`backend_login` / `backend_register_asset`).

### 1.4 Start the REAL responder on the host

First confirm the gateway address Grafana's container uses to reach the host:

```sh
# The Compose network name is <project>_default unless overridden.
docker network inspect vt-drill_default \
  -f '{{range .IPAM.Config}}{{.Gateway}}{{end}}'; echo
# From inside Grafana, confirm the host port is reachable on that address:
"${DRILL[@]}" exec -T grafana sh -c 'getent hosts host.docker.internal || true'
# Linux default: 172.17.0.1. Docker Desktop: host.docker.internal.
```

Set the webhook URL for Grafana to the confirmed gateway, then **recreate
Grafana** so it reloads the contact point:

```sh
export VT_RESPONDER_WEBHOOK_URL="http://172.17.0.1:9100/webhook/grafana"   # <- confirmed value
"${DRILL[@]}" up -d --force-recreate --no-deps grafana
```

Now launch the real responder in a dedicated terminal (recorded). Keep the
GitHub token out of your shell history by reading it from a file:

```sh
cd "$REPO/responder"

# The fine-grained responder token (#222), one line, no trailing newline issues:
#   printf %s 'ghp_xxx' > ~/.secrets/responder-token  (chmod 600)
export RESPONDER_GITHUB_TOKEN="$(cat ~/.secrets/responder-token)"

export RESPONDER_MODE=real
export RESPONDER_RUNTIME=cli                       # headless `claude -p` on your login
export RESPONDER_MODEL=claude-sonnet-5-5           # F4 pin; REQUIRED in real mode
export RESPONDER_WEBHOOK_SECRET="$VT_RESPONDER_WEBHOOK_TOKEN"   # same value Grafana presents
export RESPONDER_API_TOKEN="$RESPONDER_API_TOKEN"              # same as the backend
export RESPONDER_API_URL="http://127.0.0.1:8000"   # VERIFY: backend as the HOST sees it
export RESPONDER_GITHUB_REPO="andrew-chung-au/vuln-triage"
export RESPONDER_MAX_TURNS=30                       # modest; the default
# Do NOT export ANTHROPIC_API_KEY — the responder scrubs it anyway, but keep it clean.

# Start it, binding to all interfaces so the Grafana container can reach it.
# You are already inside $REPO/responder, so the venv is ./.venv:
.venv/bin/python -m uvicorn \
  vt_responder.app:create_app_from_env --factory \
  --host 0.0.0.0 --port 9100 2>&1 | tee "$REPO/.scratch/responder-drill.log"
#   (equivalently, from anywhere: uv run --directory "$REPO/responder" \
#      python -m uvicorn vt_responder.app:create_app_from_env --factory \
#      --host 0.0.0.0 --port 9100 )
```

What you must see at start-up:

- **No** line beginning `the 'claude' CLI ...`. That prefix means the CLI
  preflight failed (not on PATH / too old / not logged in / not a subscription
  login) — fix per the message and restart.
- uvicorn reports `Uvicorn running on http://0.0.0.0:9100`.

Sanity-check the endpoint from the host before you let the alert reach it:

```sh
# A wrong bearer must be rejected 401 (constant-time check in app.py).
curl -s -o /dev/null -w '%{http_code}\n' -X POST http://127.0.0.1:9100/webhook/grafana \
  -H 'authorization: Bearer wrong' -H 'content-type: application/json' -d '{}'
# -> 401
```

> The listen address is owned entirely by the uvicorn `--host`/`--port` flags;
> the app reads no bind variable of its own. `RESPONDER_API_URL` is unrelated —
> it is the *outbound* URL the responder uses to call the backend.

### 1.5 ✓ Metric reaches 1 (checklist step 2)

```sh
watch -n 5 "curl -fsS 'http://localhost:9090/api/v1/query?query=vt_top_tier_notification_overdue' | jq '.data.result'"
```

Capture the metric at value `1` — in Grafana (Explore → Prometheus →
`vt_top_tier_notification_overdue`) or the Prometheus UI
(`http://localhost:9090`). ✓ screenshot.

### 1.6 ✓ Exactly one alert naming the finding + owner email in MailHog (step 3)

- Grafana → **Alerting → Alert rules** (or **Active notifications**): the US-14
  rule should be **Firing** with exactly one alert carrying the finding id. ✓
  screenshot. Wait ~20 s and confirm it is still *one* (not "at least one").
- MailHog UI `http://localhost:8025`: the owner/on-call email has arrived. ✓
  screenshot.

```sh
# Quick CLI confirmation of the MailHog inbox:
curl -fsS http://localhost:8025/api/v2/messages | jq '.total, .items[0].Content.Headers.Subject'
```

### 1.7 ✓ The responder opens a real PR (step 4)

Watch the responder log (the terminal from 1.4, or tail the tee'd file):

```sh
tail -f "$REPO/.scratch/responder-drill.log" | \
  grep -E '"event":"(run_started|api_read|branch_pushed|pull_request_opened|run_failed)"'
```

Expected sequence of JSON log lines (one per line, `vt_responder.actlog`):

1. `run_started` — `outcome:"started"`, `model:"claude-sonnet-5-5"` ← note the model field.
2. `api_read` — `outcome:"ok"`.
3. `branch_pushed` — `outcome:"ok"`, `branch:"responder/<fingerprint>"`.
4. `pull_request_opened` — `outcome:"agent"`, `pull_request:"<url>"`, `model:"<served>"`.

✓ capture: the responder log showing `model`, `branch_pushed`,
`pull_request_opened`; and the PR on GitHub showing the fix **and** the new
failing test.

```sh
# Confirm the PR from the host (reads, no write):
gh api "repos/andrew-chung-au/vuln-triage/pulls?state=open&head=andrew-chung-au:responder/" \
  --jq '.[] | {number, title, html_url, head: .head.ref}'
```

If instead you see `run_failed`, read its `reason`:

```sh
grep '"event":"run_failed"' "$REPO/.scratch/responder-drill.log" | tail -1 | jq '{reason, model}'
```

Common reasons and the fix (full list in `_docs/responder-cli-runtime.md`):

| reason | meaning / what to do |
|---|---|
| `plan_usage_limit` | plan allowance exhausted; wait for reset, then let Grafana's repeat notification retry (bounded by `RESPONDER_MAX_FAILED_RUNS`, default 3). |
| `max_turns` | raise `RESPONDER_MAX_TURNS` a little and restart the responder. |
| `agent_timeout` | raise `RESPONDER_RUN_TIMEOUT_SECONDS` (default 600) and restart. |
| `diff_path_*` | the agent touched a protected path; usually transient — retry. |
| preflight message `the 'claude' CLI ...` | login/CLI problem; see 1.4. |

A retry happens automatically on Grafana's next repeat notification while the
metric is still 1; you do not need to re-fire anything by hand.

### 1.8 ✓ You merge the PR (step 5)

The responder cannot merge (`main` is protected). Merge it yourself in the
GitHub UI, or:

```sh
PR=<number-from-1.7>
gh api -X PUT "repos/andrew-chung-au/vuln-triage/pulls/$PR/merge" -f merge_method=squash
```

✓ screenshot the merged PR.

### 1.9 ✓ Delivery retried; owner mail arrives (step 6)

Turn the defect off and recreate the backend so it re-reads the environment
(`docker compose restart` does **not** re-read env):

```sh
unset VT_DEMO_DEFECT
"${DRILL[@]}" up -d --force-recreate --no-deps --wait backend
"${DRILL[@]}" exec -T backend sh -c 'printf %s "$VT_DEMO_DEFECT"'; echo   # -> empty
```

The delivery worker retries the failed job on its next ~30 s poll and the owner
notification now formats and sends. Watch MailHog:

```sh
watch -n 5 "curl -fsS http://localhost:8025/api/v2/messages | jq '.total, [.items[].Content.Headers.Subject]'"
```

✓ screenshot the delivered owner mail in MailHog.

### 1.10 ✓ Metric back to 0; alert resolves (step 7)

```sh
watch -n 5 "curl -fsS 'http://localhost:9090/api/v1/query?query=vt_top_tier_notification_overdue' | jq '.data.result'"
```

Wait for the metric to read `0`; then Grafana resolves the alert (allow the
rule evaluation + the policy `group_interval`, up to a few minutes). ✓
screenshot the **resolved** alert in Grafana. You may also see an
`alert_ignored` / `outcome:"resolved"` line in the responder log (no new run).

### 1.11 Stop the recording and save it

```sh
# If using the ffmpeg recorder from step 0.6:
kill "$(cat "$REPO/.scratch/recordings/ffmpeg.pid")"; sleep 1
ls -lh "$REPO"/.scratch/recordings/
```

Upload the file to the project channel
([youtube.com/@cloudaisolutions](https://www.youtube.com/@cloudaisolutions)) and
copy the public link; you wire it into the README in step 1.12.

### 1.12 Put the recording link in the README and on #163 (step 8)

The two blocks to update are in `README.md`:

- The **`### Demo recording`** section (just below the rubric table, ~line 48):
  replace/confirm the channel link, and add the direct video URL.
- The **`### Observability evidence`** section (~line 201): update the
  "Not captured yet" paragraph (~line 213) to point at the recording now that
  the drill is done.

Also update the criterion-12 row of the rubric table (currently `0`) once the
auditor re-audits (see "After the sitting"). Then comment on #163 with the link:

```sh
cd "$REPO"
mkdir -p .scratch
cat > .scratch/163-drill-done.md <<'MD'
Recorded alert-to-fix drill complete (task 39). Recording: <PUBLIC_URL>

metric→1 → one US-14 alert naming the finding → owner email in MailHog →
responder opened PR #<N> (model claude-sonnet-5-5) → merged → delivery retried,
owner mail delivered → metric→0, alert resolved. Responder log, PR, and
screenshots in the recording.
MD
make issue-comment N=163 FILE=.scratch/163-drill-done.md
```

### 1.13 Cleanup commit — remove the demo-defect path (step 9)

Do this **before any production promotion** (the `P-FLAG-GONE` gate blocks a
promote while the defect is in the tree). This is the task-29 cleanup; apply it
per `_docs/161-responder-job-proposal.md` §2.5, then confirm:

```sh
cd "$REPO"
python3 ci/check_flag_gone.py && echo "P-FLAG-GONE: PASS"
```

Note the cleanup touches `.github/` paths, so it needs `HUMAN_APPROVED=1`
commits (hooks installed via `make hooks`) — follow `_docs/161-owner-apply-commits.md`.

---

## Part 2 — protect Observability (criterion 10)

Same stack still up. Open Grafana `http://localhost:3000` (admin /
`$GRAFANA_ADMIN_PASSWORD`).

### 2.1 Re-load and re-capture the US-13 dashboard

```sh
# Confirm the committed JSON is the current one:
jq '.title' "$REPO/observability/grafana/dashboards/us13-journey.json"
```

In Grafana: **Dashboards → New → Import → Upload JSON file** →
`observability/grafana/dashboards/us13-journey.json` → Import. Open it, confirm
all three panes render (metric / Tempo traces / Loki logs), switch to **view
mode** (the eye icon / `d v`), and screenshot. Replace
`docs/images/g9-grafana-dashboard-dev-local.png` with this capture so the
committed screenshot matches the current JSON (no stale Environment/Version
dropdowns).

### 2.2 Metric→trace leg (exemplar)

In a metric panel, enable **Exemplars** and hover a dot to follow it to a Tempo
trace, or use Explore → Prometheus → the metric → the exemplar link. ✓
screenshot if it shows. If the exemplar will not render in the UI, leave the
existing README note — the leg is already CI-asserted
(`tests/test_compose_telemetry.py`, the `telemetry` job), which is honest
evidence.

### 2.3 Trace→logs link

Open a Tempo trace → a span → **Logs for this span** (the trace→Loki link). ✓
screenshot if it resolves to the matching Loki log line (same trace id).

---

## Part 3 — protect CI/CD (criterion 9), ~2 min

GitHub → repo **Settings → Rules → Rulesets → `protect-main`** → open the
**"Require status checks to pass"** section so the required check names are
visible. ✓ screenshot to replace/supplement
`docs/images/g5-github-settings-rulesets-protect-main.png`, so a grader can see
which checks gate the merge.

---

## After the sitting (teardown)

```sh
cd "$REPO"

# 1. Stop the host responder: Ctrl-C in its terminal (sends SIGINT to uvicorn).

# 2. Tear down the stack (removes the drill volumes too).
"${DRILL[@]}" down --volumes --remove-orphans

# 3. Hand criterion-12 re-audit to the rubric auditor (auditor edits
#    _docs/rubric-evidence.md; the Engineer does not).

# 4. Keep the nightly stop OFF until after grading (it takes the public URL down
#    and breaks criterion 8).

# 5. Scrub scratch (keeps the token in .env only); also removes the drill
#    override and the recording working copy once you have uploaded it.
make clean-scratch

# 6. If you used a throwaway HOME / CLAUDE_CONFIG_DIR for the drill login:
#    claude auth logout
```

## What this closes

- **Criterion 12 (On-Call Agent) 0 → 2**: a real agent woke on the alert and
  fixed the issue, recorded end to end.
- **Criterion 10 (Observability)**: the dashboard screenshot matches the current
  JSON; the metric leg is shown or honestly captioned; the trace→logs link tried.
- **Criterion 9 (CI/CD)**: the required status checks are visible in the ruleset.

## Quick reference — the responder's real-mode env (from `config.py`)

| Variable | Required? | Default | Notes |
|---|---|---|---|
| `RESPONDER_MODE` | yes | — | must be `real` for the drill (`stub`/`real` only) |
| `RESPONDER_MODEL` | yes (real) | — | pin `claude-sonnet-5-5` (F4); no code default |
| `RESPONDER_RUNTIME` | no | `cli` | `cli` = headless `claude -p` on your login |
| `RESPONDER_WEBHOOK_SECRET` | yes | — | = Grafana's `VT_RESPONDER_WEBHOOK_TOKEN` |
| `RESPONDER_API_TOKEN` | yes | — | = the backend's `RESPONDER_API_TOKEN` |
| `RESPONDER_API_URL` | no | `http://backend:8000` | set to `http://127.0.0.1:8000` on the host |
| `RESPONDER_GITHUB_TOKEN` | yes (real) | — | runner push + PR only; env only |
| `RESPONDER_GITHUB_REPO` | yes (real) | — | `owner/name` |
| `RESPONDER_MAX_TURNS` | no | `30` | keep modest |
| `RESPONDER_RUN_TIMEOUT_SECONDS` | no | `600` | wall-clock run cap |
| `RESPONDER_MAX_FAILED_RUNS` | no | `3` | retries per fingerprint |
| `RESPONDER_MAX_COMMITS` | no | `3` | commits before the diff gate refuses |
| `ANTHROPIC_API_KEY` | only with `RESPONDER_RUNTIME=sdk` | — | not used/needed for the `cli` drill; scrubbed |

Webhook: `POST /webhook/grafana`, `Authorization: Bearer <RESPONDER_WEBHOOK_SECRET>`;
200 accepted, 401 bad bearer, 413 too large, 400 malformed, 503 queue full.
