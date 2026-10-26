# Issue #232: responder guard forgets a fingerprint on `resolved` (task 28c-A of #160); also the #225 sweep, CC11 and the #220 split

**Date:** 2026-10-26
**Spec version:** 76c73f7

## What changed and why

The owner asked for the highest-value human verification chunk, then asked why the agent could not do it, then asked for the next task the agent could do alone. Four pieces of work followed.

- **#225 close-out sweep, done by the agent.** The Actions record was checked through the GitHub tools (telemetry log "3 passed in 61.07s" in run 40291587781, runs 40188742150, the two T-REFUSE negative checks 40073386642 and 40073409867, alert run 40226288166, dev deploy run 40291937292 for the image digests, and the `skipif` pair in `tests/test_compose_alert.py`). #157, #174 and #141 were closed with the evidence on each. #172 was closed after a QA re-check passed (6411988890). #225 itself is not ticked or closed.
- **CC11.** Juice Shop commits no `package-lock.json`; NodeGoat commits one at `lockfileVersion` 2 with a `packages` key, which the parser accepts. `deploy/pilot-seed.json` now lists NodeGoat only (plus the two `REPLACE_ME` entries that are the owner's). Read from github.com and the first lines of the raw file; the file was not run through the parser.
- **#220 grooming and split.** The PM groomed #220 (comment 6412133802) and recommended three issues; the owner chose that. Created #232 (this issue) and #233 (`P-DEMO-BE`, run twice), both under #160, and narrowed #220 to the Compose wiring.
- **#232.** The repeat-fingerprint guard now forgets a fingerprint when its alert resolves. A `resolved` that arrives while a run is in flight defers the release until the run finishes; a firing that arrives after the deferred resolved cancels the deferred release; a run that errors or raises still releases. QA PASS (6412775111).

- **#234 (follow-up to #232), same session.** QA's risk that no test made the runner raise became #234, narrowed at the owner's request to the raise-path test only; the `_save()` failure modes and restart loss became future-development item X12 in `_docs/roadmap-future.md`. Engineer `6f4792b` added `test_hook_run_that_raises_releases_the_fingerprint_and_clears_in_flight` (the webhook answers 500, the fingerprint is released, in-flight is cleared, a later firing runs). Mutation check done twice (the Engineer in place, QA on a copy): removing the `finally` makes it fail. QA PASS (6413284562), assert clean PASS. Pull request: https://github.com/andrew-chung-au/vuln-triage/pull/235.

- **#220 (Compose wiring), same session.** Engineer commits `d53438f`, `b97f714`, `ea3eee8`, `91b61a4`: `compose.responder.yaml` (no new image: built from `./backend` with the source bind-mounted), the `responder` branch of `ci/test-compose.sh`, a static compose-file test, eight `compose`-marked cases (written, NOT run: no Docker here) and the `tasks.md` 28/29 wording. QA (6413501579): the [V] criteria PASS (static checker mutated on a copy: all 10 mutations caught), the [D] criteria UNVERIFIED. Decision point (owner, 2026-10-26): the real-Grafana-body criterion is amended to a `claimed` backdated job; a one-line comment fix in the protected `Makefile` was approved and committed as `5173c20` (record on #220, comment 6413563367); QA's two test-quality risks parked as X13. #220 stays open until the Docker-host run, listed in #226 and `pending-verification.md` §#220.

## Files created or modified

- Responder: `responder/vt_responder/guard.py` (`resolve`, `finish`, in-memory in-flight and deferred sets), `responder/vt_responder/app.py` (resolved calls `guard.resolve`; the run is wrapped in try/finally calling `guard.finish`), `responder/tests/test_webhook.py` (new cases).
- Docs: `_docs/testing.md` (`I-RESP-HOOK-REPEAT`, `I-RESP-HOOK-RESOLVED`), `_docs/pending-verification.md`, `_docs/human-tasklist.md`, `_docs/cloud-tasklist.md` (CC11 row), `_docs/aws-setup.md` (A13 step 2), `_docs/roadmap.md`, `_docs/ai-usage-log.md`, this summary.
- Deploy: `deploy/pilot-seed.json`.
- GitHub, outside the diff: comments and closes on #157, #174, #141 and #172; created #232 and #233; edited the body of #220 and commented on it.
- No protected file changed.

## Decisions made by the human

- Asked the agent to run the #225 sweep itself, and to do the #172 QA re-check and the doc tidy (2026-10-26).
- Asked the agent to do the next task without them; accepted both the #220 draft and CC11.
- Chose option 1 of the PM's split question: three issues (#232, a narrowed #220, #233).
- Not asked, and so not decided: the PM's point that a second Compose service built from the existing backend Dockerfile is not a "new image". The PM's default stands unless the owner objects; this was stated in the question and on #220.

## Mismatches with the spec or design docs

none new. Earlier ones still open: `architecture.md` A34 and `roadmap.md` S4/C6 still describe the responder runtime as open (F2 settled it); `_docs/tasks.md` tasks 28/29 both claim the `responder` CI job (#220 is to align the wording).

## Commands to validate

- **Verify:** `make verify` (PASS at the end: frontend 89, backend 515, responder 76).
- **Test (responder):** `make responder-test` (76 passed).

## Proposed AGENTS.md changes

none.

## Temporary changes

- `make install` ran in this session (the `responder/.venv` was missing, so `make verify` failed until it was installed). It installs from the lockfiles into git-ignored directories (`frontend/node_modules`, `backend/.venv`, `responder/.venv`); left in place.
- No processes were started and no system configuration was changed. `.scratch/` was emptied with `make clean-scratch` at the end.

## Permission review

- Read-only (propose allowing): none of the role comments reported an approval. The orchestrator's `make install` (network; installs into git-ignored directories; no matched `ask` rule recorded).
- Writes to the record (keep asking): GitHub issue comments, issue creation, the #220 body edit and issue closes through the GitHub tools; `make issue-comment` posts by the PM, Engineer and QA roles; `git push -u origin claude/funny-dijkstra-svm6xw` (cloud session branch, several pushes); `HUMAN_APPROVED=1 git commit` for the protected `Makefile` comment change `5173c20` (matched `ask` rule, owner approved the exact diff; record on #220, comment 6413563367); opening PR #235.
- Risky (propose denying): none. A web-fetch subagent read public GitHub pages for CC11 (no approval requested). The PM's report notes it used `cat backend/Dockerfile` for a file read (a convention slip, no approval needed).
- Role comments without an approvals line: the PM's #220 comment states "none"; the #232 Engineer comment and the #232 and #172 QA comments state "none". The CC11 fetch had no comment.

## Interruptions

- The container was restarted mid-session and the GitHub tool server disconnected and reconnected. The PM's finished report was recovered from its hand-back message and from `.scratch/pm-220-groomed.md` (still present). Nothing was left half-done: no commit or issue was in a partial state.

## Unrelated problems noticed but not fixed

QA's risks on #232, none changing its verdict:
- No test makes `runner.run` raise, so the new try/finally release is untested (removing the `finally` would leave every test green).
- If `_save()` raises inside `claim`, the fingerprint stays in memory as in flight and a later resolved defers forever until a restart.
- If `_save()` raises inside `finish`, the exception replaces the run result.
- The in-flight and deferred state is in memory only, so a restart mid-run drops a pending release (relevant to #221).
- `compose.yaml` does not pass `VT_DEMO_DEFECT` through; #220's criteria add it.
- Flake #185 (Tempo drops leading zeros in trace ids) can fail `T-JOURNEY-BE` about 1 run in 16.

## Follow-ups for the next session

- #220 (Compose wiring): can be written in a cloud session but only proven on a Docker host or CI; no new image is needed per the PM.
- #233 (`P-DEMO-BE`): starts only after #232 and #220 are green in a recorded run.
- A test that makes the runner raise (the untested `finally`), and a decision on the `_save()` failure modes, if the owner wants them.
- #225 is left for the owner to tick and close. #229 (owner decisions) and #222 (token) are unchanged.
- Run `make test-compose JOB=responder` on a Docker host once #220 is built.
