# VulnTriage roadmap: showcase track

Status: adopted 2026-10-22 (human decision H1 in `_docs/roadmap.md`). This file stays separate from `_docs/roadmap.md` after the submission track is merged into it.

Purpose: VulnTriage is also a CV showcase. This track holds the work that scores no rubric points but makes the project stronger to show: the original plan's fuller deployment, the deferred product features, and an on-demand live demo. It is ongoing and has no deadline.

**Rule:** no showcase item starts before the submission is in (phase S5 in the submission track), unless the submission work is blocked waiting on something outside the project. Showcase items are filed as GitHub issues under a "Showcase" milestone when the track starts.

**Cost principle:** about $0 standing cost while the demo is down. Evidence when down: README recordings, screenshots, an architecture diagram and the history of passing workflows.

## Items

Ordered by value for effort; the order may change.

| # | Item | What it adds | Depends on | Rough cost |
|---|---|---|---|---|
| X1 | On-demand demo: `make demo-up` / `make demo-down` (Terraform apply/destroy, latest prod image, seed data loaded through the API), runnable from GitHub Actions by hand; optional scheduled build, smoke test and destroy in CI | One command builds the environment from code; $0 while down | Submission S3 | Small; cents per run |
| X2 | Separate prod server (same Terraform module, a second instance) | Real dev/prod isolation | X1 | 1-2 h; about $15/month while up |
| X3 | Deployed observability and responder in AWS (the original C4, and the C7 drill on dev: the merged fix deploys to dev and the alert clears) | A live Grafana link; the full alert-to-deployed-fix chain | X1 | The largest item; the responder's LLM key and GitHub token move to AWS secrets |
| X4 | LLM brief and its evaluation (tasks 30-31) | The AI feature most interesting to show | Submission done | Medium, plus API cost |
| X5 | MCP server with read-only tools (task 32) | Agent integration | Submission done | Medium |
| X6 | n8n service, routing, reminders, digest and workflow export (tasks 33-36) | Workflow automation; restores the full product story | Submission done | Medium |
| X7 | Hardening: managed database or snapshots, secret scanning in CI, Terraform linting and a `plan` check on pull requests | "Production ready" credibility | X1 | Small each |
| X8 | Write-ups: architecture diagram, the agent-team process, cost notes | The agent-kit process is a story in itself | Submission done | Small |
| X9 | Portfolio "Launch demo" button: a static portfolio site (GitHub Pages) calls one Lambda function URL, which triggers the X1 workflow; a scheduled workflow destroys the environment after a fixed lifetime | A live demo on request with $0 standing cost; a serverless control plane to talk about | X1 | Small to medium; Lambda free tier |
| X10 | Least-privilege deploy: replace `AWS-RunShellScript` in the dev and prod deploy roles with a custom SSM document that runs only the deploy script (one document per environment, so the dev role cannot deploy prod). Closes the Terraform review's F5 (`_docs/reviews/2026-10-25-terraform-pre-apply-review.md`), accepted for submission on 2026-10-25 | The dev role can no longer run arbitrary commands as root on the server that holds prod | Submission S3 | Small to medium; touches `terraform/deploy-roles/`, the server's SSM document and the protected deploy workflow |
| X10 | Host and runtime metrics on the Grafana dashboard: CPU, memory and requests-per-second (the course Part 4 "at minimum" monitoring bar). Add the Collector `hostmetrics` receiver (or a node/cAdvisor exporter) to the `observability/` stack and a dashboard row; the FastAPI HTTP metrics (RPS, latency, errors) already come from the auto-instrumentation (task 23). Not required by the rubric (Observability scores on the US-13 journey); this meets the course's production-monitoring expectation for the showcase | Infra health alongside the app-domain metrics; parity with the course's monitoring | task 24 (the observability stack) | Small |

## X1 design notes

- Persistent pieces cost about $0: GHCR images (public), a small S3 bucket for Terraform state, the IAM role and GitHub OIDC provider (free), a budget alert. Servers, disks and public IPs exist only while the demo is up.
- "Deploy your own": no account IDs or names in the code; region as a variable; public images, so no build step; local state as the default for someone else's account; a README section with prerequisites, rough cost per hour and the destroy step.
- While the demo is down, the deploy workflows skip cleanly instead of failing.
- HTTPS: repeated rebuilds of the same hostname can hit Let's Encrypt limits (VERIFY: about 5 duplicate certificates a week); reuse a stored certificate or use the staging endpoint for test rebuilds.

## X9 design notes

- The Lambda does not run Terraform; it asks GitHub to run the X1 workflow. Its GitHub token is scoped to triggering that one workflow and stored in SSM Parameter Store. It holds no AWS permission to create resources.
- Required protections: a gate (a demo password, an approval request by email, or a CAPTCHA such as Cloudflare Turnstile), one environment at a time (a second press returns the existing link), a cooldown and daily cap, a hard lifetime enforced by the scheduler, and a budget alert (optionally an AWS Budgets action; VERIFY).
- Wait time vs cost: a full build takes about 10-15 minutes at about $0 idle; keeping a stopped server and starting it takes about 1-3 minutes for a few dollars a month in disk. Choose when X9 is built.
- The portfolio site may live in its own repository; only the workflow it triggers lives here.
