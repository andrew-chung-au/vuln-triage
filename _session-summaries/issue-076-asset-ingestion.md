# Issue #76: Asset registration and repository ingestion (IN PROGRESS, handover)

**Date:** 2026-10-23
**Spec version:** 9b04f90

This is a handover note written mid-issue because the weekly usage limit was near. Update it as the issue moves; replace it with the final summary at close-out (process step 8).

## State when written

- #26 closed (QA PASS at `8ec6313`; summary `issue-026-data-model-sqlite.md`).
- #112 (push-check image) implemented and QA PASS on the static criteria; OPEN until the human finishes the guide `_docs/push-check-image-guide.md`: the human built the image, the plan-mode dry run showed `make -C . install verify`, and the real push (step 7) was about to run or has run. Still to report: step 8 (broken-install check) and the step 9 report. Then the orchestrator closes #112 (summary `issue-112-push-check-image.md` is already committed).
- #76 groomed by the PM: comment 6357191954 (https://github.com/andrew-chung-au/vuln-triage/issues/76#issuecomment-6357191954). It contains findings, decisions D1-D7, the grooming decisions the PM made without asking, a revised issue body, spec notes and risks. Nothing is implemented yet.

## Next steps for #76

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
