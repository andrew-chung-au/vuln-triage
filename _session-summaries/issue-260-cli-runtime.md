# Issue #260: headless `claude -p` runtime on the owner's login (amends F2)

**Date:** 2026-10-27
**Spec version:** not changed (no protected file touched)

## What changed and why

Engineer subagent on `claude/260-cli-runtime`, branched from `origin/main` (#221, #241 and #244 merged). The owner confirmed decisions 1 to 4 with "go" on the issue. A fake `claude` script drives every test: no login, no network, no model call. Nothing was run against a real login.

- **Verification first** (`_docs/responder-cli-runtime.md`): flags read from `claude --help` and `claude auth` on the installed 2.1.311 (no session started) and from the headless, CLI reference, permissions, authentication and errors pages on code.claude.com. Two things were run in the sandbox: `claude --version` and `claude auth status` (it printed `loggedIn: true`, `authMethod: oauth_token`, so the sandbox's own login was read, no model call). `--max-turns` is documented but missing from `--help`; `--bare` cannot use a login; `--allowedTools`/`--disallowedTools`/`--tools` are variadic, so they are passed as one comma-joined value and the task goes on stdin.
- **`cli_session.py`**: `CliSession` (one `claude -p` per alert, own process group via `start_new_session`, `SIGKILL` of the group at the time limit, `VT_RUN_MARKER` in its environment, output files in a temp directory outside the checkout, deleted afterwards), `preflight()` (binary, required flags in `--help`, `claude auth status` exit 0, `authMethod` `claude.ai` or `oauth_token`), `parse_output()` (the last `RESULT: FIXED|FALSE_POSITIVE|ESCALATE` line; non-zero exit, `is_error`, timeout, usage limit, unparseable output are failed runs with a short reason).
- **`config.py`/`app.py`**: `RESPONDER_RUNTIME` (`cli` default, `sdk`, anything else refused); the `cli` runtime does not read `ANTHROPIC_API_KEY`; `RESPONDER_MAX_COMMITS` (default 3). `create_app` runs the preflight unless a session is injected. Real mode is still refused in CI and test.
- **`envscrub.cli_env`**: the CLI's environment is built from scratch (allowlist plus `CLAUDE_CONFIG_DIR`, `CLAUDE_CODE_OAUTH_TOKEN`, marker, git identity); `ANTHROPIC_*`, `GH_TOKEN`, `GITHUB_TOKEN` and the provider switches are removed again at the end.
- **`cli_rules.py`**: allow and deny lists generated from `policy.py` constants, plus `evaluate` (a model of the documented rule semantics, used by tests only). New constants in `policy.py` (`PROTECTED_LOCKFILES`, `PROTECTED_PATH_PREFIXES`, `CLI_GIT_*`) and `ToolPolicy.check_publish_path`; `check_write_path` and the SDK path are unchanged.
- **`publisher.py`**: the diff gate (cloned base, ancestry, merges, commit count, file count, per-file path and mode rules, `.git/config` digest), then the runner's push of `<sha>:refs/heads/responder/<fp>` to an explicit URL with the token only in that call, then the PR through `GitHubRestBranches.create_pull_request`; title and body composed by the runner, agent summary redacted, 300 characters, fenced. `RealRunner` takes `publisher`, `system_prompt`, `task_builder`; a session result `fixed` is published inside the checkout's lifetime after the agent is killed; `AgentResult.reason` carries the failure code.
- **`prompt.py`**: `CLI_SYSTEM_PROMPT` and `build_cli_task` (commit locally with explicit paths, never push, end with the `RESULT:` line, keep the false-positive path). The SDK prompt is untouched.
- **Docs**: `_docs/responder-cli-runtime.md` (new), `_docs/responder-security-limits.md` (the `cli` section, the login-under-`HOME` limit, no dollar cap, decision 2 marked superseded for `cli`), `_docs/drill-runbook.md` (host-run responder on the login, Compose `responder` is stub-only, `172.17.0.1` with `VERIFY:`, Pro-plan caveat), `.env.example` (`RESPONDER_RUNTIME`, `RESPONDER_MAX_COMMITS`, empty).

## Existing tests changed (not weakened)

`responder/tests/test_mode.py`: the `REAL` env now names `RESPONDER_RUNTIME=sdk`, because the default real-mode runtime is now `cli`, which does not require `ANTHROPIC_API_KEY`; the SDK requirement it tests is unchanged. No assertion was removed (`make verify`: 145 assertion lines added, 0 removed). The SDK runtime, stub mode and every other existing test are untouched.

## Acceptance criteria

All met in code and tests; the F2 recording criterion's second half is the PR that closes the issue (`human-tasklist.md` F2/B14 are not edited here). Not met by construction: nothing was run live.

## Decisions made by the human

Owner "go" on decisions 1 to 4 (issue comment 6432349449).

## Mismatches with the spec or design docs

none.

## Commands to validate

- **Verify:** `make verify BASE=origin/main` PASS (frontend 89, backend 561, responder 561; 145 assertion lines added, 0 removed).
- **Test (responder):** `make responder-test`.

## Proposed AGENTS.md changes

none. Proposed Makefile target (protected, not made): `responder-start` / `responder-stop` for the host-run real responder (the runbook currently gives the raw `uvicorn` command), recording the PID as the other `*-start` targets do.

## Temporary changes

`make responder-install` and `make install` ran once (git-ignored venvs and `node_modules` in this worktree). No process left running, no system configuration changed. The fake-`claude` tests start and kill `sleep` children inside `pytest` temp directories only.

## Permission review

- Read-only (propose allowing): `make issue-dump`, `git fetch`, `which claude`, `claude --version`, `claude --help`, `claude auth --help`, `claude auth status` (reads the local login state, no model call), `ls`.
- Writes to the record (keep asking): `make responder-install` and `make install` (network, git-ignored folders); `make issue-comment`.
- Risky (propose denying): none.

## Interruptions

none.

## Unrelated problems noticed but not fixed

- `claude --help` omits `--max-turns` although the CLI reference documents it, so the preflight cannot check it.
- The read-only command set in `dontAsk` may read outside the checkout (`VERIFY:`); the accepted login-under-`HOME` limit covers it.
- The runbook's `docker network inspect` check for the bridge address and the backend URL as seen from the host (`RESPONDER_API_URL`) are `VERIFY:` items.
- SDK runtime removal and the `claude-agent-sdk` dependency stay for the later cleanup; #256 needs re-scoping now that the runner opens the PR.

## Follow-ups for the next session

- QA on #260; then the owner's first live run (`VERIFY:` list in `_docs/responder-cli-runtime.md`, 11 items) on a fresh Pro allowance, then the recorded drill (task 39 / #163).
- `human-tasklist.md` F2/B14 update in the PR that closes the issue.
