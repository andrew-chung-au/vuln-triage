# Planning: portfolio tidy (2026-11-09)

**Date:** 2026-11-09
**Spec version:** `docs/specs.md` moved from `_docs/specs.md`. User stories and acceptance lines are unchanged (see below for what did change).

Kiro Web session on branch `docs/portfolio-tidy`. Documentation, configuration and comment-only changes; no application logic changed.

## What changed and why

The project's first phase (the build, planned and recorded for a course) is over and the deployment is taken down, so the repository was reorganised to present the project to employers while keeping the working agent process.

- Tagged the pre-tidy state `v1.0.0` (pushed) as the archive of the planning, review and AI-usage record.
- Moved human-facing documentation to `docs/` and kept maintainer and agent-process material in `_docs/`.
- Consolidated overlapping documents: `docs/development.md`, `docs/deployment.md`, `docs/responder.md`, `docs/roadmap.md`, `docs/ai-assisted-development.md`, `docs/security-review.md`, and `_docs/human-review-workflow.md`.
- Rewrote `README.md` for an employer reading it: dropped the grading table, reviewer logins and dead live URLs.
- Removed course-only and superseded material (see the PR description for the list).
- Gated `deploy.yml` on the repository variable `DEPLOY_ENABLED`, and made `alert.yml` and `responder.yml` manual.
- Removed the AI usage log rule, the key-prompt rule and the rubric-auditor role from the agent configuration.
- Updated the doc paths in code comments, tests, settings and the Makefile.

## Files created or modified

See the pull request for the full list. Protected files changed, each by the owner's instruction in this session: `AGENTS.md`, `agent-kit.conf`, `Makefile`, `opencode.json`, `.claude/settings.json`, `.claude/agents/*`, `.opencode/agents/*`, `_docs/agent-kit/*` (path updates and two wording fixes), `docs/specs.md` (the header absorbed the useful parts of `project-brief.md`; "Open questions" became "Resolved questions" pointing at the architecture; references to planning stages were replaced with links; the user stories and acceptance lines are unchanged), and `.github/workflows/*`.

## Decisions made by the human

- Tag name `v1.0.0` for the archive (instead of an `archive/...` name).
- Keep `_session-summaries/`, the permission-sweep tooling and `_docs/agent-kit/` for now: they feed the permission review and will be reworked in the planned agent-kit upgrade.
- Keep the maintainer review workflow (renamed `_docs/human-review-workflow.md`, since it is for the repository maintainer, not for evaluators) and fold in the useful parts of the push-check image guide.
- Drop the AI usage log (and its rule in `AGENTS.md`); keep the short "how this was built" page.
- Drop the YouTube channel link; keep the demo video link.
- Layout: `docs/` for human-facing documentation; `_docs/` for maintainer and agent material, until the kit upgrade.

## Mismatches with the spec or design docs

- The architecture document still cites build-order labels ("task 38", decision IDs such as A26) and issue numbers. They resolve through GitHub issues and the `v1.0.0` tag.
- `P-FLAG-GONE` (`python3 ci/check_flag_gone.py`) fails with 103 findings before and after this change; the demo-defect switch is still in the tree, as documented. Not caused by this work.

## Commands to validate

- **Verify:** `make verify`. **Not run in the sandbox**: it cannot install dependencies (PyPI and the Python download host were unreachable). CI on PR #275 ran it: after one fix (below) all seven required checks pass.
- **A miss CI caught:** two tests built the contract path from segments (`"_docs" / "openapi.yaml"`), which a text search for `_docs/openapi.yaml` did not find. `sqlite-integration`, `postgres-integration` and `openapi-validation` failed until they were pointed at `docs/openapi.yaml`.
- Run instead: `tests/test_flag_gone.py` and `tests/test_marker_hygiene.py` (20 passed, with `--noconftest`); `bash -n` on every kit script and hook; JSON parse of the four settings files; Ruby YAML parse of the four workflows and `docs/openapi.yaml`; `py_compile` of every changed Python file; `git diff --check`; a script check that every relative link, image and anchor in the touched Markdown resolves.

## Proposed AGENTS.md changes

None beyond those already made.

## Temporary changes

`.scratch/` helper scripts only (emptied at the end); a temporary git worktree of `v1.0.0` (removed). No installs.

## Permission review

- Read-only (propose allowing): none recorded.
- Routine issue writes: none.
- Protected record writes (keep asking): protected-file commits for this tidy, made with `HUMAN_APPROVED=1` on the owner's go-ahead; no issue-based approval record was posted (flagged in `_docs/human-tasklist.md`).
- System and external changes (keep asking): pushing the `v1.0.0` tag.
- Risky (propose denying): none.

## Interruptions

None.

## Unrelated problems noticed but not fixed

- The Compose `responder` workflow is knowingly failing (documented in `docs/roadmap.md`).
- The Terraform security review's F1–F4 were not re-verified as fixed in the code; the deployment later ran, which suggests they were.

## Follow-ups for the next session

- Work through `_docs/human-tasklist.md` and delete it.
- Add a LICENSE.
- Agent-kit upgrade: simplify, and move the kit out of `_docs/`.
