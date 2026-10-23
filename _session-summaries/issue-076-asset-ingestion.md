# Issue #76: Asset registration and repository ingestion (IN PROGRESS, handover)

**Date:** 2026-10-23
**Spec version:** 9b04f90

This is a handover note written mid-issue because the weekly usage limit was near. Update it as the issue moves; replace it with the final summary at close-out (process step 8).

## State when written

- #26 closed (QA PASS at `8ec6313`; summary `issue-026-data-model-sqlite.md`).
- #112 (push-check image) implemented and QA PASS on the static criteria; OPEN until the human finishes the guide `_docs/push-check-image-guide.md`: the human built the image, the plan-mode dry run showed `make -C . install verify`, and the real push (step 7) was about to run or has run. Still to report: step 8 (broken-install check) and the step 9 report. Then the orchestrator closes #112 (summary `issue-112-push-check-image.md` is already committed).
- #76 groomed by the PM: comment 6357191954 (https://github.com/andrew-chung-au/vuln-triage/issues/76#issuecomment-6357191954). It contains findings, decisions D1-D7, the grooming decisions the PM made without asking, a revised issue body, spec notes and risks. Nothing is implemented yet.

## Update (later the same session)

- Done: PM correction posted (6357691953); the human answered D1-D7 (httpx + packaging approved, committed `fb33f75`; D2-D6 defaults accepted; Makefile `record-fixtures` approved, AGENTS.md line held; Engineer proposes the three fixture repositories, the human confirms before the live capture).
- Engineer implemented #76: commits `a6a342f` (parsers), `6ba1cae` (GitHub reader, fixtures, recorder, `.env.example`), `1d7c25f` (ingestion, worker), `c5ef99b` (`POST /assets`), `7f08719` (usage log); Engineer comment 6357882520. `make verify`: 62 frontend + 240 backend, PASS WITH WARNINGS (`tests/test_smoke.py` paths assertion updated for `POST /assets`; new project-authored fixtures).
- Protected Makefile commit `95eb7bf` (`record-fixtures`), approved by the human; approval record 6358822028.
- QA was launched at HEAD `95eb7bf`. When it reports: run `make assert-clean` and confirm HEAD is still `95eb7bf`.
- Decision point items to put to the human: the Engineer's open questions (finding_dependencies FK vs delete-and-reinsert for task 8; `lastScanAt` on a failed first scan; unexpected scan error left unfinished; global 422 handler; starlette testclient httpx2 warning; unverified GitHub behaviour: 409 empty repo, directory-as-absent); the PM's spec notes 1-5 (`U-GITHUB`/fixture layout in `testing.md`, E10 gaps, name the job table, replace the endpoint VERIFY, record the interim status rule); the AGENTS.md `make record-fixtures` Commands line (held); the three fixture repositories to confirm (`astral-sh/uv-docker-example`, `heroku/python-getting-started`, `heroku/node-js-getting-started`, from memory, unverified), then the human runs `make record-fixtures SOURCE=github` after putting them in `tests/fixtures/github/repositories.txt`.

## Next steps for #76 (original list; steps 1-3 are done)

1. Post a one-line `PM:` correction on #76: in the `-r` include criterion, the warning for more than 20 requirement files is kind `include refused` with message "include limit reached" (not `include limit reached` as a kind).
2. Ask the human D1-D7 from the PM comment (as decision questions with the PM's recommendations): D1 dependencies (`httpx`, `packaging`; VERIFY versions), D2 token (`GITHUB_READ_TOKEN`, `.env.example`), D3 interim scan status, D4 the `Scan` row as the job + one worker thread, D5 `local_packages` list, D6 `POST /assets` unguarded until 9a/9b, D7 protected Makefile `make record-fixtures` (leave uncommitted for a `HUMAN_APPROVED=1` commit), no AGENTS.md line, three fixture repositories confirmed by the human.
3. Launch the Software Engineer with the PM comment, the human's answers and the rule: protected files are returned as diffs for approval; `uv lock` through `make backend-lock`; the live GitHub capture is run by the human.
4. Then QA (note HEAD first), `make assert-clean`, decision point, session summary (replace this file), usage log, roadmap check-in, `make clean-scratch`, `make issue-close N=76`.

## Constraints to remember

- Only the human pushes. The agents work on `main` in the sandbox; the human fetches from the clean clone.
- Protected files change only with approval and `HUMAN_APPROVED=1`, then an approval record on the issue.
- Spec notes from the PM (add `U-GITHUB` to `testing.md`; E10 gaps; name the job table; interim status rule) go to the decision point.
- Roadmap check-in for #26 is already in `_docs/roadmap.md`; add the #76 line at its close-out. #112's line exists and says the issue is open.

## Permission review

none yet for #76 (the PM's grooming used only reads and `make issue-comment N=76`).
