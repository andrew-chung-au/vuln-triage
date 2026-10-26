# Issue #221: real Agent SDK runner, remaining criteria (task 28d of #160)

**Date:** 2026-10-26
**Spec version:** not changed (no protected file touched)

## What changed and why

Engineer subagent on `claude/f4-real-runner-fix` (PR 239), building on the scaffold already there (`RESPONDER_MODEL`, `RealRunner` behind the `AgentSession` seam, `prompt.py`). Everything is tested with a fake SDK, a fake git and a fake GitHub client; no key, no network.

- **Dependency.** `claude-agent-sdk==0.2.174` added to `responder/pyproject.toml` only, `responder/uv.lock` regenerated with `uv lock --project responder`. Name and version carry a `VERIFY:` comment (read from pypi.org/pypi/claude-agent-sdk/json; the release date was not shown). A test asserts `backend/uv.lock`, `backend/pyproject.toml` and the backend Dockerfiles do not mention it.
- **Config.** Real mode now also requires `ANTHROPIC_API_KEY`, `RESPONDER_GITHUB_TOKEN` and `RESPONDER_GITHUB_REPO` (`owner/name`), read from the environment only, `repr=False`, never in an error message. Bounds: `RESPONDER_MAX_TURNS` (default 30) and `RESPONDER_RUN_TIMEOUT_SECONDS` (default 600). CI/test signal (any one): `CI` or `GITHUB_ACTIONS` truthy, `PYTEST_CURRENT_TEST` set, `DEPLOYMENT_ENVIRONMENT=test`. The same check runs again in `build_default_session`.
- **Policy** (`policy.py`, pure): reads and writes must resolve (realpath, so `..` and symlinks) inside the checkout; writes only under `backend`, `tests`, `frontend`, `responder`, never `.github`, `.git`, Terraform/infra/deploy/ci paths, Dockerfiles, compose files or any `.env*`; `.env*` unreadable except `.env.example`; Bash only `git status/diff/log`, `git add -- <paths>`, `git commit -m`, `git checkout -b`/`switch -c` of the responder branch, `git push [-u] origin responder/<fp>`, `gh pr create` for that head, `make backend-test|responder-test|test`; no shell metacharacters; anything containing "merge" is denied; everything else is denied. A fingerprint such as `-x` is only ever used as `responder/-x`.
- **Checkout** (`checkout.py`): fresh temp directory per run, clone through a seam, refuses a dirty tree, removed afterwards on success and error. The real seam passes the token through git environment config, not the URL.
- **Bounds and cleanup** (`real_runner.py`): the session runs in a worker thread with a wall-clock limit; error, timeout, agent-reported error, a PR result without a URL, and "no change" all call `delete_branch_if_exists` for `responder/<fp>` (REST client `github_client.py`; `FakeBranchClient` in tests) and log `branch_deleted`.
- **Live session** (`sdk_session.py`): `SdkSession` uses `ClaudeSDKClient`, a `PreToolUse` hook (runs for every call, including the read tools the CLI would not ask about) plus `can_use_tool`, both calling the one policy; denials are logged as `tool_denied` with only `reason` and a known tool name. `tools` is limited, `permission_mode="default"`, nothing pre-approved, `setting_sources=[]`. The agent ends with `RESULT: PULL_REQUEST <url>` or `RESULT: NO_CHANGE <text>` (added to `prompt.py`); the model comes from `AssistantMessage.model`. The SDK is imported lazily inside `run`.
- **Seam change.** `make_session` is now `(model, ctx)`; existing test lambdas were updated, no assertion changed.

## Files created or modified

`responder/pyproject.toml`, `responder/uv.lock`, `responder/vt_responder/{policy,checkout,github_client,sdk_session}.py` (new), `config.py`, `app.py`, `real_runner.py`, `prompt.py`, `actlog.py`, `fakes.py`; tests `test_policy.py`, `test_real_runner_isolation.py`, `test_sdk_session.py`, `test_sdk_isolation.py` (new), `test_mode.py`, `test_real_runner.py`; `_docs/ai-usage-log.md`, `_docs/roadmap.md`, this summary. `.env.example` not changed.

## Decisions made by the human

none in this session (F2 and F4 were decided earlier).

## Mismatches with the spec or design docs

none new.

## Commands to validate

- **Verify:** `make verify` (PASS WITH WARNINGS: base equals HEAD; frontend 89, backend 532, responder 210).
- **Test (responder):** `make responder-test`.

## Proposed AGENTS.md changes

- Commands: `make responder-lock` (runs `uv lock` in `responder/`) would mirror `backend-lock`; this session used `uv lock --project responder`. Needs the protected `Makefile`, so proposed only.
- Optional: list `ANTHROPIC_API_KEY`, `RESPONDER_GITHUB_TOKEN`, `RESPONDER_GITHUB_REPO`, `RESPONDER_MAX_TURNS`, `RESPONDER_RUN_TIMEOUT_SECONDS` as names (no values) in `.env.example`; not done because the task said to leave it unchanged.

## Temporary changes

`make responder-install` ran (installs the SDK and 17 transitive packages into the git-ignored `responder/.venv`). No processes started; no system configuration changed.

## Permission review

- Read-only (propose allowing): `uv lock --project responder` has no make target and touches the network (PyPI) and writes `responder/uv.lock`; recorded as an approval-class command. A web fetch of pypi.org (read-only).
- Writes to the record (keep asking): `make responder-install` (network, installs into `responder/.venv`); `make issue-comment` for the Engineer comment.
- Risky (propose denying): none.

## Interruptions

none.

## Unrelated problems noticed but not fixed

- The agent-facing text of a `no_change` explanation is model-written and logged (truncated to 500 characters, non-printable characters removed). It is not advisory text read from the API, but the model could repeat some; the drill log should be read once before it is shared.
- `compose.responder.yaml` does not pass the new real-mode variables; real mode is not run in Compose (it is the owner's host drill).
- The in-memory guard state is lost on restart (X12), so a restart mid-run could allow a second run.

## Follow-ups for the next session

- First live run needs #222 (token) and the owner's key on a non-clean-clone host; check the `VERIFY:` items in `sdk_session.py` (PreToolUse deny overriding the permission mode, `RESULT:` line, git extraheader auth, commit identity).
- Real runs outlast Grafana's webhook timeout: a background run (comment 6410222768 on #221) is not built here; `app.py` still runs the agent in the request.
