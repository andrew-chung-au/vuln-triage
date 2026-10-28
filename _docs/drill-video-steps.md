# On-call drill video: the one step list

This file supersedes Part 1 step 1 of `_docs/drill-runbook.md` and all of `_docs/drill-runbook-commands.md` for the video. Use only this file.

Setup: WSL2 Ubuntu bash, repo at `~/clone/vuln-triage`, Docker running, your own Claude login (Pro plan). Paste one block per step. Stay in `~/clone/vuln-triage` unless a step says otherwise. Part A and steps marked OFF CAMERA are not recorded. If you get stuck, tell the step number (for example "B13") and the last output.

Never show on camera: `.env`, anything in `.scratch/` except `responder.log`, the Grafana password, the GitHub token, the output of `docker compose config`, the output of `env`.

---

## PART A: setup (OFF CAMERA, 20 to 40 minutes the first time)

### A1. Open a NEW terminal and go to the repo
```bash
cd ~/clone/vuln-triage
```
Expect: no output.

### A2. Get the latest code
```bash
git pull --ff-only
```
Expect: `Already up to date.` or a list of updated files.

### A3. Check the tools are installed
```bash
for t in docker openssl curl uv node git claude; do command -v $t >/dev/null && echo "ok      $t" || echo "MISSING $t"; done
```
Expect: seven `ok` lines, no `MISSING`.

### A4. Check Docker is running
```bash
docker info --format 'docker server {{.ServerVersion}}'
```
Expect: `docker server ` and a version number. An error means start Docker Desktop (or the Docker service) and repeat.

### A5. Check your Claude login
```bash
claude auth status
```
Expect: `"loggedIn": true` and `"authMethod"` `claude.ai` or `oauth_token`. If not: run `claude auth login`, then repeat A5.

### A6. Check no old exported values are left in this terminal
```bash
compgen -e | grep -E '^(POSTGRES_PASSWORD|GRAFANA_ADMIN_PASSWORD|RESPONDER_[A-Z_]+|VT_[A-Z_]+|COMPOSE_[A-Z_]+|DEPLOYMENT_ENVIRONMENT|MAIL_[A-Z_]+|LLM_MODE|ANTHROPIC_[A-Z_]+|CI|GITHUB_ACTIONS)$' || echo none
```
Expect: `none`. If names are listed: close the terminal, open a new one, repeat from A1.

### A7. Install the responder
```bash
make responder-install
```
Expect: it ends without an error line. Wait: 1 to 3 minutes.

### A8. Write `.env` (any old `.env` is moved aside, not overwritten)
```bash
mkdir -p .scratch
if [ -f .env ]; then mv .env ".env.bak-$(date +%Y%m%d-%H%M%S)"; echo "old .env moved aside"; fi
PG=$(openssl rand -hex 24)
GF=$(openssl rand -hex 24)
API=$(openssl rand -hex 24)
WH=$(openssl rand -hex 24)
cat > .env <<EOF
POSTGRES_PASSWORD=$PG
GRAFANA_ADMIN_PASSWORD=$GF
RESPONDER_API_TOKEN=$API
VT_RESPONDER_WEBHOOK_TOKEN=$WH
VT_ALERT_HUMAN_EMAIL=oncall@drill.test
MAIL_SENDER=vulntriage@sender.example
VT_RESPONDER_WEBHOOK_URL=http://host.docker.internal:9100/webhook/grafana
VT_DEMO_DEFECT=notify_no_fix
LLM_MODE=stub
RESPONDER_MODE=stub
COMPOSE_PROJECT_NAME=vt-drill
COMPOSE_FILE=compose.yaml:compose.telemetry.yaml:compose.alert.yaml:.scratch/compose.drill-defect.yaml
EOF
chmod 600 .env
unset PG GF API WH
echo ".env written"
```
Expect: `.env written` (and `old .env moved aside` if you had one).

### A9. Check `.env` has 12 lines
```bash
grep -c '=' .env
```
Expect: `12`.

### A10. Write the Compose override file
```bash
cat > .scratch/compose.drill-defect.yaml <<'YAML'
services:
  backend:
    environment:
      VT_DEMO_DEFECT: ${VT_DEMO_DEFECT:-}
  grafana:
    extra_hosts:
      - "host.docker.internal:host-gateway"
YAML
echo override written
```
Expect: `override written`.

### A11. Check Compose accepts the files and `.env`
```bash
docker compose config --quiet && echo "compose config OK"
```
Expect: `compose config OK` and no message about a missing or required variable. (Never run `docker compose config` without `--quiet`: it prints secrets.)

### A12. Write the responder start script
```bash
cat > .scratch/start-responder.sh <<'SH'
#!/usr/bin/env bash
set -eu
cd "$(dirname "$0")/.."
if [ -f .scratch/responder.pid ] && kill -0 "$(cat .scratch/responder.pid)" 2>/dev/null; then
  echo "responder already running (pid $(cat .scratch/responder.pid)); stop it first (C1)"; exit 1
fi
set -a; source ./.env; set +a
unset ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN ANTHROPIC_BASE_URL DEPLOYMENT_ENVIRONMENT CI GITHUB_ACTIONS
unset POSTGRES_PASSWORD GRAFANA_ADMIN_PASSWORD COMPOSE_FILE COMPOSE_PROJECT_NAME VT_DEMO_DEFECT LLM_MODE MAIL_SENDER VT_ALERT_HUMAN_EMAIL
export RESPONDER_WEBHOOK_SECRET="$VT_RESPONDER_WEBHOOK_TOKEN"
export RESPONDER_MODE=real
export RESPONDER_RUNTIME=cli
export RESPONDER_MODEL=claude-sonnet-5-5
export RESPONDER_API_URL=http://127.0.0.1:8000
export RESPONDER_GITHUB_REPO=andrew-chung-au/vuln-triage
export RESPONDER_STATE_FILE="$PWD/.scratch/responder-state/handled-fingerprints.json"
mkdir -p .scratch/responder-state
read -rsp 'GitHub token for the responder (hidden, not saved): ' RESPONDER_GITHUB_TOKEN
echo
export RESPONDER_GITHUB_TOKEN
nohup responder/.venv/bin/python -m uvicorn --app-dir responder \
  vt_responder.app:create_app_from_env --factory --host 0.0.0.0 --port 9100 \
  > .scratch/responder.log 2>&1 &
echo $! > .scratch/responder.pid
for i in $(seq 1 30); do
  code=$(curl -s -o /dev/null -w '%{http_code}' -X POST http://127.0.0.1:9100/webhook/grafana \
    -H 'Authorization: Bearer wrong' -H 'Content-Type: application/json' -d '{}' || true)
  [ "$code" = "401" ] && { echo "responder up (pid $(cat .scratch/responder.pid)); wrong bearer correctly refused with 401"; exit 0; }
  kill -0 "$(cat .scratch/responder.pid)" 2>/dev/null || break
  sleep 2
done
echo "responder did NOT start; last log lines:"; tail -n 15 .scratch/responder.log; exit 1
SH
chmod +x .scratch/start-responder.sh
echo written
```
Expect: `written`.

### A13. Write the value-check script
```bash
cat > .scratch/check-values.sh <<'SH'
#!/usr/bin/env bash
cd "$(dirname "$0")/.." || exit 1
set -a; source ./.env; set +a
BAD=0
h() { if [ -z "$1" ]; then echo "EMPTY"; else printf %s "$1" | sha256sum | cut -c1-12; fi; }
same() {
  if [ "$2" = "$3" ] && [ "$2" != "EMPTY" ]; then echo "OK        $1 ($2)"; else echo "MISMATCH  $1 (A=$2 B=$3)"; BAD=1; fi
}
cenv() { docker compose exec -T "$1" sh -c "printf %s \"\$$2\""; }
penv() { tr '\0' '\n' < "/proc/$1/environ" | grep "^$2=" | cut -d= -f2-; }
A=$(h "$VT_RESPONDER_WEBHOOK_TOKEN")
B=$(h "$RESPONDER_API_TOKEN")
same "grafana container VT_RESPONDER_WEBHOOK_TOKEN vs .env" "$A" "$(h "$(cenv grafana VT_RESPONDER_WEBHOOK_TOKEN)")"
same "backend container RESPONDER_API_TOKEN vs .env" "$B" "$(h "$(cenv backend RESPONDER_API_TOKEN)")"
PID=$(cat .scratch/responder.pid 2>/dev/null || true)
if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
  same "responder process RESPONDER_WEBHOOK_SECRET vs .env webhook token" "$A" "$(h "$(penv "$PID" RESPONDER_WEBHOOK_SECRET)")"
  same "responder process RESPONDER_API_TOKEN vs .env" "$B" "$(h "$(penv "$PID" RESPONDER_API_TOKEN)")"
  echo "responder: MODE=$(penv "$PID" RESPONDER_MODE) MODEL=$(penv "$PID" RESPONDER_MODEL) RUNTIME=$(penv "$PID" RESPONDER_RUNTIME) API_URL=$(penv "$PID" RESPONDER_API_URL)"
  echo "responder ANTHROPIC_API_KEY: $(penv "$PID" ANTHROPIC_API_KEY | wc -c | tr -d ' ') chars (expect 0)"
else
  echo "MISMATCH  responder is not running"; BAD=1
fi
echo "backend: VT_DEMO_DEFECT=$(cenv backend VT_DEMO_DEFECT) RESPONDER_MODE=$(cenv backend RESPONDER_MODE) VT_FEEDS=$(cenv backend VT_FEEDS) DEPLOYMENT_ENVIRONMENT=$(cenv backend DEPLOYMENT_ENVIRONMENT)"
echo "grafana to responder (wrong bearer, expect 401):"
docker compose exec -T grafana sh -c 'wget -S -O /dev/null --header="Authorization: Bearer wrong" --post-data="{}" "$VT_RESPONDER_WEBHOOK_URL"' 2>&1 | grep -E 'HTTP/|can.t connect|bad address|refused|timed out' || echo "no answer line"
claude auth status | grep -E 'loggedIn|authMethod'
[ "$BAD" = "0" ] && echo "ALL VALUE CHECKS PASSED" || echo "SOMETHING DOES NOT MATCH: see TROUBLESHOOTING"
SH
chmod +x .scratch/check-values.sh
echo written
```
Expect: `written`.

### A14. Remove any old drill containers, volumes and responder state
```bash
docker compose down --volumes --remove-orphans
rm -rf .scratch/responder-state .scratch/responder.pid .scratch/responder.log .scratch/cookie.txt
echo clean
```
Expect: `clean` (earlier lines may say nothing to remove).

### A15. Check no other container holds a drill port
```bash
docker ps --format '{{.Names}}  {{.Ports}}' | grep -E ':(3000|8000|8025|9090|9099|1025|4317|3100|3200)->' || echo "no port conflicts"
```
Expect: `no port conflicts`. A listed container: `docker stop <name>`, then repeat A15.

### A16. Download the images
```bash
docker compose pull db otel-collector prometheus tempo loki grafana mailhog
```
Expect: ends without an error. Wait: 2 to 10 minutes.

### A17. Build the app images
```bash
docker compose build backend migrations webhook-sink
```
Expect: ends without an error. Wait: 3 to 10 minutes the first time.

### A18. Copy the Grafana password to the Windows clipboard (without showing it)
```bash
grep '^GRAFANA_ADMIN_PASSWORD=' .env | cut -d= -f2- | tr -d '\n' | clip.exe && echo copied
```
Expect: `copied`. Do not paste it anywhere yet.

---

## PART B: the recording

### B1. Arrange the screen and start recording (Windows side: OBS or Game Bar)
Terminal 1 (this one), a second terminal for the log (B9), and browser tabs open to: `http://localhost:3000`, `http://localhost:8025`, `http://localhost:9090`, and your GitHub repo pull requests.
Expect: all visible; recording running.

### B2. Show the date and commit
```bash
date
git log --oneline -1
```
Expect: today's date and the latest commit line.

### B3. Start everything except Grafana
```bash
docker compose up -d --wait --wait-timeout 300 db migrations otel-collector prometheus tempo loki mailhog webhook-sink backend
```
Expect: it returns to the prompt with no error. Wait: up to 2 minutes (the command itself waits and stops with an error after 5).

### B4. Show the containers
```bash
docker compose ps
```
Expect: `db` and `backend` `healthy`; `migrations` `exited (0)`; the others `running`. Evidence: screenshot.

### B5. Wait for the metric to exist in Prometheus
```bash
for i in $(seq 1 60); do curl -fsS 'http://localhost:9090/api/v1/query?query=vt_top_tier_notification_overdue' | grep -q '"result":\[{' && { echo "metric present after $((i*5))s"; break; }; sleep 5; done
```
Expect: `metric present after 5s` to `75s`. Wait: up to 75 seconds (metric export every 60 s plus a 15 s scrape; gives up after 300 s).

### B6. Start Grafana (last, so no "no data" alert fires)
```bash
docker compose up -d --wait --wait-timeout 300 grafana
```
Expect: returns to the prompt with no error. Wait: under 1 minute.

### B7. Show the planted defect is ON
```bash
docker compose exec -T backend sh -c 'echo "VT_DEMO_DEFECT=$VT_DEMO_DEFECT VT_FEEDS=$VT_FEEDS RESPONDER_MODE=$RESPONDER_MODE"'
```
Expect: `VT_DEMO_DEFECT=notify_no_fix VT_FEEDS=fixtures RESPONDER_MODE=stub`. Evidence: screenshot.

### B8. Start the real responder in the background (before the asset; Grafana sends the alert only once)
```bash
bash .scratch/start-responder.sh
```
Expect: a prompt `GitHub token for the responder (hidden, not saved):`. Paste the responder GitHub token (nothing appears) and press Enter. Then: `responder up (pid NNNN); wrong bearer correctly refused with 401`. Wait: up to 60 seconds.

### B9. Second terminal: follow the responder log
Open a second terminal and paste:
```bash
cd ~/clone/vuln-triage
tail -n 20 -f .scratch/responder.log
```
Expect: a few log lines, no `Traceback`. Leave it on screen. Go back to Terminal 1.

### B10. OFF CAMERA (pause recording): check all values match
```bash
bash .scratch/check-values.sh
```
Expect: four `OK` lines; `responder: MODE=real MODEL=claude-sonnet-5-5 RUNTIME=cli API_URL=http://127.0.0.1:8000`; `ANTHROPIC_API_KEY: 0 chars`; `backend: VT_DEMO_DEFECT=notify_no_fix RESPONDER_MODE=stub VT_FEEDS=fixtures DEPLOYMENT_ENVIRONMENT=test`; a line containing `HTTP/1.1 401`; `loggedIn` true; last line `ALL VALUE CHECKS PASSED`. Any `MISMATCH` or a line without 401: go to TROUBLESHOOTING, do not continue. Resume recording.

### B11. Create the dashboard user
```bash
printf '%s\n' 'drill-not-a-secret' | docker compose exec -T backend python -m vulntriage.manage create-user --username drill-lead --display-name "Drill Lead" --email lead@drill.test --role "security lead"
```
Expect: `created user 'drill-lead' (id 1, role 'security lead')`.

### B12. Log in through the API
```bash
curl -sS -D .scratch/login.hdr -o /dev/null -X POST http://127.0.0.1:8000/auth/login -H 'Content-Type: application/json' -d '{"username":"drill-lead","password":"drill-not-a-secret"}'
grep -i '^set-cookie: vt_session=' .scratch/login.hdr | sed -E 's/^[Ss]et-[Cc]ookie: (vt_session=[^;]+).*/\1/' | tr -d '\r\n' > .scratch/cookie.txt
test -s .scratch/cookie.txt && echo "logged in, cookie saved" || echo "LOGIN FAILED"
```
Expect: `logged in, cookie saved`.

### B13. Register the failing asset (this starts the scan)
```bash
curl -sS -w '\nHTTP %{http_code}\n' -X POST http://127.0.0.1:8000/assets -H 'Content-Type: application/json' -H 'X-Requested-With: XMLHttpRequest' -H "Cookie: $(cat .scratch/cookie.txt)" -d '{"name":"pip-app","ownerName":"Owner","ownerEmail":"pip-owner@team.example","criticality":"high","internetFacing":true,"repositoryUrl":"https://github.com/fixture-owner/pip-app"}'
```
Expect: JSON with `"id":"1"` and `"name":"pip-app"`, then `HTTP 201`. Evidence: screenshot.

### B14. Confirm the scan found a top-tier finding with no fix
```bash
for i in $(seq 1 30); do curl -sS http://127.0.0.1:8000/findings -H "Cookie: $(cat .scratch/cookie.txt)" > .scratch/findings.json; grep -q '"package":"flask"' .scratch/findings.json && { grep -o '"id":"[0-9]*"\|"tier":"[^"]*"\|"fixedVersion":[^,}]*' .scratch/findings.json | head -n 6; break; }; sleep 4; done
```
Expect: lines including `"tier":"P1"` and `"fixedVersion":null`. Wait: a few seconds (gives up after 120 s).

### B15. Watch the metric reach 1
```bash
for i in $(seq 1 60); do out=$(curl -sS --get 'http://localhost:9090/api/v1/query' --data-urlencode 'query=vt_top_tier_notification_overdue == 1'); echo "$out" | grep -q '"result":\[{' && { echo "$out" | grep -o '"metric":{[^}]*}\|"value":\[[^]]*\]'; echo "metric = 1 after $((i*10))s"; break; }; sleep 10; done
```
Expect: a `"metric"` with `finding_id` and `"tier":"P1"`, a `"value"` ending `"1"`, then `metric = 1 after ...s`. Wait: about 1 to 2 minutes (delivery job fails within 30 s, metric export up to 60 s, scrape 15 s; gives up after 10 minutes).
Evidence (runbook step 2): in the browser open `http://localhost:9090`, query `vt_top_tier_notification_overdue == 1`, Table tab, screenshot showing value 1.

### B16. Show the Grafana alert
Browser: `http://localhost:3000`, user `admin`, paste the password (A18, Ctrl+V), then menu Alerting, Alert rules.
Expect: rule "Top-tier owner notification overdue" in state Firing with one instance showing the `finding_id`. Wait: up to 2 minutes after B15 (rule checks every 1 minute). Evidence (runbook step 3): screenshot.

### B17. Wait for the alert email
```bash
for i in $(seq 1 60); do n=$(curl -sS http://localhost:8025/api/v2/messages | grep -o '"total":[0-9]*' | head -n 1); echo "mailhog $n"; [ "$n" = '"total":1' ] && break; sleep 10; done
```
Expect: `mailhog "total":1` at the end. Wait: up to 2 minutes (gives up after 10 minutes).
Then browser `http://localhost:8025`: one email to `oncall@drill.test`, subject starting `[FIRING:1]`. Evidence (runbook step 3): screenshot the inbox and the open email. Do not expect an email to `pip-owner@team.example` yet.

### B18. Wait for the responder to open the pull request
```bash
for i in $(seq 1 80); do grep -E '"event": ?"(pull_request_opened|run_failed)"' .scratch/responder.log | tail -n 1 | cut -c1-400 | grep . && break; sleep 10; done
```
Expect: one log line with `"pull_request_opened"` and a `pull_request` URL. Wait: starts within seconds of the alert; the run is limited to 10 minutes plus checkout and push: allow up to 13 minutes (the Pro-plan duration is unverified). A `run_failed` line: see TROUBLESHOOTING. No line after 13 minutes: look at Terminal 2.
Evidence (runbook step 4): screenshot Terminal 2 showing `run_started` (with `model`), `branch_pushed`, `pull_request_opened`.

### B19. Open the pull request
Browser: open the `pull_request` URL from B18.
Expect: a PR from branch `responder/...` with a code fix and a new test in "Files changed". Evidence: screenshot.

### B20. Merge the pull request
Browser: click "Merge pull request", then confirm.
Expect: "Pull request successfully merged and closed". Evidence (runbook step 5): screenshot.

### B21. Turn the defect off in `.env`
```bash
sed -i 's/^VT_DEMO_DEFECT=.*/VT_DEMO_DEFECT=/' .env
grep '^VT_DEMO_DEFECT=' .env
```
Expect: `VT_DEMO_DEFECT=` (nothing after the equals sign).

### B22. Restart the backend with the defect off
```bash
docker compose up -d --force-recreate --no-deps --wait --wait-timeout 300 backend
docker compose exec -T backend sh -c 'echo "VT_DEMO_DEFECT=[$VT_DEMO_DEFECT]"'
```
Expect: `VT_DEMO_DEFECT=[]`. Wait: 30 to 60 seconds. Evidence: screenshot.

### B23. Wait for the owner email
```bash
for i in $(seq 1 40); do n=$(curl -sS http://localhost:8025/api/v2/messages | grep -o '"total":[0-9]*' | head -n 1); echo "mailhog $n"; [ "$n" = '"total":2' ] && break; sleep 10; done
```
Expect: `mailhog "total":2` at the end. Wait: 30 to 90 seconds (the failed job is retried at the delivery worker's next 30-second poll; gives up after 400 s).
Then browser `http://localhost:8025`: open the new email to `pip-owner@team.example`. Evidence (runbook step 6): screenshot.

### B24. Wait for the metric to return to 0
```bash
for i in $(seq 1 60); do out=$(curl -sS --get 'http://localhost:9090/api/v1/query' --data-urlencode 'query=vt_top_tier_notification_overdue == 1'); echo "$out" | grep -q '"result":\[\]' && { echo "no series at 1 after $((i*10))s"; break; }; sleep 10; done
curl -sS --get 'http://localhost:9090/api/v1/query' --data-urlencode 'query=vt_top_tier_notification_overdue' | grep -o '"value":\[[^]]*\]'
```
Expect: `no series at 1 after ...s`, then `"value"` lines ending in `"0"`. Wait: about 75 seconds (gives up after 10 minutes). Evidence: screenshot of Prometheus showing 0.

### B25. Show the resolved alert
Browser: Grafana, Alerting, Alert rules, refresh.
Expect: the rule state is Normal. Terminal 2 shows `alert_ignored` with `"outcome": "resolved"` and no new `run_started`. Wait: up to 5 minutes after B23 (rule check 1 minute, then notification at the 1-minute group interval). Evidence (runbook step 7): screenshot Grafana and Terminal 2.

### B26. Stop the recording and save the file
Expect: the video file exists. Upload it and add the link to the README placeholders and #163 (runbook step 8).

---

## PART C: cleanup (OFF CAMERA)

### C1. Stop the responder
```bash
kill "$(cat .scratch/responder.pid)" && echo "responder stopped"
```
Expect: `responder stopped`.

### C2. Stop the stack and delete its data
```bash
docker compose down --volumes --remove-orphans
```
Expect: containers, network and volumes reported `Removed`.

### C3. Empty `.scratch`
```bash
make clean-scratch
```
Expect: `.scratch/ is now empty`.

### C4. Remove the drill `.env`
```bash
rm -f .env
ls -a | grep '^\.env' || echo "no .env left"
```
Expect: `no .env left`, or only `.env.bak-<date>` (your old file: `mv .env.bak-<date> .env` to restore it).

### C5. Log out of Claude (only if this login was only for the drill)
```bash
claude auth logout
```
Expect: a logged-out message.

---

## TROUBLESHOOTING (find the exact text)

| You see | Do |
|---|---|
| `RESPONDER_WEBHOOK_SECRET is required` | `grep -c '^VT_RESPONDER_WEBHOOK_TOKEN=' .env` must print 1; start the responder only with `bash .scratch/start-responder.sh` |
| `RESPONDER_API_TOKEN is required` | `grep -c '^RESPONDER_API_TOKEN=' .env` must print 1; same script |
| `RESPONDER_MODE must be 'stub' in test and CI` | a `CI`, `GITHUB_ACTIONS` or `DEPLOYMENT_ENVIRONMENT=test` value reached the script; do not add them to `.env`; open a new terminal and repeat from A1 |
| `RESPONDER_GITHUB_TOKEN is required in real mode` | you pressed Enter on an empty token; run C1 then B8 again |
| `RESPONDER_GITHUB_REPO must be 'owner/name'` | re-run A12 |
| a line starting `the 'claude' CLI` | `claude auth login` with your Claude account, then `claude auth status` (A5); `ANTHROPIC_API_KEY` must not be set; then B8 |
| `required variable ... is missing a value` or `set VT_RESPONDER_WEBHOOK_URL` | you are not in `~/clone/vuln-triage`, or `.env` is missing: `cd ~/clone/vuln-triage`, redo A8 |
| `compose.drill-defect.yaml: no such file` | redo A10 |
| `password authentication failed` | old database volume: `docker compose down --volumes`, then redo B3 |
| backend exits with `VT_DEMO_DEFECT=notify_no_fix is refused unless DEPLOYMENT_ENVIRONMENT` | `grep '^COMPOSE_FILE=' .env` must match A8 exactly |
| B10 `MISMATCH grafana container` | `docker compose up -d --force-recreate --no-deps grafana`, repeat B10 |
| B10 `MISMATCH responder process` or `responder is not running` | C1, then B8, then B10 |
| B10 grafana line `can't connect to remote host` or `refused` or `timed out` | responder not running or Windows/host firewall blocks port 9100: allow it, `ss -ltn | grep 9100` must show `0.0.0.0:9100`, repeat B10 |
| B10 grafana line `bad address 'host.docker.internal'` | redo A10, then `docker compose up -d --force-recreate --no-deps grafana`, repeat B10 |
| B10 grafana line `HTTP/1.1 404` or `403` | another program uses port 9100: `ss -ltnp | grep 9100`, stop it, C1, B8 |
| B10 grafana line `no answer line` | run `curl -s -o /dev/null -w '%{http_code}\n' -X POST http://127.0.0.1:9100/webhook/grafana -H 'Authorization: Bearer wrong' -d '{}'`: `401` means the responder is fine; report the Grafana line to the orchestrator |
| Grafana contact point error `401` or `Unauthorized` | repeat B10 and fix the `MISMATCH` line |
| Grafana contact point error `connection refused` or `no such host` | see the B10 grafana-line rows above |
| B14 prints nothing | `curl -sS -o /dev/null -w 'rescan HTTP %{http_code}\n' -X POST http://127.0.0.1:8000/assets/1/rescan -H 'X-Requested-With: XMLHttpRequest' -H "Cookie: $(cat .scratch/cookie.txt)"` must print `rescan HTTP 202`, then repeat B14 |
| B15 never reaches 1 | repeat B7 (must be `notify_no_fix`) and B14 (must show `"fixedVersion":null`); `docker compose logs --tail 50 backend` |
| B17 stays at `"total":0` while the metric is 1 | `docker compose logs --tail 50 grafana`; Alerting, Contact points in Grafana |
| `plan_usage_limit` (in `run_failed`) | Pro allowance used up: wait for the reset (`/usage` in `claude`), then use the replay block below |
| `max_turns` | C1; add the line `RESPONDER_MAX_TURNS=40` at the end of `.env` (the script reads it); B8; replay |
| `agent_timeout` | C1; add the line `RESPONDER_RUN_TIMEOUT_SECONDS=900` at the end of `.env`; B8; replay |
| `push_failed` or `pull_request_create_failed` | the GitHub token lacks push or pull-request rights: fix the token, C1, B8, replay |
| other `run_failed` `reason` (`diff_path_*`, `no_commits`, `too_many_commits`, `agent_escalated`, `output_unparseable`, `result_line_missing`, `agent_cli_error`, `cli_exit_nonzero`, `checkout_failed`, `install_failed`) | replay once; if it fails again, stop and send the `reason` (meanings: `_docs/responder-cli-runtime.md`) |
| `retry_cap_reached` or `alert_ignored` with `"outcome": "repeat"` | C1; `rm -rf .scratch/responder-state`; B8; replay |

Replay the alert to the responder (Grafana does not resend it). Copy `fingerprint` and `finding_id` from the `run_failed` line in `.scratch/responder.log` into the two lines marked below, then paste (unverified; body shape from `tests/compose_responder.py`):
```bash
FP=PASTE_FINGERPRINT_HERE
FID=PASTE_FINDING_ID_HERE
WH=$(grep '^VT_RESPONDER_WEBHOOK_TOKEN=' .env | cut -d= -f2-)
curl -sS -X POST http://127.0.0.1:9100/webhook/grafana -H "Authorization: Bearer $WH" -H 'Content-Type: application/json' -d "{\"status\":\"firing\",\"alerts\":[{\"status\":\"firing\",\"fingerprint\":\"$FP\",\"labels\":{\"finding_id\":\"$FID\",\"tier\":\"P1\"}}]}"
unset WH
```
Expect: `{"results":[{"fingerprint":"...","outcome":"accepted"}]}` and a new `run_started` in Terminal 2.

## Value map (reference)

| Variable | Where it is set | Who reads it |
|---|---|---|
| `POSTGRES_PASSWORD` | `.env` | `compose.yaml` db, migrations, backend |
| `GRAFANA_ADMIN_PASSWORD` | `.env` | Grafana (required by `observability/compose.yaml` and `compose.alert.yaml`) |
| `RESPONDER_API_TOKEN` | `.env` | backend; the responder script uses the same value |
| `VT_RESPONDER_WEBHOOK_TOKEN` | `.env` | Grafana; the script copies it to `RESPONDER_WEBHOOK_SECRET` |
| `VT_RESPONDER_WEBHOOK_URL`, `VT_ALERT_HUMAN_EMAIL` | `.env` | `compose.alert.yaml` (required) |
| `MAIL_SENDER` | `.env` | Grafana SMTP sender |
| `VT_DEMO_DEFECT` | `.env` | backend, through `.scratch/compose.drill-defect.yaml` |
| `LLM_MODE`, `RESPONDER_MODE` (`stub`) | `.env` | `compose.yaml` backend only |
| `COMPOSE_PROJECT_NAME`, `COMPOSE_FILE` | `.env` | Docker Compose |
| `VT_FEEDS=fixtures`, `DEPLOYMENT_ENVIRONMENT=test` | `compose.telemetry.yaml` (fixed) | backend; not in `.env` on purpose (the responder refuses real mode when `DEPLOYMENT_ENVIRONMENT=test`) |
| `RESPONDER_MODE=real`, `RESPONDER_RUNTIME`, `RESPONDER_MODEL`, `RESPONDER_API_URL`, `RESPONDER_GITHUB_REPO`, `RESPONDER_STATE_FILE` | `.scratch/start-responder.sh` | the responder only |
| `RESPONDER_GITHUB_TOKEN` | typed at the hidden prompt in B8 | the responder only; never written to a file |
