# Responder CLI runtime: what was verified, and what the first live run must settle (#260)

Status: written 2026-10-27 for #260 (amends F2). **Nothing here has been run against a login or a model from this repository.** The CLI facts below were read from `claude --help` and `claude auth` on the sandbox's installed `claude` 2.1.311, and from Anthropic's documentation pages named under each heading (fetched 2026-10-27). Anything not established is marked `VERIFY:` and stays marked until the owner's first live run (task 39 / #163).

## What the runtime is

`RESPONDER_MODE=real` with `RESPONDER_RUNTIME=cli` (the default) runs **one headless `claude -p` per alert** in the fresh checkout, on the owner's own Claude login. No API key. The agent only commits locally. After the run the **runner** checks the commits, pushes `responder/<fingerprint>` and opens the pull request. This is the shape of the coursework's `04-order-tracker` (webhook returns at once, headless `claude -p`, a fixed allow list and a deny list because a headless run cannot ask, the agent never pushes, its own process group and a time limit, the token kept out of the agent), with the push and the PR moved into the runner.

```
webhook -> 202 -> background run:
  clone -> make install (runner, no secrets) -> record base sha + .git/config digest
  -> claude -p (agent: reads, edits, make test, git add/commit)   [own process group, time limit]
  -> kill the process tree (group, then VT_RUN_MARKER)
  -> diff gate (publisher.py) -> git push (token here only) -> REST: open PR -> S4 read-back
  -> remove the checkout -> clean up a branch this run created if the run failed
```

Files: `responder/vt_responder/cli_session.py` (the session and the preflight), `cli_rules.py` (rules generated from `policy.py`), `publisher.py` (diff gate, push, PR), `envscrub.py` (`cli_env`), `prompt.py` (`CLI_SYSTEM_PROMPT`). Tests drive a fake `claude` (`responder/tests/fake_claude.py`).

## The flags used, and the source of each

Source key: **help** = `claude --help` / `claude auth --help` on 2.1.311 in this sandbox; **headless** = code.claude.com/docs/en/headless; **cli-ref** = code.claude.com/docs/en/cli-reference; **perm** = code.claude.com/docs/en/permissions; **auth** = code.claude.com/docs/en/authentication; **errors** = code.claude.com/docs/en/errors.

| Flag or command | What it does here | Source |
|---|---|---|
| `-p` / `--print` | non-interactive run; **reads the prompt from stdin** when no prompt argument is given; exits 0 on success and non-zero when the run fails | help, headless ("Non-interactive mode reads stdin", "exits with code 0 on success and a non-zero code when the run fails") |
| `--model <model>` | the model from `RESPONDER_MODEL` | help |
| `--max-turns <n>` | the turn limit (`RESPONDER_MAX_TURNS`); "Exits with an error when the limit is reached" | cli-ref. **Not listed in `claude --help` 2.1.311**, so the start-up preflight cannot check it: `VERIFY:` the flag is accepted |
| `--output-format json` | one JSON result object, text in `result`, plus session id and metadata | help, headless |
| `--permission-mode dontAsk` | "Claude Code denies every call that would otherwise prompt"; reads in the working directories and the read-only command set still run; anything matching `--allowedTools` runs | help (choice exists), headless |
| `--tools <list>` | limits the built-in tools to `Bash, Edit, Glob, Grep, MultiEdit, Read, Write` (from `policy.KNOWN_TOOLS`); no web tool, no sub-agent, no MCP | help |
| `--allowedTools <list>` / `--disallowedTools <list>` | the generated allow and deny rules; "comma or space-separated"; variadic, so each is passed as ONE comma-joined value and the task goes on stdin | help, headless |
| `--append-system-prompt <text>` | `CLI_SYSTEM_PROMPT` (keeps Claude Code's default prompt) | help |
| `--no-session-persistence` | no transcript saved under `HOME` ("only works with --print") | help |
| `--safe-mode` | starts with CLAUDE.md, hooks, plugins, MCP servers, skills, custom commands disabled; "Auth, model selection, built-in tools and plugins, and permissions work normally" | help. `VERIFY:` that `--allowedTools`/`--disallowedTools`/`--permission-mode` from the command line still apply under it |
| `claude auth status` | the login preflight: JSON `{loggedIn, authMethod, ...}`; "Exits with code 0 if logged in, 1 if not"; `authMethod` is one of `none`, `claude.ai`, `oauth_token`, `api_key`, `api_key_helper`, `third_party`; no model call | cli-ref; run once in this sandbox (printed `loggedIn: true`, `authMethod: oauth_token`; the not-logged-in output was not captured) |

Flags deliberately **not** used: `--bare` ("never reads OAuth credentials or the system keychain", so it cannot use a login; headless, help), `--dangerously-skip-permissions` and any `bypassPermissions`/`acceptEdits` mode, `--max-budget-usd` (a dollar cap means nothing on a plan; the turn and time limits bound the run instead), `--permission-prompts none` (needs 2.1.259 or later; in a `-p` run with no host those requests are denied anyway, the flag only tells Claude not to retry).

Preflight (`cli_session.preflight`, run once by `create_app` before the first alert): the binary is on `PATH`; `claude --help` lists every flag in `REQUIRED_HELP_FLAGS`; `claude auth status` exits 0; `authMethod` is `claude.ai` or `oauth_token`. Anything else (including `api_key`, `api_key_helper`, `third_party`) refuses to start with a message naming the cause, because those methods may bill something other than the plan. The preflight runs with the **same scrubbed environment as a run** (`cli_env`), so an `ANTHROPIC_API_KEY` set on the responder cannot make it look logged in.

## Credentials and the environment (auth page)

Precedence when several credentials exist (auth): cloud-provider variables, then `ANTHROPIC_AUTH_TOKEN`, then `ANTHROPIC_API_KEY` ("In non-interactive mode (`-p`), the key is always used when present"), then `apiKeyHelper`, then `CLAUDE_CODE_OAUTH_TOKEN`, then profiles, then the saved subscription login. So an API key or auth token in the environment **overrides the login and bills the API**, which is why `cli_env` removes them.

The saved login on Linux is `~/.claude/.credentials.json` under `HOME`, or under `CLAUDE_CONFIG_DIR` when that is set (auth). The CLI's environment is therefore built from scratch (`envscrub.cli_env`): the existing allowlist (`PATH`, `HOME`, `LANG`, proxy and CA names, ...) plus `CLAUDE_CONFIG_DIR` and `CLAUDE_CODE_OAUTH_TOKEN` (the login variables), the run marker and a git identity. `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_BASE_URL`, profile and federation variables, the Bedrock/Vertex/Foundry switches, `GH_TOKEN`, `GITHUB_TOKEN` are removed even if someone adds them to an allowlist (`CLI_FORBIDDEN`). No responder secret and no `GIT_CONFIG_*` credential is in it. `VERIFY:` the macOS login is in the Keychain (auth), which `HOME` alone does not reach from every context; the target host is Linux.

## Tool rules (perm page) and what they cannot do

Generated by `cli_rules.build_rules()` from `policy.py`'s constants (writable roots, protected components and suffixes, lockfiles, make targets, git subcommands). Semantics relied on, from **perm**:

* Evaluation order is deny, then ask, then allow, and "the first match in that order determines the outcome": **a deny always wins over a more specific allow**.
* `Bash(git diff *)` is a prefix rule (the space before `*` matters; a trailing ` *` also matches the bare command). Compound commands are split on `&&`, `||`, `;`, `|`, `|&`, `&` and newlines and each part must match an allow rule; a deny rule applies if **any** part matches, including inside `$(...)`.
* `Edit(backend/**)` as an allow rule is anchored at the working directory; `Edit(**/.github/**)` matches at any depth. "Claude Code checks file permissions against `Edit(path)` and `Read(path)` rules only": a `Write(...)`, `Glob(...)` or `MultiEdit(...)` path rule is accepted but never matches, so the generated rules use only `Edit(...)` and `Read(...)`.
* `Read(!**/.env.example)` after `Read(**/.env*)` carves the example file back out ("a `!` rule listed first carves nothing out").
* Reads inside the working directory need no rule under `dontAsk`; a bare `Read` allow would also reach files outside the checkout (the login under `HOME`), so it is not granted.

Generated lists (see the output of `build_rules()`; the test file `responder/tests/test_cli_rules.py` has one test per refused case against them):

* **Allowed**: `Edit(backend/**)`, `Edit(tests/**)`, `Edit(frontend/**)`, `Edit(responder/**)`; `Bash(make backend-test)`, `Bash(make responder-test)`, `Bash(make test)`; `Bash(git status *)`, `Bash(git diff *)`, `Bash(git log *)`, `Bash(git add *)`, `Bash(git commit *)`.
* **Denied**: `WebFetch`, `WebSearch`; `Bash(git push *)`, `gh`, `curl`, `wget`, `ssh`, `scp`, `sudo`, `pip`, `uv`, `uvx`, `npm`, `npx`, `node`, `pytest`, `python`, `python3`, `git config|remote|checkout|switch|branch|reset|rebase|merge|tag|fetch|pull|clone`, `make *install*`, anything containing `merge`; `Edit` on every protected component (`.github`, `terraform`, `infra`, `deploy`, `ci`, `.git`, `.claude`, ...), on `*.tf`/`*.tfvars`/..., `.env*`, `Dockerfile*`, `compose*.y*ml`, the lockfiles, and `responder/vt_responder/**`; `Read` on `.env*` except `.env.example`.

What a CLI rule **cannot express**, so the runner's diff gate is the control (see the next section):

1. The arguments of `git add` and `git commit`: `Bash(git add *)` also allows `git add .github/x.yml` (perm: argument-constraining Bash rules are fragile). `ToolPolicy` refuses that for the SDK runtime; the CLI cannot.
2. A program in another spelling: `Bash(curl *)` does not match `/usr/bin/curl`, `sh -c 'curl ...'`, `env curl`; `Bash(git push *)` does not match `git -C . push` or `git -c ... push` (perm, table of "what a rule doesn't match"). Those are not allowed either, so `dontAsk` denies them, but the deny list is not a boundary.
3. Anything the agent's own code does: a test or `conftest.py` that `make test` runs can open sockets, read files outside the checkout, or run `git push` with no credential to push with. No rule sees inside it.
4. Case-insensitive paths: the rules are case-sensitive globs; the gate is case-insensitive.
5. The read-only command set: `dontAsk` still runs it without a rule (headless). `VERIFY:` whether it can read outside the checkout (for example `cat ~/.claude/.credentials.json`); assume it can (this is the accepted login-under-`HOME` limit in `_docs/responder-security-limits.md`).

`cli_rules.evaluate` is **this repository's model** of those semantics, used only by the tests. `VERIFY:` that the real CLI agrees with it for every refused case in `test_cli_rules.py`; the first live run should try a few (a `git push`, an `Edit` of `.github/x`, a `curl`) and read the denials in the output.

## The runner-side diff gate (`publisher.py`), independent of the CLI

After the run, and after the process tree is killed, before any push. A refusal is a failed run with a short reason; nothing is pushed.

| Reason | Refused when |
|---|---|
| `git_config_modified` | `.git/config` differs from its digest right after the clone (it could point the push, with the token, elsewhere) |
| `no_commits` | the head is still the cloned head although the agent said FIXED |
| `base_not_cloned_head` | the new head does not descend from the cloned head |
| `merge_commit`, `too_many_commits` | any merge commit; more than `RESPONDER_MAX_COMMITS` (default 3) |
| `diff_path_<code>` | a changed file is outside the writable roots, or on `.github/`, infrastructure/Terraform/CI/devcontainer paths, an `.env*` file, a lockfile, or `responder/vt_responder/` (codes from `ToolPolicy.check_publish_path`: `path_not_allowed`, `github_dir`, `infrastructure_path`, `env_file`, `lockfile`, `guard_module`, `path_outside_checkout`); deleted files too |
| `diff_symlink`, `diff_submodule`, `diff_type_change`, `diff_mode_unexpected`, `diff_mode_changed`, `diff_status_unexpected`, `diff_path_odd_name` | a symlink or submodule, a file changing type, a new executable, a mode change, a rename/copy status, a control character in a path |
| `diff_empty`, `diff_too_many_files` | a commit that changes nothing; more than 40 files |
| `diff_check_failed` | git failed while checking (never a push) |
| `push_failed`, `pull_request_create_failed` | the push or the REST call failed; a branch this run created is removed (S1) |

The runner's git calls switch hooks and fsmonitor off (`-c core.hooksPath=/dev/null -c core.fsmonitor=false`), use `--no-ext-diff --no-textconv`, push `<head sha>:refs/heads/responder/<fp>` to an explicit `https://github.com/<repo>.git` URL (not a remote name from `.git/config`), never force, and pass the token (`git_auth_env`) to that one call. The PR title and body are composed by the runner from the validated fingerprint and finding id and the checked file list; the agent's one-line summary is redacted (`envscrub.redact`), cut to 300 characters, stripped of backticks and put in a code block, and nothing from the API or an advisory is read into it.

## Failure handling (the `reason` in `run_failed`)

`cli_exit_nonzero` (a non-zero exit is never a success, whatever the JSON says), `plan_usage_limit`, `max_turns`, `output_unparseable`, `result_line_missing`, `agent_cli_error` (`is_error` or a `subtype` other than `success`), `agent_escalated` (`RESULT: ESCALATE`), `agent_timeout` (the wall-clock limit: the CLI's process group gets SIGKILL, then the runner's marker kill), plus the diff-gate reasons above, `checkout_failed`, `install_failed`. Each is followed by the S1 branch cleanup rule and the checkout removal. `RESULT: FALSE_POSITIVE` pushes nothing and logs the explanation (US-15). There is no dollar budget on a plan; the turn limit and the time limit bound a run.

How a plan usage limit surfaces is **not established**. The errors page lists the messages ("You've hit your session limit", "...weekly limit", "...Opus limit", "...Sonnet limit", "Request rejected (429)", and that temporary 429s are retried automatically with backoff, up to 10 attempts by default) but, in the part read, neither the exit code nor the JSON shape of a headless run that hits one. The code treats a non-zero exit **or** `is_error` as a failed run and labels it `plan_usage_limit` when the output matches `hit your .. limit`, `usage limit`, `rate limit` or `credit balance`. `VERIFY:` the real wording, exit code and JSON on the owner's Pro plan; a retried 429 can also make a run slow, which the time limit then ends.

## `VERIFY:` list for the first live run

1. `--max-turns` is accepted by 2.1.311 (documented in cli-ref, absent from `--help`).
2. The JSON result has `is_error`, `subtype` (`success`, `error_max_turns`, ...), `result` (the final text) and `modelUsage` keyed by the served model. The headless page confirms `result`, session id and `total_cost_usd`; the rest is from the SDK's result message and is unconfirmed for the CLI.
3. `--permission-mode dontAsk` plus `--allowedTools` runs the allowed `make`/`git`/`Edit` calls headless without a prompt, and denies the rest.
4. `Edit(dir/**)` allow rules also cover the `Write` and `MultiEdit` tools (perm says path rules are checked against `Edit` and `Read` only; whether `Write` falls under `Edit` is not stated in the part read). If not, the agent cannot create new files and the allow list needs `Write` entries.
5. `--safe-mode` keeps the command-line permission flags in force, and really disables the checkout's `.claude/` hooks and the owner's user hooks.
6. The model of the rule semantics in `cli_rules.evaluate` matches the CLI for every refused case; whether the read-only command set can read outside the checkout.
7. A plan usage limit's wording, exit code and JSON (above).
8. A killed run: SIGKILL to the group leaves no CLI child; the `VT_RUN_MARKER` environment reaches the Bash children the CLI starts.
9. `git push` of a sha refspec to an explicit URL with the `http.extraheader` credential works against GitHub, and the PR REST call answers 201 with `html_url` (both `VERIFY:` in the code).
10. That the host's Linux Docker bridge is reachable as `172.17.0.1` from the Grafana container (runbook step 1).
11. How many turns and how much plan allowance a real run uses on the Pro plan (set `RESPONDER_MAX_TURNS` accordingly; the default is 30).
