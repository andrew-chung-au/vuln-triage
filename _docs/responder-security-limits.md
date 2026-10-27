# Responder security limits (#244)

Status: written 2026-10-27 for the pre-drill hardening of the real runner (#244, follow-up to #221). Nothing here has been run against a live Agent SDK session.

## The tool policy is a guardrail, not a sandbox

`responder/vt_responder/policy.py` stops a **confused** agent from doing the wrong thing by accident: writing to `.github/`, pushing to `main`, running an unlisted command. It does **not** contain an agent that has been prompt-injected or is otherwise hostile. The policy allows the agent to edit code and tests under `backend`, `tests`, `frontend` and `responder` and to run `make backend-test`, `make responder-test` and `make test`. Code the agent writes into a test, a `conftest.py` or `frontend/package.json` then runs as an ordinary child of the agent, with the agent's environment and network. The policy cannot see inside it. No document in this repository should say otherwise.

## What actually bounds a hostile agent

1. **Token scope (#222).** The responder's GitHub token is a fine-grained, repository-only token. #222 showed that a push to `main` with it is rejected.
2. **`protect-main`.** The repository ruleset rejects direct pushes to `main`, so a stolen token still cannot change `main` without a reviewed merge.
3. **The environment scrub (#244, B1).** `build_options` overrides every inherited variable that is not on a short allowlist with an empty string, so `RESPONDER_API_TOKEN`, `RESPONDER_WEBHOOK_SECRET`, `RESPONDER_GITHUB_TOKEN`, database, mail and cloud credentials are not visible to the agent or its children. The SDK builds the CLI environment as `{**os.environ, **options.env}` (`claude_agent_sdk/_internal/transport/subprocess_cli.py`, 0.2.174, read in the installed package), so it can override a variable but not remove it. The dependency install the runner does before the session gets only the allowlisted names.
4. **Run limits.** Turn limit, wall-clock limit, a spend cap (`RESPONDER_MAX_BUDGET_USD`, default 3.0, passed as `max_budget_usd`, which the installed SDK turns into `--max-budget-usd`), and the agent's processes are killed (by a per-run marker in their environment) before the checkout is removed and the branch is cleaned up. The kill is best effort: Linux `/proc` only, and a child that starts with a cleaned environment (`env -i`) is not found.
5. **Branch and pull-request checks.** Cleanup deletes only a `responder/<fp>` branch this run created. A reported pull request is accepted only if the REST API shows its head is `responder/<fp>` in the configured repository.

## What the scrub does not hide (known limit)

- `ANTHROPIC_API_KEY` must reach the CLI, and every Bash child inherits the CLI's environment. Code the agent runs can read it.
- `GH_TOKEN` and the `GIT_CONFIG_*` variables (the token, base64) are there because the policy lets the agent run `git push` and `gh pr create` itself. The SDK gives no way to set a variable for one Bash command only. So the git and `gh` credential is visible to code the agent runs. It is bounded only by items 1 and 2: the token can push `responder/*` branches and open pull requests in this one repository, and nothing else.
- Proxy and CA variables are on the allowlist because the CLI needs the network; a proxy URL can carry credentials.
- The scrub covers environment variables only, not files. Credentials stored under the responder's `HOME` (for example `~/.netrc`, `~/.aws`, `~/.config/gh`) are readable by code the agent runs. Run the drill on a host or account where those files hold nothing the agent should not reach, ideally a throwaway `HOME`.
- `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB` is a name inside the bundled CLI binary. Its error messages say it needs bubblewrap and a sandbox setup. It was not tried and nothing relies on it.

The narrowest change that would hide the git credential from the agent's children is to have the runner, not the agent, do `git push` and open the pull request (the agent would commit locally and report). That changes the agent contract and the policy; it is not built. The owner has decided against it for the drill (decision 2 below).

## Owner decision B13: accept the residual risk for the drill (2026-10-27)

The owner decided to **accept the residual risk** and not run the drill in a container with limited egress. The limits for the first live run are the environment scrub above, the repository-only fine-grained token (#222), and `protect-main`.

This acceptance is scoped to the **supervised, recorded drill on a throwaway demo defect** (task 39). It must be **revisited before any unattended or production use**: the revisit is to run the responder in a container whose network egress is limited to the Anthropic API and GitHub, which would also cover the Anthropic key and git token visibility described above. That container is not built and is out of scope for #244.

## Owner decision 2: the agent keeps `git push` and `gh pr create` for the drill (2026-10-27)

The owner decided to **keep it as is** for the drill: the agent runs `git push` and `gh pr create` itself through its Bash tool, and the runner does not take them over (#244 comment 6431746364). So the git credential and the Anthropic key stay visible to code the agent runs, as described under "What the scrub does not hide". The limits are the same as for B13: the repository-only fine-grained token (#222), `protect-main`, and the environment scrub for everything else.

This is scoped to the **supervised, recorded drill** (task 39). It must be **revisited before any unattended or production use**, together with the container option above: have the runner push and open the pull request while the agent only commits and reports, which would hide the git credential from the agent's children at the cost of changing the agent contract and the policy.

## Not covered

The reviewer's lower-priority items C1 to C9 (#244 "Out of scope") are not fixed here. The live SDK behaviour (whether a `PreToolUse` deny overrides the permission mode, the hook field names, whether cancellation ends the CLI, git over HTTPS with the extra header) is `VERIFY:` until the first live run.
