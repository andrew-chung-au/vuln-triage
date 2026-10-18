# VulnTriage product spec (Stage 1)

Source: `_docs/project-brief.md`. Criteria: `_docs/rubric.md`.
Deferred to later stages: prioritisation formula (Stage 2), LLM guardrails
(Stage 2), API contract (Stage 3), tests (Stage 4).

## Users and roles

| Role | Who | Needs |
|---|---|---|
| Asset owner | Engineer owning an app/service | Know what to fix first, with a correct fix version, without triaging feeds |
| Security lead | Person accountable for exposure | See ranked exposure across assets, get a weekly digest, track overdue fixes |
| Developer (AI-assisted) | Developer using an AI assistant | Ask "which assets are affected by this CVE?" and get a correct answer |

## User stories

### US-1: Register an asset
As a security lead, I register an app/service with its owner, criticality,
and whether it is internet-facing.
- Acceptance: an asset record shows owner, criticality, and internet-facing
  flag; listing assets shows all three fields.

### US-2: Dependencies read automatically
As a security lead, dependencies are picked up from the asset's lockfiles
(`uv.lock`, `requirements.txt`, `package-lock.json`) without manual entry.
- Acceptance: pointing an asset at a repo with a supported lockfile produces
  dependency entries with package name and installed version; no per-package
  typing is needed.

### US-3: Match vulnerabilities with fixed versions
As an asset owner, each dependency version is matched against known
vulnerabilities, showing the fixed version when one exists.
- Acceptance: a dependency with a known vulnerability shows a finding with the
  vulnerability id and the fixed version; a clean dependency shows no finding.

### US-4: Enrich with real-world exploit signals
As an asset owner, each finding shows CISA KEV status, FIRST EPSS score, and
the asset context (criticality, internet-facing).
- Acceptance: a finding displays KEV exploited/not, an EPSS score, and the
  owning asset's criticality and internet-facing flag.

### US-5: Deterministic, explainable ranking
As an asset owner, findings are ranked deterministically and each finding
shows why it ranks where it does. (Formula in Stage 2; no AI involved.)
- Acceptance: re-scoring the same inputs gives the same order; each finding
  shows the reason for its rank (e.g. tier and contributing signals).

### US-6: Plain-language fix brief
As an asset owner, I get a short plain-language brief per finding built from
the structured finding (what is affected, why it matters, what version to
move to). (Guardrail design in Stage 2; brief content tests in Stage 4.)
- Acceptance: an open finding shows a brief naming the affected package and
  the fixed version; the fixed version in the brief matches the finding's
  fixed version.

### US-7: Daily refresh and re-score
As a security lead, KEV/EPSS data is refreshed daily and findings are
re-scored through the API.
- Acceptance: after a scheduled refresh with changed feed data, affected
  findings show updated signals and ranks without manual action.

### US-8: New top-priority finding notifies and opens an issue
As an asset owner, a new top-priority finding notifies me and opens a GitHub
issue automatically.
- Acceptance: a newly appearing top-priority finding produces exactly one
  owner notification and exactly one GitHub issue referencing the finding.

### US-9: Overdue reminders, escalation, weekly digest
As a security lead, overdue findings trigger reminders and escalation, and I
get a weekly digest of exposure.
- Acceptance: an open finding past its due date produces a reminder to the
  owner and an escalation to the security lead; a weekly digest listing open
  findings by rank is delivered once per week.

### US-10: Re-scan closes fixed findings
As an asset owner, a finding closes automatically when a re-scan shows the
fixed version is in place.
- Acceptance: after upgrading to the fixed version and re-scanning, the
  finding status is `fixed` with a timestamp; findings on still-vulnerable
  versions stay open.

### US-11: Dashboard with status and audit trail
As a security lead, I see findings per asset with status (`open` /
`risk accepted` / `fixed`) and an audit trail; risk acceptance happens only
by a human in the dashboard.
- Acceptance: the dashboard lists findings per asset with current status;
  changing status records who, when, and the previous value; no automated
  component sets `risk accepted`.

### US-12: Read-only assistant answers exposure questions
As a developer using an AI assistant, I can ask "which assets are affected by
this CVE?" through the read-only MCP server (tools: `list_top_exposures`,
`which_assets_affected`, `get_finding`, `get_asset`).
- Acceptance: asking for a known CVE returns the affected assets; asking for
  an unknown CVE returns an empty result, not an error; the MCP server offers
  no write operations.

### US-13: The notification journey is instrumented
As a security lead, I can see whether a top-priority finding reached its owner,
as metrics, traces and structured logs that share one trace ID, viewable in
Grafana.
- Acceptance: one scan-to-notification journey emits a metric, a trace and a
  structured log line carrying the same trace ID; Grafana shows them side by
  side.
  No telemetry payload contains advisory text, owner contact details, repository
  URLs, lockfile content or any credential.

### US-14: An alert fires when a top-priority finding is not notified
As an asset owner, if my finding is never delivered to me, an alert fires so
someone looks at it.
- Acceptance: a top-priority finding whose notification fails or does not
  complete within the agreed window fires exactly one alert naming the finding;
  a successful notification fires none.

### US-15: A responder agent wakes on the alert and fixes it
A responder agent wakes on the US-14 alert, reproduces a defect in VulnTriage's
notification path (e.g. a finding with no fixed version or several advisory IDs
fails to format), fixes it, and opens a pull request with the fix
and a test; once merged, CI deploys it to dev.
- Acceptance: the undelivered finding then reaches its owner, the alert
  resolves, and the agent's actions are logged. Production promotion stays
  manual.

## Non-goals (from the brief)

- Servers, network devices, and commercial software.
- Active scanning or penetration testing (the tool only reads inventory).
- Automatic patching (people approve fixes).
- Write tools in the MCP server.

## Edge cases

| # | Case | Expected behaviour |
|---|---|---|
| E1 | Package with no fixed version yet | Finding stays open with "no fixed version"; ranked by exploit signals (tier rule in Stage 2) |
| E2 | Asset with no owner | Finding is still recorded and ranked; notification is held and the asset is flagged ownerless in the dashboard |
| E3 | A feed (OSV / KEV / EPSS) is unavailable | Last-known data is kept and marked stale; scheduled run retries; no findings are deleted |
| E4 | A vulnerability is later removed from a feed | Finding is marked withdrawn, not deleted, with an audit entry |
| E5 | Lockfile fails to parse | Asset shows a scan error; previous findings are kept; error is visible in the dashboard |
| E6 | A telemetry backend is unavailable | Buffer in-process and retry; findings, notifications and alerts are unaffected; the gap is visible in Grafana |

## Open questions

1. What counts as "top-priority" for US-8 notification (which tier)? — to be
   fixed in Stage 2.
2. What are the overdue/escalation time windows for US-9?
3. Which notification channel (email / chat) does the pilot use for US-8/US-9?
4. What is the notification window for US-14 (how long before an undelivered
   top-priority finding fires the alert)?
5. What credential does the responder use, and how is it scoped (branch and
   pull request only, no push to main)? Does a human merge or an automatic
   merge after CI passes complete US-15?

## Assumptions

- ASSUMPTION: "asset criticality" is a small fixed set (e.g.
  low/medium/high/critical); final values in Stage 2.
- ASSUMPTION: pilot repos plus OWASP Juice Shop give real findings; pilot
  asset list in a later stage.
- ASSUMPTION: an asset owner has a name and a contact email; an asset is ownerless when neither is set.

## Suggested additions (not in the plan unless approved)

- None. Severity scores (e.g. CVSS) as a display-only field alongside
  KEV/EPSS, if wanted.
