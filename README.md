# VulnTriage
Ranks vulnerable dependencies by real-world exploit risk and routes each fix to the owner who can make it.

The project is in the build phase (phase S1 first): the plan in `_docs/` passed review on 2026-10-22 (`_docs/reviews/2026-10-22-plan-review-2.md`), and the application is not yet implemented or deployed. Everything below describes intended functionality and expected behaviour, not something that is currently available.

## The problem

Vulnerabilities are published faster than teams can triage them. Most do not affect a given organisation, but the few that do are hard to find. Hand-maintained asset lists go stale, and severity alone does not show what attackers actually exploit. Findings that never reach an owner do not get fixed.

VulnTriage is for the security function of an organisation with many teams: the security lead, who is accountable for exposure, sees one ranked, explainable view across all assets, and each asset owner (the team that owns the code) gets the findings they can fix. The outcome it aims for is that teams know which findings to act on, and who acts:

- **One ranked view.** Every finding is ranked across all assets from evidence of real-world exploitation (CISA KEV and FIRST EPSS) and from the asset's criticality and internet-facing flag. Every rank comes with its reason, and no AI is involved in the ranking.
- **A named owner.** Each new top-priority finding notifies the asset owner who can fix it.
- **Checked delivery.** Delivery is checked, and an alert fires if a top-priority finding is not delivered.
- **Confirmed fixes.** A finding closes only when a re-scan shows the fixed version is in place.
- **A human decision on risk.** Accepting a risk is a human decision, not an automatic one: an asset owner may accept risk on their own assets and the security lead on any asset. The audit trail records who, when, the previous value and the reason.

VulnTriage addresses that gap: it combines what is installed, what is known to be exploited in the wild, and who owns each asset, then routes the work to that person.

## What VulnTriage does

VulnTriage is intended to cover the whole path from inventory to a fix owned by a person. The LLM brief (step 5), the n8n workflows with reminders, escalation and the weekly digest (step 6), the MCP server and the workflow export are Showcase: they are built after submission and kept in full in the plan. See the Showcase section of [_docs/specs.md](_docs/specs.md#showcase-post-submission). The backend itself runs the daily refresh and scheduled re-scan and delivers the owner notification.

1. **Inventory.** Register apps and services as assets with an owner, a criticality value and an internet-facing flag. Read each asset's dependency files automatically: `uv.lock`, `requirements.txt` and `package-lock.json`.
2. **Match.** Query OSV.dev (the Open Source Vulnerabilities database) for known vulnerabilities in each installed package version, recording the fixed version when one exists.
3. **Enrich.** Add CISA KEV (Cybersecurity and Infrastructure Security Agency Known Exploited Vulnerabilities catalog) status, the FIRST EPSS (Exploit Prediction Scoring System from the Forum of Incident Response and Security Teams) probability score, and the asset's criticality and internet-facing flag.
4. **Rank.** Give every finding a deterministic, explainable rank that shows why it sits where it does. No AI is involved in the ranking.
5. **Brief (Showcase, post-submission).** An LLM (large language model) writes a short plain-language brief for the asset owner from the structured finding. The application rejects any brief whose fixed version differs from the finding's recorded fixed version, and treats advisory text as untrusted data.
6. **Route.** The backend refreshes KEV and EPSS data daily with its own scheduler, re-scores findings, and notifies the owner of a new top-priority finding. Showcase (post-submission): the n8n workflow automation tool opens a GitHub issue for that finding, sends reminders and escalation for overdue findings, and sends the security lead a weekly digest; the workflows are exported as JSON into the repository.
7. **Re-scan.** Close a finding automatically when a re-scan shows that the fixed version is in place.
8. **Watch and respond.** One key journey, scan to owner notification, is instrumented with metrics, traces and structured logs that share a trace ID and are viewable in Grafana. An alert fires when a top-priority finding is not delivered. A responder agent wakes on that alert, opens a pull request with a fix and a test, and logs its actions; promotion to production stays manual. No customer data, advisory text or credentials are sent to telemetry.

Alongside that workflow:

- A planned web dashboard lists findings per asset with status (`open`, `risk accepted`, `fixed`, `withdrawn`) and an audit trail. Only a human can set `risk accepted`.
- Showcase (post-submission): an MCP (Model Context Protocol) server offers read-only tools, `list_top_exposures`, `which_assets_affected`, `get_finding` and `get_asset`, which call the API with a read-only token. It has no write tools.

VulnTriage does not actively scan networks or applications, does not patch software automatically, and does not expose write tools through MCP.

## Expected behaviour

- A new top-priority finding produces exactly one owner notification. Showcase (post-submission): and exactly one GitHub issue referencing the finding.
- A re-scan that finds the fixed version sets the finding to `fixed` with a timestamp. Findings on still-vulnerable versions stay `open`.
- A package with no fixed version stays `open` and is never given an invented fixed version.
- An ownerless asset's findings are still recorded and ranked. The notification is held, and the dashboard flags the asset as ownerless.
- If an OSV.dev, KEV or EPSS feed is unavailable, the last-known data is kept and marked stale, the scheduled run retries, and no findings are deleted.
- Only a human can set `risk accepted`. The audit trail records who made the change, when, and the previous value.
- Showcase (post-submission): the MCP server returns an empty result, not an error, for an unknown CVE, and offers no write tools.
- An undelivered top-priority finding fires exactly one alert. The responder agent's actions are logged, and promotion to production stays manual.

Planning documents:

- [_docs/project-brief.md](_docs/project-brief.md) — problem, workflow, success criteria
- [_docs/rubric.md](_docs/rubric.md) — final project criteria
- [_docs/planning-process.md](_docs/planning-process.md) — staged planning process
- [_docs/specs.md](_docs/specs.md) — product spec (Stage 1); its [Showcase (post-submission)](_docs/specs.md#showcase-post-submission) section holds the stories built after submission
- [_docs/architecture.md](_docs/architecture.md) — architecture (Stage 2)
- [_docs/openapi.yaml](_docs/openapi.yaml) — API contract, OpenAPI 3.1 (Stage 3)
- [_docs/api.md](_docs/api.md) — Stage 3 endpoint table and schema differences (n8n, brief and MCP operations marked Showcase)
- [_docs/testing.md](_docs/testing.md) — test strategy (Stage 4); Showcase cases are marked and not counted in the submission totals
- [_docs/tasks.md](_docs/tasks.md) — build backlog with numbered tasks, coverage summary and dependency chain (Stage 5)
- [_docs/plan-summary.md](_docs/plan-summary.md) — rubric map, top risks, open questions and assumptions (Stage 6)
- [_docs/reviews/2026-10-16-final-rubric-impact.md](_docs/reviews/2026-10-16-final-rubric-impact.md) — impact of the final rubric on the plan (issue #11)
- [_docs/roadmap.md](_docs/roadmap.md) — order of the open work, score checkpoints and progress check-ins
- [_docs/tier-b-build.md](_docs/tier-b-build.md) — consolidated Tier B (S2-S3) build sheet: per-milestone task, dependency, human prerequisite and done-when
- [_docs/tier-c-build.md](_docs/tier-c-build.md) — consolidated Tier C (S4) build sheet: observability, alert and on-call milestones, build order, and the open D4 / human prerequisites
- [_docs/roadmap-showcase.md](_docs/roadmap-showcase.md) — showcase track: work built after the submission
- [_docs/aws-setup.md](_docs/aws-setup.md) — human-side AWS and GitHub setup for the Tier B/C deployment
- [_docs/terraform-verify.md](_docs/terraform-verify.md) — how to verify the `terraform/` modules (static checks, pre-apply review, per-module and acceptance checks)
- [_docs/human-cheatsheet.md](_docs/human-cheatsheet.md) — the human's commands for reviewing, pushing and merging agent work
- [_docs/verify-locally.md](_docs/verify-locally.md) — step-by-step guide to install, run `make test`, and bring the app up locally for an end-to-end check
- [_docs/pending-verification.md](_docs/pending-verification.md) — the cross-issue checklist of build steps left for a Codespace / cloud session / CI (Docker, network, AWS)

AI workflow evidence:

- [_docs/agent-team.md](_docs/agent-team.md) — the agent team, which tool and model run each role, and how work passes between them
- [_docs/ai-usage-log.md](_docs/ai-usage-log.md) — append-only record of AI-assisted work
- [_docs/rubric-evidence.md](_docs/rubric-evidence.md) — rubric criterion status (auditor-maintained)
- [_docs/ai-usage-report.md](_docs/ai-usage-report.md) — AI-assisted workflow report (skeleton)
- [_docs/prompts/README.md](_docs/prompts/README.md) — index of key prompts
