# Issue #159 (task 27): the `alert` Compose test and CI job (US-14 A-* cases)

**Date:** 2026-10-24
**Branch:** `feat/159-alert-compose-job` (cloud session — commit on this branch, do not push/merge)
**Environment:** Kiro cloud sandbox. No Docker socket; PyPI/npm blocked (npm 403) and uv's Python download refused (read-only home), so no 3.12 venv can be built and `make verify`/pytest cannot run here. System Python is 3.11.

## Scope (orchestrator defaults, carried to the human as decisions)

- **SCOPE:** the `alert` job only. `I-OWNER-SENDER` MailHog form and `T-E6` stay follow-ups (Out of scope in #159).
- **FIRING-STATE SEAM:** an in-container `manage.py` command that creates a `top tier` NotificationJob in a named state (failed / pending-backdated / sent / held) with set created_at/sent_at/tier, committed to the gauge's Postgres — firing from **stored job state**, not simulated.
- **STUB WEBHOOK SINK:** stdlib `http.server` recorder run from the backend image already in the stack — **no new image/dependency**.

## What shipped (committed on this branch)

- `backend/vulntriage/manage.py` — the firing-state seam: `alert-seed` / `alert-set` / `alert-rescore` / `alert-clear`. `alert-seed` builds a self-contained finding→lifecycle→`top tier` job directly in stored state, with a chosen recorded `NotificationJob.tier`, a backdated `created_at` (`--age-minutes`) and optional `sent_at` (`--sent-age-hours`), committed to the same Postgres `compute_overdue_series` reads. `alert-set` drives a finding's job to a state (e.g. `sent` for A-RESOLVE). `alert-rescore` changes the finding's current tier (recorded job tier must win). `alert-clear` removes seeded rows between cases. Test/harness only; never touches `_OVERDUE_WINDOW` (W = 30 min, A33).
- `tests/alert_webhook_sink.py` — the stub responder sink (stdlib): records each POST; `GET /__recorded|/__reset|/__health`.
- `tests/compose_alert.py` — alert helpers: the in-container seam runner (`docker compose run -T --rm backend python -m vulntriage.manage alert-*`), the webhook-sink client + `webhook_finding_ids`, overdue-series polling, MailHog-by-recipient, Collector stop/start for A-GAP; reuses `compose_telemetry.py`'s `_poll`/Prometheus/MailHog.
- `tests/test_compose_alert.py` — `compose`-marked A-* cases: A-FIRE (both sinks, payload = finding_id + tier only), A-FIRE negative (rule-absent harness pass), A-HELD, A-TIER, A-GAP part 1 + part 2 (NoData → human-only), A-RESOLVE (resolution ≠ second alert).
- `tests/test_manage.py` — SQLite/unit cases for the seam cross-checked against `compute_overdue_series` (so the seam is covered under `make test`, no Docker).
- `tests/test_marker_hygiene.py` — `test_compose_alert.py` added to the allowlist.
- `compose.alert.yaml` — override layered on `compose.yaml` + `compose.telemetry.yaml`: Grafana SMTP→MailHog, the `webhook-sink` service (backend image, command swapped), the alert env, and the rule-absent provisioning toggle (`VT_ALERT_PROVISIONING`). Does **not** edit `observability/compose.yaml`.
- `ci/test-compose.sh` — the `alert` branch now brings the stack up and runs the A-* cases + the rule-absent negative pass; `responder` still returns the not-implemented message.
- Docs: this summary, `_docs/ai-usage-log.md`, `_docs/roadmap.md` check-in, `_docs/pending-verification.md` #159.

## Uncommitted — needs human approval

- `.github/workflows/verify.yml` — the new `alert` job (mirrors `telemetry`). Left in the working tree; the exact diff is in the Engineer comment under "Proposed protected-file change". Not committed with `HUMAN_APPROVED=1` because a subagent cannot obtain approval mid-run.
- The `Makefile` already wires `COMPOSE_JOBS=alert` — confirmed, no Makefile change.

## Verification

`make verify` **could not run in this sandbox** (PyPI/uv-python/npm blocked, read-only home; Python 3.11 vs the project's ≥3.12). Offline checks done instead (all pass):
- `python3 -m py_compile` on every new/changed Python file; `bash -n ci/test-compose.sh`; `make -n test-compose JOB=alert`.
- `.scratch/check_alert_159.py` (read-only + a loopback port it starts/stops): the firing-state decision table (a standalone copy of `_series_value`) confirms the seam's states/backdating map to the 0/1/None the overdue gauge emits, plus the recorded-tier-wins invariant; and the stub webhook sink end-to-end — POST a Grafana-shaped firing body, read `/__recorded`, confirm `webhook_finding_ids` / `_is_firing` / `/__reset`.
- `.scratch/check_marker_hygiene.py`: `compose` appears only in the two allowed modules.

The alert cases are `compose`-marked and **deselected** by `make test`/`make verify` (`-m "not compose"`), so they never run or skip in the no-Docker gate; the seam's own logic is covered under `make test`. **BASE for verify = `1c43045`** (the commit before this branch's first #159 commit; `git rev-parse <first commit>^`). The human/CI runs `make verify` and `make test-compose JOB=alert` under Docker; VERIFY points are in `_docs/pending-verification.md` #159.

## Choices the issue does not cover

1. The seam creates a deterministic self-contained finding→lifecycle→job chain (Q2 option A) rather than driving a real pygoat P1 over HTTP — either is valid per the issue; the SET-state + backdate seam is required regardless.
2. A-FIRE negative = a provisioning COPY with the rule file removed, selected by `VT_ALERT_PROVISIONING`, recreated with `up --force-recreate --no-deps grafana`, driven by `VT_ALERT_RULE_ABSENT=1` in a second pass; the committed provisioning tree is untouched.
3. The stub sink builds from the same `./backend` context (reuses the backend image), module bind-mounted at `/sink`, `PYTHONPATH=/sink`.
4. `compose.alert.yaml` overrides the imported `grafana` service (env + volumes) via a third `-f` file — supported on current Compose (compose-go PR #559); VERIFY-marked for pinned CI versions with a documented fallback.

## No new dependency

The seam is in the existing `manage.py`; the sink + helpers are stdlib; the sink runs from the backend image already in the stack. `backend/uv.lock` unchanged.
