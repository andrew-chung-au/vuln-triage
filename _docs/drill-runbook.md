# On-call drill and evidence-capture runbook (owner-run)

Runbook for issue [#163](https://github.com/andrew-chung-au/vuln-triage/issues/163)
(task 39). You run every step on a Docker host that is **not** the sandbox; an
agent cannot (it needs your Claude login, your token, and a live Compose stack).

This runbook does two jobs in one sitting:

1. **The recorded alert-to-fix drill** — the On-Call Agent evidence (rubric
   criterion 12, the only one below maximum).
2. **Close the "hard to see" soft spots** the rubric audit flagged, so a strict
   grader cannot dock Observability (10) or CI/CD (9): re-capture the dashboard
   after the filter change, capture the metric→trace leg, and re-screenshot the
   `protect-main` required checks.

Do them in this order; the drill is the long part.

> **Running it?** For the video, follow only
> [`_docs/drill-video-steps.md`](drill-video-steps.md): the single, copy-paste
> step list (it supersedes Part 1 step 1 below and the older
> `drill-runbook-commands.md`). This file stays the checklist and the *why*.

## Prerequisites (must be true before you start)

- [ ] **F4 done** — model pinned: `claude-sonnet-5-5` via `RESPONDER_MODEL` (decided 2026-10-26).
- [ ] **#260 done** — the `cli` runtime (headless `claude -p` on your own Claude
      login; the runner pushes and opens the PR). This replaces the API-key route
      (#221's Agent SDK session stays in the code but is not used for the drill).
- [ ] **Claude Code installed and logged in on the host that runs the responder**
      (not in a container): `claude auth status` must exit 0 with `authMethod`
      `claude.ai` (or `oauth_token`). The responder checks this at start-up and
      refuses to start otherwise. Do **not** put `ANTHROPIC_API_KEY` in the
      responder's environment; the responder removes it from the CLI's environment
      anyway, so it can never bill the API. Read `_docs/responder-cli-runtime.md`
      for the `VERIFY:` items that this first live run settles.
- [ ] **Plan allowance.** On the **Pro** plan a run draws on your plan's usage
      limits (not dollars), and a run that hits the limit ends as a failed run
      (`plan_usage_limit` in the action log), after which Grafana's repeat
      notification retries it (up to `RESPONDER_MAX_FAILED_RUNS`). Start the drill
      with a fresh allowance (check `/usage` in Claude Code), keep
      `RESPONDER_MAX_TURNS` modest (the default is 30), and do not run other heavy
      Claude Code work in the same hours.
- [ ] **#222 done** — the fine-grained responder token exists and the
      refused-push proof is recorded on #160 (`_docs/responder-token-proof.md`).
- [ ] **#161 done** — the `responder` job is in `verify.yml` and `P-FLAG-GONE` is in place.
- [ ] Your local `.env` has the responder GitHub token and `RESPONDER_RUNTIME`
      left empty or `cli` (never committed; agents cannot read `.env`). The token is
      used only by the responder's own git push and PR call, never by the agent.

## Part 1 — the recorded alert-to-fix drill

Record the screen for this whole part (screenshots at each ✓, or a short video).

1. [ ] Bring up the stack with the **real** responder **on the host**, not in
   Compose. The Compose `responder` service (`compose.responder.yaml`) is
   **stub-only**: it is built from the backend image, which has no `claude` CLI, no
   login and no GitHub token (it passes none of the real-mode settings through), so
   a real start there cannot run an agent. So:
   - Start the rest of the stack with `VT_DEMO_DEFECT=notify_no_fix` on, over the
     recorded fixtures (`compose.yaml` + `compose.telemetry.yaml` +
     `compose.alert.yaml`), **without** `compose.responder.yaml` (it would also hold
     port 9100). Wait for all containers healthy.
   - Run the real responder from the `responder/` project on the host, as the user
     whose Claude login you want to use, with `RESPONDER_MODE=real`,
     `RESPONDER_MODEL=claude-sonnet-5-5`, the webhook secret
     (`RESPONDER_WEBHOOK_SECRET` = the value of `VT_RESPONDER_WEBHOOK_TOKEN`),
     `RESPONDER_API_TOKEN`, `RESPONDER_API_URL` pointing at the backend as the host
     sees it (VERIFY: `http://127.0.0.1:8000` if the backend publishes that port),
     `RESPONDER_GITHUB_TOKEN` and `RESPONDER_GITHUB_REPO`, for example
     `responder/.venv/bin/uvicorn vt_responder.app:create_app_from_env --factory
     --host 0.0.0.0 --port 9100` from the `responder/` directory with those
     variables exported (there is no `make` target for this yet; see the proposal in
     the #260 comment). It must listen on an address Grafana's container can reach,
     so not `127.0.0.1`.
   - Point Grafana at it: set `VT_RESPONDER_WEBHOOK_URL` to
     `http://172.17.0.1:9100/webhook/grafana`. On Linux, `172.17.0.1` is the
     default Docker bridge gateway address (the host as seen from a container on the
     default bridge); on a Compose project network the gateway differs, and Docker
     Desktop uses `host.docker.internal`. VERIFY: check with
     `docker network inspect <network>` and from inside the Grafana container, and
     allow the port through any host firewall.
   - A start-up message beginning "the 'claude' CLI" means the preflight failed
     (not installed, too old, not logged in, or not a subscription login); fix it
     and start again.
2. [ ] **Metric reaches 1.** The no-fixed-version top-tier finding's notification
   job fails; `vt_top_tier_notification_overdue` goes to 1 in Prometheus/Grafana.
   ✓ capture the metric at 1.
3. [ ] **Exactly one alert, naming the finding.** The US-14 rule fires one alert
   carrying the finding id. ✓ capture the alert (Grafana Alerting) and the owner
   email arriving in MailHog.
4. [ ] **The responder opens a real PR.** The real runtime wakes on the webhook
   and runs one `claude -p` in a fresh checkout; the agent reproduces the defect,
   writes a failing test, fixes the code and commits locally. The **runner** then
   checks the commits (diff gate), pushes `responder/<fingerprint>` and opens the
   pull request. ✓ capture the PR on GitHub (showing the fix + the test) and the
   responder action log (the responder's standard output on the host — note the
   logged **model** field, and the `branch_pushed` and `pull_request_opened`
   events). A run that ends in `run_failed` carries a short `reason`
   (`plan_usage_limit`, `agent_timeout`, `max_turns`, `diff_path_*`, ...); see
   `_docs/responder-cli-runtime.md`.
5. [ ] **You merge** the PR (the responder cannot — `main` is protected). ✓ capture the merge.
6. [ ] **Delivery retried; owner mail arrives.** Recreate the backend with the
   defect off, let the next delivery attempt succeed; the owner notification
   reaches MailHog. ✓ capture the delivered mail.
7. [ ] **Metric back to 0; alert resolves.** ✓ capture the resolved alert.
8. [ ] Save the recording, upload it, and put the link in the README placeholders
   (the two `<!-- PLACEHOLDER ... -->` blocks: "Demo recording" near the rubric
   table, and under "Observability evidence") and in #163.
9. [ ] **Cleanup (#161, `P-FLAG-GONE`).** Remove the `VT_DEMO_DEFECT` path with the
   task-29 cleanup commit; confirm `P-FLAG-GONE` passes. Do this **before** any
   production promotion.

## Part 2 — protect Observability (criterion 10), same sitting

The dashboard JSON changed after the committed screenshots (the Environment and
Version filters were removed) and has not been loaded in Grafana since. Close that:

1. [ ] Load `observability/grafana/dashboards/us13-journey.json` in the live
   Grafana once and confirm the US-13 dashboard still renders all three panes
   (metric / Tempo traces / Loki logs). ✓ re-capture the dashboard in **view
   mode** to replace `docs/images/g9-grafana-dashboard-dev-local.png` (so the
   committed screenshot matches the current JSON, with no stale dropdowns).
2. [ ] **Metric→trace leg.** Either capture a view showing the metric's exemplar
   (the dot on the panel linking to a trace) or a metric→trace click-through. If
   you cannot get the exemplar to show in the UI, the README already states the
   leg is CI-asserted — leave that note as the evidence.
3. [ ] **Trace→logs link.** From the Tempo trace, try the "Logs for this span"
   link to Loki. ✓ capture it if it works.

## Part 3 — protect CI/CD (criterion 9), two minutes

1. [ ] Open GitHub → Settings → Rules → `protect-main`, **expand** the "Require
   status checks to pass" section so the required check names are visible. ✓
   re-capture to replace/supplement `docs/images/g5-github-settings-rulesets-protect-main.png`,
   so a grader can see which checks gate the merge.

## After the sitting

- [ ] The rubric auditor re-audits `main` and updates `_docs/rubric-evidence.md`
      (auditor-only — the Engineer does not edit it) toward all 12 criteria MET.
- [ ] Keep the nightly stop **off** until after grading (it takes the public URL
      down and breaks criterion 8).
- [ ] Delete `.scratch/` contents (`make clean-scratch`); keep the token in `.env`
      only. Stop the host responder. If you used a throwaway `HOME` for the drill,
      the Claude login in it can be removed with `claude auth logout`.

## What this closes

- Criterion 12 (On-Call Agent) 0 → 2: a real agent woke on the alert and fixed
  the issue, recorded.
- Criterion 10 (Observability): the dashboard screenshot matches the current
  JSON; the metric leg is shown or honestly captioned; the trace→logs link tried.
- Criterion 9 (CI/CD): the required status checks are visible in the ruleset.
