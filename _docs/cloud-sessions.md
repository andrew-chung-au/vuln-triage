# Running VulnTriage work in Claude Code cloud sessions

How to use Claude Code on the web (cloud sessions) for this project, what has to change in the repo first, and the steps to follow. Status: proposal, 2026-10-20. The repo changes in step 3 touch protected files and wait for the human's approval.

Sources: <https://code.claude.com/docs/en/claude-code-on-the-web> and <https://code.claude.com/docs/en/cloud-environments>, read 2026-10-20. Details the docs don't state, or that may change, are marked `VERIFY:`. Check them in the trial session (step 5).

## 1. Why cloud sessions, and when to use them

What a cloud session gives this project:

- **Docker, Docker Compose and PostgreSQL 16 are preinstalled** in the cloud VM. The local sandbox has no Docker. That is what blocks #31, so the cloud environment is a candidate for the "Docker-capable environment" that roadmap step 7 must name.
- Python with uv, Node 22 (on `PATH` by default), npm, git and `gh` are preinstalled.
- `CLAUDE.md`, `AGENTS.md`, `.claude/settings.json` (permissions and hooks) and the `.claude/agents/` roles are used as in the local sandbox, because they come with the clone. Your user-level `~/.claude/` settings are not.
- Sessions can run subagents, so one session can run the whole PM → Engineer → QA lifecycle for an issue.
- Usage counts toward the plan's usage limits like any other Claude Code usage; there's no separate charge for the VM. Parallel sessions use limits proportionately. `VERIFY:` how any promotional cloud credits on the account are applied.

**The most efficient way to use it:** one cloud session per issue, running the full lifecycle, with the human's decisions batched up front and at the decision point.

- Use cloud sessions for long, self-contained work: step 7 (architecture), the Stage 3-6 planning documents, and especially the build steps that need Docker or Postgres (#24-#26, #31).
- Keep small edits, roadmap check-ins and quick questions local: they cost the same usage with no benefit.
- Answer the issue's decision questions before launching, so the session doesn't sit idle waiting. An idle VM pauses after a few minutes; a paused VM can be reclaimed, which keeps the conversation but loses running subagents and background commands.
- Run parallel sessions only for issues that touch different files.
- Work on one issue in only one environment (cloud or local sandbox) at a time.

## 2. What differs from the local sandbox, and what that breaks

| Area | Local sandbox (today) | Cloud session | Consequence |
|---|---|---|---|
| Where work lands | Commits on local `main`; the human pushes from a clean clone | Commits on the session's branch; the session pushes that branch, and the human merges a PR | The "commit to `main`, never push" rule needs a cloud variant |
| GitHub write access | Read-only code token | The GitHub proxy allows pushes to **any** branch (it blocks only branch deletion and non-branch pushes) | `main` needs a GitHub ruleset; it becomes the real control |
| `.claude/settings.json` | Denies `git push *` | Same file, same deny | The session can't push its branch: needs a change |
| `guard_git.py` hook | Blocks every `git push` | Same | Needs a cloud-only exception for the session branch |
| `gh issue ...` / `gh pr ...` | Work | **403**: the proxy rejects GraphQL; only `gh api` (REST) works | `make issue-dump` (uses `gh issue view`) fails; comments and closing need REST |
| Node | 24.22.0 (dev container) | 22 by default | CI already uses the runner's default Node, so 22 is acceptable; `VERIFY:` `npm ci` and the 35 tests pass on 22 in the trial |
| Docker / Postgres | Not available | Available | Unblocks #31 |
| Git hooks (`make hooks`) | Installed by `setup.sh` | Not installed | A SessionStart hook must run `make hooks` |
| Starting point | The sandbox folder | A fresh clone of the GitHub remote at the chosen branch | Push local commits **before** starting a session |

## 3. Repo changes needed (proposed; protected files, need approval)

These go through the normal process as one issue (Engineer drafts, human approves the exact diff, protected commits made alone with `HUMAN_APPROVED=1`, QA). Under the roadmap's priority rule this counts as tooling, so it should be one small issue, justified because it unblocks the Docker work. The PM files it once you approve this plan.

1. **`Makefile`: GitHub issue targets that use REST only,** so they work both locally and in the cloud:
   - `issue-dump`: replace `gh issue view` with `gh api repos/{owner}/{repo}/issues/$(N)` plus `gh api --paginate repos/{owner}/{repo}/issues/$(N)/comments`, written to `.scratch/issue-$(N).json` and `.scratch/issue-$(N)-comments.json`.
   - New `issue-comment N=<n> FILE=<path>`: `gh api repos/{owner}/{repo}/issues/$(N)/comments -F body=@$(FILE)`.
   - New `issue-close N=<n>`: `gh api -X PATCH repos/{owner}/{repo}/issues/$(N) -f state=closed`.
   - `VERIFY:` the `{owner}/{repo}` placeholders resolve from the clone's remote in a cloud session.
2. **`.claude/settings.json`:**
   - Add allow rules `Bash(gh api repos/*)` for reads (comments and closing stay behind the make targets).
   - Keep `Bash(git push *)` as a deny locally, but make the cloud exception possible: deny rules beat hooks, so replace the blanket deny with denies for `git push * main*`, `git push --force*`, `git push -f*` and `git push --delete*`, and let `guard_git.py` decide the rest.
   - Add a `SessionStart` hook that runs `_docs/agent-kit/claude-code/hooks/cloud_session_start.sh`.
3. **`_docs/agent-kit/claude-code/hooks/guard_git.py`:** allow `git push -u origin <current branch>` only when `CLAUDE_CODE_REMOTE` is `true`, the current branch is not `main`, and the branch starts with `claude/` (`VERIFY:` the branch name prefix cloud sessions use). Block everything else as today.
4. **New `_docs/agent-kit/claude-code/hooks/cloud_session_start.sh`:** exits at once unless `CLAUDE_CODE_REMOTE` is `true`; otherwise runs `make install` (skipped when `frontend/node_modules` is already current) and `make hooks`, then prints `Environment: Claude Code cloud session (Docker available; push only this session's branch)`. The banner tells the agent where it is, so agents never need to read environment variables themselves.
5. **`AGENTS.md`:**
   - **Environment:** add the cloud profile: Docker and Postgres available, `gh` limited to REST via the make targets, the session start banner.
   - **Branching:** "Local sandbox: commit directly to `main`; never push. Cloud session: commit on the session's branch; push only that branch; the human reviews the PR and merges it with a merge commit."
   - **Commands:** the new `issue-comment` and `issue-close` targets.
   - The rule "Don't push" gains the same cloud exception.
6. **Not changed:** the agent kit's `environments.md` (protected kit text). Record the cloud profile in this file and `AGENTS.md` only; propose a kit update later if the profile works.

## 4. GitHub and claude.ai setup (the human does these)

1. **Push the local commits first.** A cloud session clones the GitHub remote, not the sandbox folder. From the clean clone: fetch the sandbox, review, push as usual.
2. **Protect `main` with a ruleset** (repo Settings → Rules → Rulesets), because the cloud proxy doesn't limit which branches a push updates:
   - target the default branch;
   - require a pull request before merging;
   - require the `verify` status check (from `.github/workflows/verify.yml`) to pass;
   - block force pushes and deletion.
   - Bypass: yourself only, so your own clean-clone pushes still work (`VERIFY:` whether you want to keep pushing to `main` directly, or switch to PRs for everything).
3. **Allow only merge commits** (Settings → General → Pull Requests): turn off "squash merging" and "rebase merging". Approval records pin full commit SHAs, and protected changes must be committed alone; squashing or rebasing would rewrite both.
4. **Connect GitHub to Claude:** at <https://claude.ai/code>, authorize the Claude GitHub App and install it on `andrew-chung-au/vuln-triage` only ("Only select repositories"), not all repositories. (The alternative, `/web-setup`, sends your local `gh` token to your Claude account. Don't use it from the sandbox, whose token is read-only by design.)
5. **Create an environment** for this repo in claude.ai/code:
   - Network access: **Trusted** (the default). It allows the package registries and GitHub, which is all planning and the frontend need. Later, the app's OSV, KEV and EPSS calls need a **Custom** allowlist (`VERIFY:` the exact hosts at that time).
   - Environment variables: **none**. Anyone using the environment can read them; never put a token or secret there. If a secret is needed later, use the environment's network secrets, which stay outside the VM.
   - Setup script: none. The repo's SessionStart hook (step 3.4) does project setup, so it is versioned and reviewed.

## 5. Trial session (do this once, before real work)

A short, low-cost run that checks every `VERIFY:` above, on a throwaway branch with no product change.

1. From the clean clone (with the step 3 changes merged and pushed), start a session at <https://claude.ai/code>, or in a terminal in a checkout of the repo: `claude --cloud "Read AGENTS.md. Trial run only: report the session start banner, run make tool-versions, make verify, make issue-dump N=41, and docker run --rm hello-world; create .scratch/trial.md, commit nothing, and report each result."`
2. Check in the session's output:
   - the banner appeared, and `make verify` passed (35 tests) on Node 22;
   - `make issue-dump` worked through `gh api`;
   - `docker run` worked (this is the evidence for step 7 and #31);
   - the branch name prefix (for `guard_git.py`).
3. Then ask it to make one empty commit on its branch (`git commit --allow-empty -m "Cloud trial"`, so no file changes) and push that branch. Confirm the push works, and that `git push origin main` is refused by the guard.
4. Close the trial PR without merging, and delete the branch on GitHub.
5. Record the results in `_docs/ai-usage-log.md` and fix any `VERIFY:` here that turned out different.

## 6. Running an issue in the cloud (routine)

1. **Local, before:** answer the issue's decision questions; push all local commits from the clean clone.
2. **Start:** `claude --cloud "Work issue #N following _docs/agent-kit/process.md, as the orchestrator. Ask me at the decision point."` (or start it from claude.ai/code). Use the web or mobile app to answer approvals and decisions; approvals work the same way, including protected commits with `HUMAN_APPROVED=1` after you approve the exact diff in the session.
3. **During:** check in when it asks. Answer promptly; idle sessions pause.
4. **End:** the session pushes its branch. On GitHub, open the PR from that branch and do your usual review: `git diff` stat, then the full diff, asking about any file outside the issue's Constraints. CI runs `make verify`. Merge with a merge commit only.
5. **Local, after:** in the sandbox container, `git pull` so the local `main` matches. Don't start local work on the same issue while a cloud session is open.
6. **Optional:** `claude --teleport <session-id>` brings a session into a local checkout to continue it there. It needs a clean working tree, the same repository, and the session branch pushed.

## 7. Risks

- **Pushes are possible in the cloud.** The proxy can push to any branch. The ruleset on `main`, the guard hook and your PR review are the controls; review every PR's full diff, especially `.claude/`, `.githooks/`, `Makefile` and `.github/`.
- **The repo's own hooks run in the cloud.** A change to `.claude/settings.json` or a hook script on a branch takes effect in the next session started from that branch. Start sessions only from `main` or branches you have reviewed.
- **Lost work on a reclaimed VM.** Commit and push the branch at milestones; a reclaimed session keeps the conversation but not running subagents.
- **Two environments diverging.** Pull after every merge, and keep each issue in one environment.
