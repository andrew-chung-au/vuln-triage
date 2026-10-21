# Running VulnTriage work in Claude Code cloud sessions

How to use Claude Code on the web (cloud sessions) for this project: what differs from the local sandbox, the settings to enter, and the steps to follow. Status: the repo changes are done (#44, `8eeaf53`); the GitHub and claude.ai setup (section 4) and the trial (section 5) are still to do. Cloud credit is limited, so the project must not depend on it. The default Docker setup is option A in the local sandbox (`_docs/docker-runbook.md`).

Sources: <https://code.claude.com/docs/en/claude-code-on-the-web>, <https://code.claude.com/docs/en/cloud-environments> and <https://code.claude.com/docs/en/web-quickstart>, read 2026-10-20 and 2026-10-21. Details the docs don't state, or that may change, are marked `VERIFY:`. Check them in the trial session (section 5).

## 1. Why cloud sessions, and when to use them

What a cloud session gives this project:

- **Docker, Docker Compose and PostgreSQL 16 are preinstalled** in the cloud VM. The local sandbox has no Docker. That is what blocks #31.
- Python with uv, Node 22 (on `PATH` by default), npm, git and `gh` are preinstalled. The VM has about 4 vCPUs, 16 GB of RAM and 30 GB of disk.
- Sessions can run subagents, so one session can run the whole PM → Engineer → QA lifecycle for an issue.
- Usage counts toward the plan's usage limits like any other Claude Code usage; there's no separate charge for the VM. Parallel sessions use limits proportionately. `VERIFY:` how any promotional cloud credits on the account are applied.

What the agents see:

- **The same as local:** `CLAUDE.md`, `AGENTS.md`, `.claude/settings.json` (allow, ask and deny rules, and hooks) and the `.claude/agents/` roles, because they come with the clone.
- **Not carried over:** user-level `~/.claude/` settings and memory. A preference saved only there (for example "the human owns the timeline: no deadlines or dates in agent-facing docs") must be told to the session or written into the repo.
- **Starting point:** a fresh clone of the GitHub remote at the chosen branch. Uncommitted work and `.scratch/` files in the sandbox are not there, so push local commits **before** starting a session.

**The most efficient way to use it:** one cloud session per issue, running the full lifecycle, with the human's decisions batched up front and at the decision point.

- Use cloud sessions for long, self-contained work, especially the build steps that need Docker or Postgres (#24-#26, #31).
- Keep small edits, roadmap check-ins and quick questions local: they cost the same usage with no benefit.
- Answer the issue's decision questions before launching, so the session doesn't sit idle waiting. An idle VM pauses after a few minutes; a paused VM can be reclaimed, which keeps the conversation but loses running subagents and background commands.
- Run parallel sessions only for issues that touch different files.
- Work on one issue in only one environment (cloud or local sandbox) at a time.

## 2. What differs from the local sandbox, and how the repo handles it

| Area | Local sandbox | Cloud session | How it's handled |
|---|---|---|---|
| Where work lands | Commits on local `main`; the human pushes from a clean clone | Commits on the session's branch; the session pushes that branch, and the human merges a PR | `AGENTS.md` Branching has both variants |
| GitHub write access | Read-only code token | The GitHub proxy allows pushes to **any** branch (it blocks only branch deletion and non-branch pushes), using the human's GitHub credential | The ruleset on `main` is the real control (section 4.2) |
| Pushes from the agent | Refused | Only `git push -u origin <current claude/* branch>` | `.claude/settings.json` denies pushes to `main`, force and delete; `guard_git.py` blocks every other push, except that cloud one |
| `gh issue ...` / `gh pr ...` | Work | **403**: the proxy rejects GraphQL; only `gh api` (REST) works | `make issue-dump`, `issue-comment` and `issue-close` use REST in both |
| Node | 24.22.0 (dev container) | 22 by default | CI already uses the runner's default Node; `VERIFY:` `npm ci` and the 35 tests pass on 22 |
| Docker / Postgres | Not available | Available | Unblocks #31 |
| Git hooks and dependencies | Installed by `setup.sh` | Not installed | The `SessionStart` hook `cloud_session_start.sh` runs `make install` (when needed) and `make hooks` |
| Commit author | `setup.sh` name and noreply email | Not documented | `VERIFY:` in the trial (section 5) |

## 3. Repo changes (done in #44, `8eeaf53`)

- **`Makefile`:** `issue-dump` (two flat JSON files in `.scratch/`), `issue-comment N= FILE=` and `issue-close N=`, all through `gh api`. `issue-dump` pipes `gh api --paginate --slurp` into `jq`, so `jq` must exist in the cloud image (`VERIFY:`).
- **`.claude/settings.json`:** allows `gh api repos/*`; asks before `make issue-close`; denies `git push * main*`, `--force`, `-f` and `--delete`; adds the `SessionStart` hook.
- **`guard_git.py`:** allows `git push -u origin <current branch>` only when `CLAUDE_CODE_REMOTE` is `true` and the current branch starts with `claude/` (`VERIFY:` the prefix cloud sessions use).
- **`cloud_session_start.sh`:** does nothing locally; in the cloud, prepares the session and prints `Environment: Claude Code cloud session (Docker available; push only this session's branch)`. Agents use the banner instead of reading environment variables.
- **`AGENTS.md`:** the cloud profile in Environment and Branching.
- **Known gaps:** #47 (ways around the guard, such as `git -c alias.p=push`, and `FILE` checks); under "Later".

## 4. GitHub and claude.ai setup (the human does these)

### 4.1 Push the local commits

A cloud session clones the GitHub remote, not the sandbox folder. From the clean clone: fetch the sandbox, review, push as usual.

### 4.2 Protect `main` (repo Settings → Rules → Rulesets → Protect Main Branch)

The ruleset already targets the default branch and requires a pull request (merge commits only), the `verify` status check, no force pushes and no deletion. Set:

- **Enforcement status:** `Active`. While it is `Disabled`, only `guard_git.py` stands between a session and `main`, and #47 lists ways around it.
- **Bypass list:** change the admin role's bypass mode from `Always` to `For pull requests only` (or remove it). Cloud pushes go out under the human's GitHub account; with `Always`, a session could probably push straight to `main` (`VERIFY:` in the trial). The cost: the human also stops pushing to `main` directly and merges PRs instead, which is the same flow as cloud work.

### 4.3 Pull request settings (Settings → General → Pull Requests)

- Untick **Allow squash merging** and **Allow rebase merging**; keep **Allow merge commits**. Approval records pin full commit SHAs, and protected changes must be committed alone; squashing or rebasing would rewrite both.
- Tick **Automatically delete head branches**, so merged `claude/*` branches are cleaned up.

### 4.4 Connect GitHub to Claude

The GitHub account is linked by authorizing it on GitHub, not by email: the Claude account and the GitHub account can use different emails. What matters is which GitHub account the browser is signed in to.

1. In the browser, sign in to GitHub as `andrew-chung-au`.
2. Sign in at <https://claude.ai/code> with the Claude account. When it asks to connect GitHub, approve the request on GitHub's authorization page.
3. Install the Claude GitHub App (<https://github.com/apps/claude/installations/new>) with **Only select repositories** → `vuln-triage`. The repo is public, so sessions could clone it without the App, but the App keeps access limited to this repo.
4. Don't use `/web-setup`. It sends the local `gh` token to the Claude account and replaces the browser connection; the sandbox's token is read-only by design.

Pushes, PRs and Claude's replies to review comments appear under that GitHub username. If the wrong account was linked, disconnect it at <https://claude.ai/customize/connectors>, sign in to the right one on GitHub, and connect again.

Email privacy: if GitHub's **Block command line pushes that expose my email** is on and a cloud commit uses a private email, the push is refused. The trial shows which author email cloud commits use.

### 4.5 Create the environment (claude.ai/code)

| Field | Enter | Why |
|---|---|---|
| Name | `vuln-triage` | |
| Network access | `Limited` | Blocks arbitrary sites, so a session that reads a malicious issue or page can't send data out. Avoid `Full`. |
| Allow package managers | Checked | `make install` (npm) and `make openapi-validate` (uv and PyPI) |
| Allowed domains | `registry-1.docker.io`, `auth.docker.io`, `production.cloudflare.docker.com` (one per line) | Docker Hub, for `docker run hello-world` in the trial and Postgres images for #31. `VERIFY:` whether these are enough; a failed pull names the blocked host. GitHub needs no entry: the GitHub proxy works whatever the network setting. |
| Network secrets | None | Nothing needs a key yet. A secret stored here stays outside the VM. |
| Setup script | None | The repo's `SessionStart` hook does project setup, so it is versioned and reviewed. (If one is ever added: it runs as root, a non-zero exit stops the session from starting, and it should finish within 5 minutes.) |
| Environment variables | None | Anyone using the environment can read them; never put a token or secret here. |

Later, when the app calls the vulnerability APIs, add their hosts to **Allowed domains** (`VERIFY:` the exact hosts then; likely `api.osv.dev`, `www.cisa.gov` and `api.first.org`).

## 5. Trial session (do this once, before real work)

A short, low-cost run that checks every `VERIFY:` above, on a throwaway branch with no product change.

1. With section 4 done, start a session at <https://claude.ai/code> from `main`, or in a terminal in a checkout of the repo: `claude --cloud "Read AGENTS.md. Trial run only: report the session start banner, run make tool-versions, make verify, make issue-dump N=41, git config user.name, git config user.email, and docker run --rm hello-world; create .scratch/trial.md, commit nothing, and report each result."`
2. Check in the session's output:
   - the banner appeared, and `make verify` passed (35 tests) on Node 22;
   - `make issue-dump` worked through `gh api` (so `jq` is present);
   - `docker run` worked (the evidence for #31), or which host was blocked;
   - the branch name prefix (for `guard_git.py`);
   - the commit author name and email.
3. Then ask it to make one empty commit on its branch (`git commit --allow-empty -m "Cloud trial"`) and push that branch. Confirm:
   - the push works and the commit's author on GitHub is as expected;
   - whether the commit has a `Claude-Session: <url>` trailer (the docs say cloud commits get one, although `.claude/settings.json` sets `sessionUrl: false`);
   - `git push origin main` and `git push origin HEAD:main` are both refused. The deny rule `git push * main*` doesn't match `HEAD:main`, so that one tests `guard_git.py`.
4. Close the trial PR without merging; the branch is deleted on GitHub (automatically, or by hand).
5. Record the results in `_docs/ai-usage-log.md` and fix any `VERIFY:` here that turned out different.

## 6. Running an issue in the cloud (routine)

1. **Local, before:** answer the issue's decision questions; push all local commits from the clean clone. Finish or stop any local work on the issue.
2. **Start:** `claude --cloud "Work issue #N following _docs/agent-kit/process.md, as the orchestrator. Ask me at the decision point."` (or start it from claude.ai/code, from `main`). Use the normal permission mode, not auto or bypass, so the `ask` rules on protected files still stop for the human. Answer approvals and decisions in the web or mobile app, including protected commits with `HUMAN_APPROVED=1` after approving the exact diff in the session.
3. **During:** check in when it asks. Answer promptly; idle sessions pause.
4. **End:** the session pushes its branch. On GitHub, open the PR from that branch and do the usual review: `git diff` stat, then the full diff, asking about any file outside the issue's Constraints. CI runs `make verify`. Merge with a merge commit only.
5. **Local, after:** in the sandbox container, `git pull` so the local `main` matches.
6. **Optional:** `claude --teleport <session-id>` brings a session into a local checkout to continue it there. It needs a clean working tree, the same repository, and the session branch pushed.

## 7. Risks

- **Pushes are possible in the cloud.** The proxy can push to any branch. The active ruleset on `main`, the guard hook and the PR review are the controls; review every PR's full diff, especially `.claude/`, `.githooks/`, `Makefile` and `.github/`.
- **The repo's own hooks run in the cloud.** A change to `.claude/settings.json` or a hook script on a branch takes effect in the next session started from that branch. Start sessions only from `main` or branches you have reviewed.
- **Lost work on a reclaimed VM.** Commit and push the branch at milestones; a reclaimed session keeps the conversation but not running subagents.
- **Two environments diverging.** Pull after every merge, and keep each issue in one environment.
