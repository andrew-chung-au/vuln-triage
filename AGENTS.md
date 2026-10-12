# AGENTS.md

<!-- PROJECT: specific to this folder. Protected: changes need human approval. -->

VulnTriage ranks vulnerable software dependencies by real-world exploit risk and routes each fix to its owner.
Layout: `AGENTS.md`, `agent-kit.conf`, `Makefile`, `opencode.json`, `.opencode/agents/` (OpenCode role definitions), `_docs/agent-kit/` (agent kit, version 1.9), `_docs/project-brief.md` (project brief, to be written in planning).

Current phase: PLANNING. No application code until the plan in _docs/ has passed review.

## Commands

<!-- Every slot is a make target or "none". To be filled in when the project is scaffolded. -->

- **Install:** `none`
- **Run:** `none`
- **Test (all):** `none`
- **Test (one file):** `none`
- **Verify:** `make verify`: whitespace and weakened-test checks (no test command yet: no code exists). How to use it: `_docs/agent-kit/procedures/verify.md`.
- **Assert clean:** `make assert-clean`: confirms nothing in this folder changed (used after QA).
- **E2E:** `none`
- **New migration:** `none`

## Project settings

- **Environment:** local sandbox (dev container; you can't push; no Docker). See `_docs/agent-kit/environments.md`.
- **Branching:** commit directly to `main`; the human reviews and pushes from the clean clone.
- **Dependencies:** no stack scaffolded yet; ask before adding any dependency.
- **Session summaries:** `_session-summaries/`, named `issue-<NNN>-<short-name>.md` for issue work and `planning-<YYYY-MM-DD>-<short-name>.md` for planning.

## Project rules

- No new dependencies without asking.
- Commit regularly; never push (the human reviews and pushes from the clean clone).
- Mark any uncertain external API detail with "VERIFY:".
- The project brief will live at `_docs/project-brief.md`.

## Project gotchas

- There is no Docker in this container, so anything needing Docker Compose must wait for a codespace or a Compose-based container recipe (see `_docs/agent-kit/environments.md`).

<!-- SHARED: from _docs/agent-kit/templates/AGENTS.md.template. Change it there first, then copy it here. -->

## Conventions

- The product spec is `_docs/specs.md`. The human owns it: propose changes, and make them only after approval. If it doesn't exist yet, the project is in planning (see `_docs/agent-kit/process.md`).
- Run project commands through `make`. If you need a command that has no target, propose a new Makefile target instead of documenting a raw command. When a target changes, propose the matching change to Commands above.
- Change only files the current task needs. If you spot an unrelated problem, note it in the session summary instead of fixing it.
- Don't delete files or data you didn't create in this task, including git-ignored files and Docker volumes, without the human's approval. The exception is `make clean-scratch` at the end of an issue, which the process calls for.
- Ask before adding a dependency, or before installing anything large into `.scratch/` (browsers, toolchains). Delete such installs when the issue is done.
- Stage explicit paths only (`git add path/to/file`). Never use `git add .`, `git add -A` or `git commit -a`.
- Before each commit, show `git status --short`, `git diff --check`, and the exact paths being staged.
- Don't add co-author lines to commit messages yourself. Any attribution comes from your tool's settings.
- Protected files, listed in `agent-kit.conf` (including this file and the spec), change only with human approval. Commit them with `HUMAN_APPROVED=1` only after the human has approved that specific change in this session.
- Never bypass git hooks with `--no-verify`. If a hook blocks you, fix the cause or ask the human.
- Never open, print or copy `.env` files; use `.env.example`.
- Keep all work inside this folder. Put scratch files in `.scratch/` here (git-ignored), never in `/tmp` or other outside locations.
- Don't read the AI tool's settings, your home folder or environment variables. If something depends on how the tool or the machine is set up, ask the human, or report it as a finding.
- Edit files only with your tool's editing feature, so every change shows as a diff. Never edit files from the shell (`sed -i`, `cat >> file <<EOF`, scripts that rewrite files).
- Prefer your tool's built-in file reading and searching over shell commands, and `make` targets over raw commands. Run commands from this folder. Every command your tool can't check stops the human for approval, so avoid these forms:
  - Shell variables and expansions (`$VAR`, `$(...)`, `$?`). Your tool already reports exit codes.
  - `cd` followed by other commands, and chains of several commands. Run one command, read the result, then run the next.
  - Environment variable prefixes. Write `make <target> VAR=value`, not `VAR=value make <target>`. The one exception is `HUMAN_APPROVED=1 git commit` for an approved protected change: your tool will ask the human first, and that's intended.
  - Paths outside this folder, including `/dev/null` and `/tmp`. Send output to `.scratch/` instead.
  - Inline code (`python3 -c`, heredocs), loops, and `sed` or `awk` scripts. Write a script in `.scratch/` and run it, for example `python3 .scratch/check_alert.py` or `bash .scratch/check.sh`.
- If a command is blocked or needs approval only because the tool couldn't check it, rewrite it in a simpler form and try once before asking. If the human declines a request, or your tool blocks an action as risky, don't pursue the same goal another way: stop and report what you were trying to do, and ask how to proceed.
- Give every command a description that says what it does and why, naming the issue and step, for example "Send the test alert to check criterion 4 of #10". Your tool shows it when it asks the human.
- Before anything that needs the human's approval on its merits (system changes, stopping a process you didn't start, anything outside this folder, installs, protected commits, anything that can't be undone), send an approval request first. Ask decisions as decision questions. Both layouts are in `_docs/agent-kit/procedures/asking-the-human.md`. As a subagent, don't run the command: return the request to the orchestrator.
- Start long-running processes (servers, watchers) only through `<name>-start` and `<name>-stop` make targets, or a `.scratch/` script that records the process ID it started and stops only that process. Wait for results with a timeout, never an open-ended loop. Never stop a process you didn't start; ask the human.
- Don't type injection or bypass attempts as live shell commands. Put them in tests, or in a `.scratch/` script for a one-off check.
- Don't change system configuration (firewall rules, installed packages, services, git config) without the human's approval, even temporarily. The approval request includes the command that undoes the change; record in the session summary whether it was undone.
- Never edit or delete existing issue comments; post a new comment instead. Other roles' comments are part of the record.
- Start every issue comment with your role (`PM:`, `Engineer:`, `QA:` or `Orchestrator:`). All roles usually share one GitHub account, so the label is the only way to tell them apart.
- Don't push. The human reviews the diff and pushes; the pre-push hook runs `make verify`.
- Work isn't done until `make verify` passes. Never weaken or skip a test to make it pass.
- Working a GitHub issue → `_docs/agent-kit/process.md`. The main session orchestrates; each role follows its file in `_docs/agent-kit/team/`.
