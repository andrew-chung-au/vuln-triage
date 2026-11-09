# Human tasks: review list for the portfolio tidy

**For the repository owner only. Delete this file when you have worked through it.** It lists only the things I could not or should not decide for you. The earlier 239-line tasklist (AWS applies, per-issue verification runs, sweeps) described the first build and is preserved at the `v1.0.0` tag.

## Done

- **LICENSE:** MIT added (copyright 2026 Andrew Chung).
- **AWS teardown:** confirmed complete by the owner.
- **Demo video:** confirmed still available.
- **Channel link:** removed; the video link stays.
- **Protected-change approval records:** posted on the tracking issue for the tidy.

## Needs checking outside the repository

I cannot see your AWS account or GitHub settings.

| # | Item | What to check |
|---|---|---|
| 5 | **GitHub environments, secrets and variables.** | The `dev` and `production` environments and any secrets or variables (`AWS_REGION`, `AWS_DEV_ROLE_ARN`, `AWS_PROD_ROLE_ARN`) point at roles that no longer exist. Delete them, or leave them. The deploy workflow now skips unless the repository variable `DEPLOY_ENABLED` is `true`, so nothing deploys while it is unset. |
| 6 | **The `protect-main` ruleset.** | It requires seven checks (`verify`, `unit`, `frontend`, `sqlite-integration`, `postgres-integration`, `telemetry`, `openapi-validation`). This PR does not rename any of them, but confirm the PR can merge. |
| 7 | **Stale branches, issues and pull requests.** | Old `claude/*` branches; open issues such as #160 (responder tracking) that describe work as pending. The issue tracker is part of what an employer sees, so close or annotate what is finished. |
| 9 | **Repository presentation.** | Add a description and topics, and pin the repository on your profile, since the repo is how an employer will find it. |
| 10 | **Public demo credentials in history.** | The old README published a demo login (`reviewer` / `vt-reviewer-demo`) for the dev site. It is gone from the working tree. It remains in git history and at `v1.0.0`. The server no longer exists, so this is harmless, but do not reuse that password anywhere. |

## Decisions I made that you may want to reverse

- **Removed from the working tree (still at `v1.0.0`):** the AI usage log and report, the prompt archive, the grading criteria and evidence (and the rubric-auditor role and skill), plan-stage reviews and scaffolding (planning process, plan summary, task backlog, tier build sheets, roadmap diary), cloud-session and drill runbooks, one-off change proposals, and the top-level `agent-kit/` mirror (a stale duplicate of `_docs/agent-kit/`).
- **Kept as is:** `_session-summaries/` (the permission sweep reads them), the permission-sweep procedure and report, `.agent-logs/`, the OpenCode permission-log plugin, and `_docs/agent-kit/`. These can be simplified when you upgrade the agent kit. At that point the kit could move out of `_docs/`.
- **Layout:** `docs/` holds the product and engineering documentation for readers; `_docs/` now holds only maintainer and agent-process material (`agent-kit/`, `human-review-workflow.md`, `permission-sweeps.md`).
- **Workflows:** `deploy.yml` is gated on `vars.DEPLOY_ENABLED == 'true'`. The nightly schedules on `alert.yml` and `responder.yml` are removed (both stay runnable by hand). `responder.yml` is documented as known failing.
- **Left alone:** "task N" and "#NNN" citations inside code comments and tests. They still resolve through GitHub issues and the `v1.0.0` tag, and rewriting hundreds of them was not worth the risk. `docs/testing.md` explains this.
- **Rewritten from several documents into one:** development, deployment, responder, roadmap, ai-assisted-development and the maintainer review workflow (which absorbed the useful parts of the push-check image guide). The detailed per-flag CLI notes were condensed into `docs/responder.md`; the originals are at `v1.0.0` if you need the finer detail.

## What I could not verify

See the pull request description for the checks that ran and the ones that did not.
