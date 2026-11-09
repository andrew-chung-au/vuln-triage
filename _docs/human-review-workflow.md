# Human review workflow

For the maintainer of this repository, not for people evaluating it. How to review, push and merge work that AI agents produce, and the rules that keep that safe. It describes the method as the repo works now; where it disagrees with `AGENTS.md`, `agent-kit.conf` or the agent-kit procedures, they win and this file should be fixed. Items marked `VERIFY:` are inferred from the record, not confirmed.

## 0. The one-minute picture

- **`main` only changes by merged pull request** (merge commit; no squash, no rebase). The ruleset requires a pull request and the `verify` check, and forbids force-push and deletion. The maintainer's bypass is "for pull requests only", so even the maintainer cannot push to `main` directly.
- **Work lands on a branch**, `claude/<name>` or `claude/issue-NNN-<name>`, from one of two places:
  - **Cloud session:** the session pushes its own branch (the only push an agent may make). The maintainer opens and merges the PR.
  - **Local sandbox:** the agent commits on a branch in the sandbox and **cannot push** (`git push*` is denied, the token is read-only). The maintainer fetches it into the clean clone, pushes the branch, and opens the PR.
- **Issues, comments and closing** go through `make issue-dump`, `make issue-comment` and `make issue-close` (REST), not `gh issue ...` (blocked in the cloud).
- **Protected files** (`AGENTS.md`, `docs/specs.md`, `agent-kit.conf`, `.claude/`, `.opencode/`, parts of the `Makefile`, `_docs/agent-kit/`) change only on the maintainer's approval, in their own commit with `HUMAN_APPROVED=1`, followed by an approval record on the issue. Merge commits keep those SHAs valid, which is why squash and rebase are off.

| | Sandbox (dev container) | Clean clone | Cloud session |
|---|---|---|---|
| Who works there | Agent | The maintainer | Agent |
| Can push? | No | Yes (own login) | Own `claude/*` branch only |
| `make` | Yes | **Never** | Yes |

## 1. Rules that never change

- **Never run `make` in the clean clone** (including `make hooks`, `make verify`). The Makefile is agent-written and the clone holds the maintainer's login.
- **Touch the sandbox folder only with `git fetch sandbox`**, run from the clean clone. Don't open or rebuild the dev container without comparing `.devcontainer/` against the clean clone's copy first.
- **Read the full diff before every merge or push.** A QA PASS or green CI is not proof of a clean diff. Ask about every file outside the issue's constraints.
- **Check these files first:** `Makefile`, `.claude/`, `.opencode/`, `.githooks/`, `.github/`, `.devcontainer/`, `.vscode/`, `.envrc`, `mise.toml`, `.gitmodules`, `agent-kit.conf`, `AGENTS.md`, `docs/specs.md`, `package.json` and lockfiles (new dependencies need approval), and any test that shrank.
- **Start cloud sessions only from `main` or a branch you have reviewed.** The branch's own hooks and `.claude/settings.json` run in the session.
- **One issue, one environment, one branch at a time.**

Examples use `<branch>` for the branch name. Run each command on its own line. `$` lines are commands; `#` lines are notes.

## 2. Flow A: a cloud session's branch

1. **Before launching:** answer the issue's decision questions; push anything local first (the session clones GitHub, not the sandbox).
2. **Launch** in normal permission mode, not auto or bypass, and answer approvals promptly because idle sessions pause:

   ```
   $ claude --cloud "Work issue #N following _docs/agent-kit/process.md, as the orchestrator. Ask me at the decision point."
   ```

3. **At the decision point** the session asks once; approve or reject protected diffs there. Approved protected commits are made in the session with `HUMAN_APPROVED=1`.
4. **When it finishes, review the branch** (clean clone, read-only commands):

   ```
   $ git fetch origin
   $ git log --oneline origin/main..origin/<branch>
   $ git diff origin/main...origin/<branch> --stat
   $ git diff origin/main...origin/<branch>
   ```

   Then open the PR on GitHub (the branch page offers "Compare & pull request"), or with `gh pr create --base main --head <branch> --title "..." --body "..."`. `VERIFY:` `gh pr create` uses GraphQL; it works on the maintainer's machine but not in a cloud session.
5. **Check the PR:** `verify` is green; each protected commit has an approval record on the issue whose SHA matches. Merge with a **merge commit** (web button "Create a merge commit", or `gh pr merge N --merge`). Merged head branches are deleted automatically.
6. **Sync** the clean clone, then the container:

   ```
   $ git switch main
   $ git fetch origin
   $ git merge --ff-only origin/main
   ```

   ```
   # in the dev container
   $ git pull
   ```

## 3. Flow B: a branch the local sandbox agent committed

Run in the clean clone, one command at a time.

1. **Check the clone is clean and current.** `git status --short` should print nothing.

   ```
   $ git status --short
   $ git fetch origin
   ```

2. **Bring in the sandbox's work and list what is new:**

   ```
   $ git fetch sandbox
   $ git branch -r
   $ git log --oneline origin/main..sandbox/<branch>
   ```

3. **Review** (stat first, then everything; use the section 1 list):

   ```
   $ git diff origin/main...sandbox/<branch> --stat
   $ git diff origin/main...sandbox/<branch>
   $ git diff origin/main...sandbox/<branch> -- Makefile .claude .githooks      # one area at a time
   $ git show <sha> --stat                                                       # one commit
   ```

4. **Make a local branch of the same name:**

   ```
   $ git switch -c <branch> sandbox/<branch>
   ```

5. **Dry-run the push check** (section 8; prints which projects it would verify, sends nothing; the "push blocked" message at the end is expected):

   ```
   $ AGENT_PUSH_CHECK_PLAN=1 git push origin HEAD:refs/heads/<branch>
   ```

6. **Push the branch, not `main`.** Always name the destination: a bare `git push` uses the branch's upstream, which for a branch created from the agent's work is the `sandbox` remote, and `sandbox` is the agent's folder, which you only ever fetch from. The push check runs `make install verify` in a throwaway container and blocks the push if it fails.

   ```
   $ git push origin HEAD:refs/heads/<branch>
   ```

   Success ends with `VERIFY: PASS` and a `* [new branch]` line.
7. **Open the PR and merge** as in Flow A steps 4–5.
8. **Sync.** The clean clone as in Flow A step 6. In the container, make sure the agent isn't still on the old branch:

   ```
   # in the dev container
   $ git switch main
   $ git pull
   $ git branch -d <branch>        # refuses if the branch isn't merged, which is the check you want
   ```

   Clean up the clone's copies:

   ```
   $ git branch -d <branch>
   $ git fetch origin --prune
   ```

## 4. Several sessions at once

Parallel branches are normal. Habits that keep it safe:

- Run in parallel only issues that touch different files.
- Expect conflicts in files every session appends to (session summaries are per-issue files, so they don't collide). Resolution rule: **keep both entries**. Have the branch's session merge `main` into the branch (`Merge remote-tracking branch 'origin/main' into <branch>`), then re-review.
- Merge the PRs in dependency order, and after each merge tell the other sessions to merge `main` in. Agents do this themselves when asked; read what they did with `git log --merges --oneline -5`.
- `.scratch/` is shared in the sandbox; a session may skip `make clean-scratch` while another is active. Run it yourself when all are done.

## 5. Between issues

- **Session summary** (`_session-summaries/`) arrives with every issue's branch. Check that it is present and says the same thing as the diff. Its Permission review section lists every approval the agents needed, which feeds the permission sweep.
- **Priority rule:** product work first; tooling (agent kit, hooks, dev container) only if it blocks the next product step or has been scheduled. Don't let a PR smuggle in tooling work.
- **Permission sweep** (`_docs/agent-kit/procedures/permission-sweep.md`, history in `_docs/permission-sweeps.md`): periodically run `make permission-report SINCE=<commit>` in the container and approve or reject the proposed settings changes.
- **Spec and protected changes** are never silent: each has the maintainer's approval in chat or on the issue and an approval record comment.
- **Rebuilding the dev container** is a maintainer step, not mid-issue.

### Handy commands

Clean clone (read-only, safe):

```
$ git log --oneline --graph -15 origin/main        # recent history, with merged PRs
$ git log origin/main..main                        # commits only in your local main (should be empty)
$ git cat-file -p <sha>                            # a commit's parents and message
$ git rev-parse <sha>:AGENTS.md                    # blob ID, to compare with an approval record
$ git show --format= --no-renames --patch <sha> -- AGENTS.md   # the diff an approval record should contain
```

Container:

```
$ make issue-dump N=56          # writes .scratch/issue-56.json and issue-56-comments.json
$ make issue-comment N=56 FILE=.scratch/comment.md
$ make issue-close N=56         # orchestrator only, after QA PASS and a committed session summary
$ make verify                   # tests, whitespace, weakened-test check
$ make verify BASE=origin/main  # same, with a real base on a branch with no upstream
$ make assert-clean             # nothing changed (used after QA)
$ make clean-scratch            # empty .scratch/ (when no session is still using it)
$ make permission-report SINCE=<commit>   # approvals recorded since a commit (for the sweep)
$ make tool-versions            # node, npm, uv, python3, docker
```

Approving a protected change (container; only after you approved the exact diff in chat):

```
$ git add AGENTS.md
$ git status --short
$ git diff --check
$ HUMAN_APPROVED=1 git commit -m "Describe what changed and why"
```

Then the agent posts the approval record on the issue (format: `_docs/agent-kit/procedures/asking-the-human.md`).

## 6. When something goes wrong

| Symptom | What to do |
|---|---|
| Push check: `make verify failed` | Read the container output; ask the agent to fix on the branch; re-fetch and re-review. Don't edit in the clean clone. |
| Push check fails on Node/npm | The image is wrong or missing; see section 8. |
| Push check: "nothing checked" | The new commits touch no project with `agent-kit.conf`; fine for docs-only, but confirm the diff really is. |
| Push check: `agent-kit.conf was removed` | Stop and find out why. Only if intended: `AGENT_PUSH_CHECK_ALLOW_REMOVED=1`. |
| GitHub rejects a push to `main` | Expected. Push a branch and open a PR. |
| PR blocked: `verify` not passing | Open the Actions run; the same `make verify` runs there. A branch with no upstream can hide a weakened test locally: use `make verify BASE=origin/main` in the container. |
| Branch behind `main` after another PR merged | Have the session merge `main` into the branch (keep both sides' entries), then re-review the new diff. |
| `git merge --ff-only origin/main` refuses in the clean clone | Your local `main` has a commit that isn't on GitHub. Don't force; find it with `git log origin/main..main` and ask. |
| A session stopped early | Don't trust partial output. Check `git status --short`, `git log --oneline -5`, the issue's latest comments and any running process before relaunching (`process.md`, "When a role stops early"). |
| Agent action blocked as risky | The agent stops and reports. Look at each blocked command and what it tried; decide to resume or restart fresh (QA: usually fresh). |
| `git fetch sandbox` acts strangely | The agent can edit `.git/config` in the shared folder. Read `<sandbox>/.git/config` as text; don't run git inside that folder. Keep git updated. |

## 7. Checklist before you click merge

- [ ] I read the whole diff, including any file outside the issue's constraints.
- [ ] `verify` is green on the PR (or the push check passed).
- [ ] QA PASS is on the issue and refers to the commit I'm merging.
- [ ] Protected commits are alone, each with an approval record whose SHA and diff match.
- [ ] No new dependency I haven't approved; no weakened or deleted tests.
- [ ] The session summary is present.
- [ ] Merge type is **merge commit**.
- [ ] After merging: clean clone and container are on the new `main`; other sessions know.

## 8. The push-check image

The pre-push hook in the clean clone runs `make install verify` for the pushed commits **inside a throwaway Docker container**, so agent-written code never runs on the maintainer's machine, and blocks the push if it fails. The image is built from [`ci/push-check/Dockerfile`](../ci/push-check/Dockerfile): Node 24.22.0, npm 11.19.1, uv 0.13.1, Python 3.12, git, make, bash, the `libpq` headers, `pip-audit`, `openapi-spec-validator` and Terraform.

**Build and check it** (clean clone; `docker build` and `docker run` are fine because they run the Dockerfile's steps inside Docker):

```
$ docker build -t vulntriage-push-check:1 ci/push-check
$ docker run --rm vulntriage-push-check:1 node --version                     # v24.22.0
$ docker run --rm vulntriage-push-check:1 uv --version                       # uv 0.13.1
$ docker run --rm vulntriage-push-check:1 python3.12 --version               # Python 3.12.15
$ docker run --rm --network none vulntriage-push-check:1 uvx openapi-spec-validator==0.9.0 --help   # proves the tool is cached
$ docker run --rm vulntriage-push-check:1 terraform version                  # Terraform v1.17.0
$ docker image ls vulntriage-push-check:1                                    # target: under about 2 GB
```

If the build fails, the likely points are: the pinned `ghcr.io/astral-sh/uv` tag not existing (use the uv release tarball with its `.sha256` instead), uv placing Python somewhere the link step doesn't look, a Terraform checksum mismatch (never work around it; a changed checksum needs a human look), or a transient network error (run it again). Don't edit the Dockerfile in the clean clone; changes go through an agent so they are committed in the sandbox and reviewed.

**Use it.** Point the hook at the image for the terminal (or add the line to your own `~/.bashrc`):

```
$ export AGENT_PUSH_CHECK_IMAGE=vulntriage-push-check:1
$ AGENT_PUSH_CHECK_PLAN=1 git push origin HEAD:refs/heads/<branch>      # dry run: shows "make -C . install verify" and blocks on purpose
$ git push origin HEAD:refs/heads/<branch>                              # the real push
```

The check needs the internet (don't set `AGENT_PUSH_CHECK_NETWORK=none`) and takes a few minutes. It ends with `PASS` or `PASS WITH WARNINGS` (read the warnings), then git's usual output. A good way to confirm the gate really blocks is a throwaway branch with `backend/uv.lock` removed: `uv sync --locked` fails and the push must be refused. Delete that branch afterwards.

**Rebuild the image** whenever a pinned version changes (Node, npm, uv, Python, `openapi-spec-validator`, `pip-audit`, Terraform). The pins are listed in the comment block at the top of the Dockerfile and must be changed together with `.github/workflows/verify.yml` and the dev container so the three stay in step.

**If you need to push before the image works,** don't bypass the hook with `--no-verify`. Run `make install` and `make verify` in the sandbox (not the clean clone) to see whether the code passes, and ask the agent session for help.
