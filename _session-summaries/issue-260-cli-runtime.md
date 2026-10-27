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
- QA-fix session: `make responder-install` in the new worktree (network, git-ignored `responder/.venv`; writes to the record, keep asking; explicitly allowed by the brief); `make issue-comment N=260 FILE=...` (keep asking). `make install` was NOT run (not authorized); `make verify` fails on the missing `frontend/node_modules` only.

## QA fixes (2026-10-27, branch `claude/260-qa-fixes` from `claude/260-cli-runtime` at `1516c7c`)

QA's FAIL (comment 6433016307) had four findings. Each was reproduced RED first with a test (new `responder/tests/test_publisher_real_git.py` drives the real `GitPublisher` and `SubprocessPublishGit` on local temp repositories and a local bare remote; the tool rules with `cli_rules.evaluate`), then fixed, one commit per finding:

- **1d** global git config: every runner git call sets `GIT_CONFIG_GLOBAL=/dev/null` and `GIT_CONFIG_NOSYSTEM=1`. Red: a `url.insteadOf` in `~/.gitconfig` and in the XDG config sent the push to another repository.
- **1c** `git replace`: every runner git call passes `--no-replace-objects`. Red: the gate accepted a replaced evil commit.
- **1b** intermediate commits: the runner builds ONE commit (`commit-tree` of the checked head's tree on the cloned base, its own message) and pushes that; the agent's commits are never pushed. Red: three commits including `.github/workflows/evil.yml`, a leak file and an executable were pushed. New `PublishGit.squash`; the fake-git tests now expect the squashed sha.
- **1a** symlink swap: `check_publish_path` judges the committed path string lexically (no `realpath`, no filesystem). Red: a `.github` or `responder/vt_responder` directory swapped for a symlink after the commit passed.
- **2** tool rules: `git add` allowed only under a writable root and with no flag, `.`, `..`, absolute or protected name; `git commit` only as `-m`, with trailing flags denied; `--output`, `--no-index`, `--ext-diff`, `--textconv` (and abbreviations) denied for status, diff and log. Red: 31 new refused cases were allowed. Two existing tests were adapted to the narrower allow list (the "built from policy constants" assertion for add/commit; the "cannot express" test, which used to assert that `git add .github/...` was allowed by the rules and now asserts it is refused and keeps `git add backend/link` as the remaining gap).
- **3** PR body paths: a changed path must match `[A-Za-z0-9._/+=,~-]+` and be at most 200 characters, else the run fails before the push (`diff_path_odd_name`, `diff_path_too_long`).
- **4** docs: the two overclaiming sentences in `_docs/responder-security-limits.md` softened, what the gate does and does not guarantee stated, the `--output` gap and its closure recorded; `_docs/responder-cli-runtime.md` updated.
- **Minor, done**: preflight refuses `loggedIn:false` even with exit 0; a `RESULT:` line inside a code fence is ignored; output over 5 MB (checked while the CLI runs, polled every 0.25 s, and after) is a failed run `output_too_large` instead of an unparseable truncated read. Fake `claude` gained `logged_in` and `flood` options.

Existing assertions changed (listed by `make verify` as removed or rewritten): `test_cli_rules.py` `assert check(... "git add .github/workflows/x.yml").allowed` (replaced by its refused opposite, finding 2); `test_cli_runtime.py` and `test_publisher.py` `pushed == [(head sha, BRANCH)]` (now the squashed sha plus an assertion on what was squashed, finding 1b). No assertion was weakened. The `sdk` runtime, stub mode and the other tests are unchanged.

Verification here: `make responder-test` 618 passed. `make verify` could NOT pass in this worktree: `frontend/node_modules` is missing (`make install` needs network and was not authorized for this task), so the frontend test and type-check steps fail for that reason only; whitespace passes; the weakened-test warning is explained above. Backend tests were not run here (unchanged by this work).

## QA round 2 (2026-10-27, branch `claude/260-qa-fixes-2` from `claude/260-cli-runtime`, QA comment 6435357864)

One commit per item, each red first (a new failing test, watched failing, then the fix):

- **1d residual (a)**: a `.git/commondir` pointing at a copy of `.git` with a `url.insteadOf` redirected the push while the `.git/config` digest matched. Red: 10 new real-git tests failed (push reached the evil remote, no refusal). Fixed: every `SubprocessPublishGit` call sets `GIT_DIR` and `GIT_COMMON_DIR` to the checkout's `.git`; `config_digest` refuses (`git_dir_unexpected`) a `.git` that is a symlink/not a directory, holds `commondir`, `gitdir`, `config.worktree`, `info/grafts`, `objects/info/alternates`, `objects/info/http-alternates`, or has a non-plain `config`; `GitPublisher.publish` re-reads the digest after the squash, immediately before the push (`git_config_modified`). Tests: commondir absolute and relative refused; the explicit `GIT_DIR` alone defeats a planted `commondir` (push called directly); four other entries refused; `.git` symlink refused; a config edit injected between squash and push refused.
- **1d residual (b)**: `checkout.SubprocessGit` now sets `GIT_CONFIG_GLOBAL=/dev/null` and `GIT_CONFIG_NOSYSTEM=1`. Red: a `url.insteadOf` in a temp HOME's `.gitconfig` made the clone fetch the other repository (`EVIL`).
- **2 tool rules**: red: 100+ new refused cases were allowed by the model. Fixed in `cli_rules.py`: quote and backslash refused in any `git status|diff|log` and `git add` argument; every prefix (3+ characters) of `--output`, `--no-index`, `--ext-diff`, `--textconv`, `--orderfile` refused as a whole argument; `--or`, `-O` substrings; `git commit` allowed only as `-m '<msg>'` or `-m "<msg>"`, with `* -*` (any flag, abbreviation or `--`) and quote-then-space (a second argument) denied; `git add` also denies `compose*.yaml|yml`, tab, `*` (`\*` in a rule), and `--`. The model's pattern parser learned `\*` and `\\`. `ToolPolicy` now refuses `*?[]` in `git add` paths. `prompt.py` tells the agent the commit form. Not refused by the rules (documented): `?`/`[` globs, other-case protected names, symlinks (gate only).
- **3 docs**: `_docs/responder-security-limits.md` items 2 and 3 and the git-limits bullet, `_docs/responder-cli-runtime.md` (`git_config_modified` row, new `git_dir_unexpected` row, allowed/denied lists, "cannot express", git-call paragraph) rewritten to say what is guaranteed and what is not, with R1 (straggler between re-check and push), R2 (gate reads a repository the agent can write to), R4 (the real CLI may not match `evaluate`), and two new `VERIFY:` items (`\*`/`\\` escape syntax, quote handling in `Bash(git commit -m '*')`).
- **4 minor**: `_outside_fences` is now a fence parser (opening run of 3+ backticks or tildes, closed only by the same character, at least as long, nothing else on the line). Red: a 4-backtick fence containing a 3-backtick line, and a 3-backtick fence containing a ```` ```text ```` line, let a quoted `RESULT:` count.

Existing assertion changed: `test_cli_rules.py` `assert "Bash(git commit -m *)" in RULES.allowed` became the two quoted forms plus an assertion that the unquoted rule is absent (the rule shape changed with item 2). No test weakened or skipped.

Verification: `make verify BASE=origin/main` PASS (frontend 89, backend 561, responder 911; 182 assertion lines added, 0 removed). Commands that needed approval: `make install` (network install of git-ignored venvs and `node_modules` in this worktree).

Still open: R1, R2, R4 as documented; nothing run against a live `claude`.

## QA round 3 (2026-10-27, branch `claude/260-cli-runtime` at `973f054`, QA comment 6436104728)

One commit per item, red first:

- **F1 (medium)**: shell expansion rebuilt a denied flag after the rules looked (`git diff --${u}output=/x`, `--o{u,u}tput`, `git add backend/.en${u}v`, `backend/{.github,x}/y`, `$HOME`). Red: 25 new refused cases were allowed by `cli_rules.evaluate`. Fixed in `cli_rules.py`: `$`, `{` and `}` are denied in any `git status|diff|log|add|commit` argument (`GIT_EXPANSION`); `ToolPolicy` already refused them as shell metacharacters, and the new cases are asserted against both. `git commit` got the same refusal so the rules and the policy agree (a message containing `$` or braces is refused). `make` targets are exact-match rules and needed nothing. `?`, `[`, `]` are still not refused (documented).
- **F2 (low to medium)**: `changes()` now passes `--ignore-submodules=none`, so an untracked `.gitmodules` with `ignore = all` cannot hide a committed gitlink. Red: a real-git test published the run with the gitlink pushed. Other runner git calls checked: `rev-list`, `merge-base`, `rev-parse`, `commit-tree`, `push` do not read submodule settings; `checkout.is_clean` (`git status --porcelain`) runs right after the clone, before any agent code exists, so it needs no change.
- **3 docs**: `_docs/responder-security-limits.md` item 3 no longer says paths are judged "never through the working tree" (the one known working-tree input, `.gitmodules`, is named and closed; others are not examined, R2); item 2 lists the expansion refusal; `_docs/responder-cli-runtime.md` has the expansion paragraph with a `VERIFY:` (raw or expanded text matched by the real CLI) and the `diff_submodule` row mentions the flag.
- **4 minor**: `test_the_run_starts_in_the_checkout_in_its_own_process_group_and_leaves_no_file_behind` now points `tempfile.tempdir` at an empty directory under `tmp_path` and asserts that directory is empty afterwards, so another process's `vt-cli-*` in `/tmp` cannot fail it; it still fails if the run leaves its output directory behind.

No existing assertion was changed or removed. Verification: `make verify BASE=origin/main` PASS (frontend 89, backend 561, responder 940; 182 assertion lines added, 0 removed). Commands that needed approval: none.

Still open: R1, R2, R4 as documented; nothing run against a live `claude`.

## QA round 4 (2026-10-27, branch `claude/260-cli-runtime` at `7b5a3e0`, QA comment 6436304070)

- **N1 (low)**: `git commit -m "x"<TAB>-a<TAB>-m "y"` was allowed by `evaluate` (the commit denials are space-based; real git ran `-a`). Red: 16 of the new whitespace cases were allowed. Fixed in `cli_rules.py`: `GIT_CONTROL_WHITESPACE` (tab, VT, FF, CR) is denied in any argument of `git status|diff|log|add|commit`. Tests: tab-smuggled forms are refused by `evaluate` and `ToolPolicy`; tab elsewhere and VT/FF/CR are refused by `evaluate` only (`ToolPolicy` splits like the shell, so a tab between words is a legitimate commit there). Newline is already a separator; Unicode spaces (NBSP, em space) are not word separators in bash and are not refused (documented).
- **Prompt**: `prompt.py` now tells the agent a commit message may not contain `& ( ) ; < > $ { }`, a backtick or a tab; a test checks the sentence.
- **Docs**: `_docs/responder-security-limits.md` item 2 (commit bullet, new whitespace bullet, `~` and `*` in the not-guaranteed list, from QA's omissions) and `_docs/responder-cli-runtime.md` (whitespace sentence); the item 2 `git commit` sentence holds as modelled.

Verification: `make verify BASE=origin/main` PASS (see the final run in the issue comment). Commands that needed approval: none. Still open: R1, R2, R4; nothing run against a live `claude`.

## Interruptions

The session hit its usage limit once during finding 1d; the work resumed from the uncommitted state with no loss.

## Unrelated problems noticed but not fixed

- `claude --help` omits `--max-turns` although the CLI reference documents it, so the preflight cannot check it.
- The read-only command set in `dontAsk` may read outside the checkout (`VERIFY:`); the accepted login-under-`HOME` limit covers it.
- The runbook's `docker network inspect` check for the bridge address and the backend URL as seen from the host (`RESPONDER_API_URL`) are `VERIFY:` items.
- SDK runtime removal and the `claude-agent-sdk` dependency stay for the later cleanup; #256 needs re-scoping now that the runner opens the PR.

## Follow-ups for the next session

- QA on #260; then the owner's first live run (`VERIFY:` list in `_docs/responder-cli-runtime.md`, 11 items) on a fresh Pro allowance, then the recorded drill (task 39 / #163).
- `human-tasklist.md` F2/B14 update in the PR that closes the issue.
