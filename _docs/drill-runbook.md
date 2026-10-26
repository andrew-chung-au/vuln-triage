# On-call drill and evidence-capture runbook (owner-run)

Runbook for issue [#163](https://github.com/andrew-chung-au/vuln-triage/issues/163)
(task 39). You run every step on a Docker host that is **not** the sandbox; an
agent cannot (it needs your key, token, and a live Compose stack).

This runbook does two jobs in one sitting:

1. **The recorded alert-to-fix drill** — the On-Call Agent evidence (rubric
   criterion 12, the only one below maximum).
2. **Close the "hard to see" soft spots** the rubric audit flagged, so a strict
   grader cannot dock Observability (10) or CI/CD (9): re-capture the dashboard
   after the filter change, capture the metric→trace leg, and re-screenshot the
   `protect-main` required checks.

Do them in this order; the drill is the long part.

## Prerequisites (must be true before you start)

- [ ] **F4 done** — model pinned: `claude-sonnet-5-5` via `RESPONDER_MODEL` (decided 2026-10-26).
- [ ] **#221 live SDK wiring done** — `build_default_session` wired to the Claude
      Agent SDK (the fake-SDK scaffold alone is not enough for a real fix).
- [ ] **#222 done** — the fine-grained responder token exists and the
      refused-push proof is recorded on #160 (`_docs/responder-token-proof.md`).
- [ ] **#161 done** — the `responder` job is in `verify.yml` and `P-FLAG-GONE` is in place.
- [ ] Your local `.env` has `ANTHROPIC_API_KEY` and the responder GitHub token
      (never committed; agents cannot read `.env`). Set a small spend cap on the
      Anthropic key first.

## Part 1 — the recorded alert-to-fix drill

Record the screen for this whole part (screenshots at each ✓, or a short video).

1. [ ] Bring up the full local stack with the **real** responder runtime
   (`RESPONDER_MODE=real`, not `stub`) and `VT_DEMO_DEFECT=notify_no_fix` on, over
   the recorded fixtures. Use the Compose command from the responder job
   (`compose.yaml` + `compose.telemetry.yaml` + `compose.alert.yaml` +
   `compose.responder.yaml`). Wait for all containers healthy.
2. [ ] **Metric reaches 1.** The no-fixed-version top-tier finding's notification
   job fails; `vt_top_tier_notification_overdue` goes to 1 in Prometheus/Grafana.
   ✓ capture the metric at 1.
3. [ ] **Exactly one alert, naming the finding.** The US-14 rule fires one alert
   carrying the finding id. ✓ capture the alert (Grafana Alerting) and the owner
   email arriving in MailHog.
4. [ ] **The responder opens a real PR.** The real runtime wakes on the webhook,
   reproduces the defect, writes a failing test, fixes the code, and opens a pull
   request on `responder/<fingerprint>`. ✓ capture the PR on GitHub (showing the
   fix + the test + the alert link) and the responder action log
   (`docker compose logs responder` — note the logged **model** field; it should
   read the model the API served).
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
- [ ] Delete `.scratch/` contents (`make clean-scratch`); keep the key and token
      in `.env` only.

## What this closes

- Criterion 12 (On-Call Agent) 0 → 2: a real agent woke on the alert and fixed
  the issue, recorded.
- Criterion 10 (Observability): the dashboard screenshot matches the current
  JSON; the metric leg is shown or honestly captioned; the trace→logs link tried.
- Criterion 9 (CI/CD): the required status checks are visible in the ruleset.
