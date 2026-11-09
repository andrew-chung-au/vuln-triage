# How this was built: AI agents under human control

VulnTriage was built with AI coding agents working inside a deliberate process. The point of the process is that an agent can do a lot of the typing, but a person owns the specification, approves every change to the rules the agents follow, and reviews every diff before it reaches `main`. This page summarises the setup. The working rules themselves are in [`AGENTS.md`](../AGENTS.md) and the agent kit in [`_docs/agent-kit/`](../_docs/agent-kit).

## The team

Work moves through separate roles, each defined by a file that both supported tools read. Claude Code and OpenCode use the same `AGENTS.md`, so there is one source of truth; each tool's config asks before editing the other's.

| Role | Does | Does not |
|---|---|---|
| **Orchestrator** (the main session) | Launches the other roles, passes work between them, brings every question to the human, runs the checks that prove QA changed nothing, closes issues | Plan the backlog, implement or test |
| **PM** | Grooms one GitHub issue before anyone implements it, against the spec; proposes backlog changes | Write code; change issues without approval |
| **Software Engineer** | Implements one groomed issue, writes tests, runs the verification gate | Edit protected files, close the issue or push |
| **QA Engineer** | Checks finished work against the acceptance criteria, runs the gate itself, tries to get around each limit, then posts `QA: PASS` or `QA: FAIL` | Fix or edit anything |
| **The human** | Owns the spec and the protected files, answers decision questions, reviews the diff, merges | |

Role definitions: [`.claude/agents/`](../.claude/agents) and [`.opencode/agents/`](../.opencode/agents), backed by [`_docs/agent-kit/team/`](../_docs/agent-kit/team). Every issue comment starts with its role (`PM:`, `Engineer:`, `QA:`, `Orchestrator:`), because the roles share one GitHub account and the label is the only way to tell them apart.

## The loop

1. The PM grooms an issue into acceptance criteria. Grooming is never skipped.
2. The Engineer implements it, commits, and runs **`make verify`**: all test suites, the frontend type check, a whitespace check, and a check that no test was deleted or weakened. In Claude Code a hook re-runs the gate when the Engineer tries to finish.
3. QA runs in a **fresh, isolated context**, never the one that built the work, and a different tool or model is preferred. The orchestrator then asserts the working tree is clean and HEAD hasn't moved; if QA changed anything its verdict is discarded and it runs again.
4. At a single decision point the orchestrator gathers everything that needs the human (proposed rule changes, spec notes, the Engineer's open choices, QA's risks) and asks once, with the reasons, alternatives and a recommendation.
5. The orchestrator writes a session summary and closes the issue. A person reviews the diff and merges a pull request.

## Guardrails

- **Protected files.** `AGENTS.md`, the spec, the agent kit, the Makefile, the agent configs and the hook settings are listed in [`agent-kit.conf`](../agent-kit.conf). A commit touching them is blocked by a git hook unless it carries `HUMAN_APPROVED=1`, which an agent may set only after the human approved that exact diff. An approval record is then posted on the issue.
- **Permissions.** Agents get a narrow allow list (`make` targets, read-only git and GitHub queries) and ask for everything else. A periodic *permission sweep* counts the approvals recorded in session summaries and proposes settings changes for the human to approve. Repeated approvals become validated `make` targets rather than broader shell rules.
- **No unreviewed pushes.** `main` is protected by a ruleset; agents push at most their own branch; pre-push runs the verification gate in a throwaway container. The maintainer-side procedure is in [`_docs/human-review-workflow.md`](../_docs/human-review-workflow.md).
- **Untrusted text.** Issue text and comments not written by a project role or the human are treated as data, not instructions.
- **Secrets.** Agents never read `.env` files, hold AWS credentials, or run `terraform apply`.

## What this produced

A per-issue [session summary](../_session-summaries) records what each agent did, which tool and model ran it, and which approvals it needed. The summaries are the audit trail for the development process and the input to the permission sweeps. The full planning, review and AI-usage record from the first build is preserved at the `v1.0.0` tag.

## What it did not solve

- A green gate is not a clean diff, which is why a person reads every diff. Independent QA found five separate bypasses in the responder's diff gate, each fixed one at a time, and a live run later showed that the real CLI read a rule pattern differently from the project's model of it.
- Rule-based permissions are fragile (see the argument-matching limits in [responder.md](responder.md#what-is-not-guaranteed)); a `make` target with validation is safer than a clever allow pattern.
- The process is heavy for a small project. It was worth building to find out where the friction is, and the agent kit is due for a simplifying upgrade.
