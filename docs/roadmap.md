# Roadmap

What VulnTriage does today, what is deliberately not built, and what comes next. Nothing here is claimed as working unless the README or another document links to its evidence.

## Where it stands

**Built and tested:** asset ingestion from lockfiles (`uv.lock`, `requirements.txt`, `package-lock.json`); vulnerability matching against OSV; KEV and EPSS enrichment; deterministic, explainable ranking; owner notification by email; a daily scheduler for refresh and re-scan; the audited `open` / `risk accepted` / `fixed` / `withdrawn` lifecycle; a React dashboard; Docker Compose; CI; OpenTelemetry metrics, traces and logs sharing a trace ID, viewed in Grafana; a Grafana alert on an undelivered top-priority finding; and an on-call responder agent that opens a fix pull request (see [responder.md](responder.md)). Infrastructure for an AWS deployment is in [`terraform/`](../terraform) and was run live and then torn down (see [deployment.md](deployment.md)).

**Deliberately not built yet:** the LLM owner brief, n8n workflow automation, a read-only MCP server, and observability and the responder on AWS. The spec marks these as [future development](specs.md), and the API and data model leave room for them, but they are not claimed anywhere as working.

VulnTriage does not actively scan networks or applications, does not patch software automatically, and exposes no write tools through MCP.

## What comes next

Ordered within each theme by value for effort. The order may change. The `X` numbers are the stable labels that the architecture document and code comments cite.

### Operations and hardening

The goal is a deployment that costs about nothing while idle and is safe to leave running.

| Item | What it adds | Rough effort |
|---|---|---|
| **On-demand demo** (X1) | `make demo-up` / `make demo-down`: Terraform apply and destroy, latest production image, seed data loaded through the API, runnable from GitHub Actions by hand. Optionally a scheduled build, smoke test and destroy in CI. One command builds the environment from code; about $0 while down. Persistent pieces cost cents: public GHCR images, a small state bucket, the IAM role and OIDC provider, a budget alert. Rebuilding the same hostname repeatedly can hit Let's Encrypt limits, so tests should reuse a stored certificate or the staging endpoint. | Small; cents per run |
| **Separate production server** (X2) | The same Terraform module with a second instance, for real dev and prod isolation | 1–2 hours; about $15 a month while up |
| **Least-privilege deploy** (X11) | Replace `AWS-RunShellScript` in the dev and prod deploy roles with a custom SSM document that runs only the deploy script, one per environment, so the dev role can no longer run arbitrary commands on the server that holds prod. This closes the weakness noted in the [security review](security-review.md) and [deployment guide](deployment.md#4-check-the-terraform-before-you-apply). | Small to medium; touches the deploy-roles module, the server's SSM document and the deploy workflow |
| **Hardening** (X7) | A managed database or snapshots, secret scanning in CI, Terraform linting and a `terraform plan` check on pull requests | Small each |
| **"Launch demo" button** (X9) | A static portfolio page calls one Lambda function URL, which asks GitHub to run the on-demand demo workflow; a scheduled workflow destroys the environment after a fixed lifetime. The Lambda holds no AWS permission to create resources, only a token scoped to trigger one workflow. Needs a gate (password, approval or CAPTCHA), one environment at a time, a cooldown and daily cap, and a hard lifetime. A full build takes about 10–15 minutes at about $0 idle. | Small to medium; Lambda free tier |

### Product

| Item | What it adds |
|---|---|
| **LLM owner brief** (X4) | A short, readable brief per finding for the owner, written from structured fields only. The model never decides ranking, status or priority. A guardrail rejects any brief that names a fixed version the backend does not hold, and a small fixed evaluation set (P1–P4, no fixed version, no CVE, merged aliases, conflicting ranges, malicious advisory text) checks it. |
| **Read-only MCP server** (X5) | Four read-only tools so agents can query findings. Read-only by construction: the API credential has a role that allows `GET` only. |
| **n8n workflows** (X6) | Routing, reminders and escalation, a weekly digest and a GitHub tracker issue per finding, plus a workflow export. Today the backend scheduler and mailer cover refresh, re-scan and the owner notification. |

### Cloud observability

| Item | What it adds |
|---|---|
| **Grafana and the responder on AWS** (X3) | A live Grafana link, and the full alert-to-deployed-fix chain on a dev environment: the merged fix deploys to dev and the alert clears. The largest item: the responder's LLM credentials and GitHub token move to AWS secrets, and the egress-limited container described in [responder.md](responder.md#what-is-not-guaranteed) becomes the natural place to run it. |
| **Host and runtime metrics** (X10) | CPU, memory and requests per second on the Grafana dashboard, using the Collector's `hostmetrics` receiver (or a node/cAdvisor exporter) and a new dashboard row. HTTP request rate, latency and errors already come from FastAPI auto-instrumentation. |
| **Working dashboard filters** (X14) | Make the journey dashboard's Environment and Version filters work by turning on resource-to-telemetry conversion in the Collector's Prometheus exporter, restoring the two variables, and referencing them in the panel queries. The same change makes the alert annotations that name the environment and version resolve; today those labels are empty. |

## Known limitations

Things I know are imperfect, listed so nobody has to discover them.

- **The responder drill is scripted.** The agent is told the defect is planted. Several details of the real CLI remain unverified (see [responder.md](responder.md#live-run)).
- **The Compose `responder` workflow is manual.** It injected the demo defect that the responder's own pull request removed, so it fails until it is rebased on another way to inject a failure. The leftover `VT_DEMO_DEFECT` switch is also pending cleanup, and a production-promotion check (`P-FLAG-GONE`) fails the promotion if it is still in the tree.
- **Responder guard failure modes (X12).** If saving state fails inside the repeat-alert guard's claim, a fingerprint can stay marked in-flight and a later `resolved` defers until restart; a save failure when finishing can replace the run result; and the in-flight and deferred-release state is in memory only, so a restart mid-run drops a pending release. Each needs one decided behaviour and a test.
- **Responder Compose test code (X13).** The static checker for the Compose file is an indentation-based parser that does not parse a list-form `environment:` entry, so a credential added that way would not be flagged; and one Grafana test snapshots a counter in a way a late event could miscount.
- **Observability runs locally, not on AWS**, and the deploy roles use a generic SSM document (see above).
