# VulnTriage product spec (Stage 1)

Status: draft, pending the 2026-10-16 review issues

Source: `_docs/project-brief.md`. Criteria: `_docs/rubric.md`.
Deferred to later stages: prioritisation formula (Stage 2), LLM guardrails
(Stage 2), API contract (Stage 3), tests (Stage 4).

## Users and roles

| Role | Who | Needs |
|---|---|---|
| Asset owner | Engineer owning an app/service | Know what to fix first, with a correct fix version, without triaging feeds |
| Security lead | Person accountable for exposure | See ranked exposure across assets, get a weekly digest, track overdue fixes |
| Developer (AI-assisted) | Developer using an AI assistant | Ask "which assets are affected by this CVE?" and get a correct answer |

## Defined terms

### fixed version for this dependency

The **fixed version for this dependency** is the lowest version greater than
the installed version that is outside every affected range containing the
installed version, considering all ranges and all advisories for that
vulnerability so that the upgrade clears every one. If no such version exists,
the finding has **no fixed version for this dependency**.

- An advisory with fixed versions on several release lines (for example 1.2.5
  on the 1.x line and 2.0.1 on the 2.x line): installed 1.2.0 → `1.2.5`;
  installed 2.0.0 → `2.0.1`.
- `VERIFY:` an advisory may have no `fixed` event, and two advisories for the
  same vulnerability may list different fixed versions; in both cases apply
  the rule to all ranges and all advisories.
- `VERIFY:` OSV advisories represent affected versions as ranges with
  `introduced` and `fixed` events, and the same vulnerability may have several
  ranges or several advisories.

The fixed version for this dependency is the only value the US-6 brief
guardrail compares against.

## User stories

### US-1: Register an asset
As a security lead, I register an app/service with its owner, criticality,
and whether it is internet-facing.
- Acceptance: an asset record shows the owner's name and contact email (or an
  ownerless marker when both are unset), criticality, and internet-facing flag;
  listing assets shows all three fields.

### US-2: Dependencies read automatically
As a security lead, dependencies are picked up automatically from the asset's
GitHub repository URL, read with a read-only token scoped to repository
contents. The files read are `uv.lock`, `requirements.txt` and
`package-lock.json`; no per-package typing is needed. This GitHub repository
URL is the only ingestion mechanism in the MVP; there is no local-path or
upload option.
- Acceptance: `uv.lock` produces a dependency entry for every package,
  including transitive entries, with package name and installed version.
- Acceptance: `requirements.txt` produces a dependency entry for every direct
  requirement, with package name and installed version, or an explicit
  "version unknown" with a visible warning.
- Acceptance: `package-lock.json` produces a dependency entry for every
  package, including transitive entries, with package name and installed
  version.
- Transitive dependencies are in scope for `uv.lock` and `package-lock.json`
  (every entry). For `requirements.txt` only direct entries are in scope.

### US-3: Match vulnerabilities with fixed versions
As an asset owner, each dependency version is matched against known
vulnerabilities, showing the fixed version for this dependency when one exists.
Each finding records the vulnerability's primary id and all its alias ids (for
example GHSA, PYSEC and CVE), including aliases when the primary id is not a
CVE. (`VERIFY:` OSV advisories carry a primary id and an `aliases` list; the
primary id may not be a CVE.)
- Acceptance: a dependency with a known vulnerability shows a finding with the
  vulnerability's primary id, all its alias ids, and the fixed version for this
  dependency when one exists; a clean dependency shows no finding.

### US-4: Enrich with real-world exploit signals
As an asset owner, each finding shows CISA KEV status, FIRST EPSS score, and
the asset context (criticality, internet-facing).
- Acceptance: a finding displays KEV exploited/not or "not listed", an EPSS
  score or `n/a`, and the owning asset's criticality and internet-facing flag.

### US-5: Deterministic, explainable ranking
As an asset owner, findings are ranked deterministically and each finding
shows why it ranks where it does. (Formula in Stage 2; no AI involved.)
- Acceptance: re-scoring the same inputs gives the same order; each finding
  shows the reason for its rank (e.g. tier and contributing signals).

### US-6: Plain-language fix brief
As an asset owner, I get a short plain-language brief per finding built from
the structured finding (what is affected, why it matters, what version to
move to). (Guardrail design in Stage 2; brief content tests in Stage 4.)
- Acceptance: an open finding shows either a brief whose fix version matches
  the finding's fixed version for this dependency, or the structured finding
  with a visible "brief unavailable" marker; never a brief with a mismatched
  version.

### US-7: Daily refresh and re-score
As a security lead, KEV/EPSS data is refreshed daily and findings are
re-scored through the API.
- Acceptance: after a scheduled refresh with changed feed data, affected
  findings show updated signals and ranks without manual action.

### US-8: New top-priority finding notifies and opens an issue
As an asset owner, a new top-priority finding notifies me and opens a GitHub
issue automatically. "New" means the first time this finding enters the top
tier in its current lifecycle. It covers a newly created finding and an
existing finding promoted into the top tier by a daily KEV/EPSS refresh. The
top tier is `P1` as defined by the Stage 2 formula, and Open question 1 is a
blocker for Stage 2 sign-off.
- Acceptance: a newly appearing top-priority finding produces exactly one
  owner notification and exactly one GitHub issue referencing the finding.
- Acceptance: a finding that leaves and re-enters the top tier without being
  fixed produces no second GitHub issue and no second owner notification; a
  finding that was `fixed` and reappears (E7) starts a new lifecycle and may
  produce at most one new issue and one new notification.
- Acceptance: exactly one owner notification and exactly one GitHub issue are
  created per finding lifecycle, even if the daily refresh runs twice or
  retries after a partial failure. The idempotency basis is the finding
  lifecycle.
- Acceptance: for an ownerless asset, the notification is held and the asset
  is flagged ownerless (E2), while the GitHub issue is still opened once.
- The issue is opened in the dedicated tracker repo `vuln-triage-findings`
  using one narrowly scoped token. Closing the issue does not change the
  finding's status; n8n may comment on or close the issue after a re-scan
  marks the finding `fixed`.

### US-9: Overdue reminders, escalation, weekly digest
As a security lead, overdue findings trigger reminders and escalation, and I
get a weekly digest of exposure. A finding's due date is its first detection
time plus the window for the highest tier the finding has reached. A tier rise
moves the due date earlier to the new tier's window; a tier drop never moves it
later; an already-overdue finding stays overdue. The windows are an
`ASSUMPTION:` until Stage 2. The escalation target is one configured
security-lead contact (name and email) in deployment configuration, not an
asset record.
- Acceptance: an open finding past its due date produces a reminder to the
  owner and an escalation to the security lead; a weekly digest listing open
  findings by rank is delivered once per week.
- Acceptance: a missing security-lead contact is a visible configuration
  error, not a silent drop.

### US-10: Re-scan closes fixed findings
As an asset owner, a finding closes automatically when a re-scan shows the
installed version no longer falls in any affected range.
- Acceptance: after upgrading to a version outside every affected range (for
  example 2.0.3 when the fixed version for this dependency is 2.0.1) and
  re-scanning, the finding status is `fixed` with a timestamp; if the installed
  version is still inside any affected range (even after an upgrade), the
  finding stays `open`.

### US-11: Dashboard with status and audit trail
As a security lead, I see findings per asset with status (`open` /
`risk accepted` / `fixed`) and an audit trail; risk acceptance happens only
by a human in the dashboard. Dashboard users sign in, and the signed-in user is
recorded as "who" in every audit entry. Both the asset owner and the security
lead may set `risk accepted`. No automated component may set it. The
authentication mechanism is defined in Stage 2.
- Acceptance: the dashboard lists findings per asset with current status;
  changing status records who, when, and the previous value; no automated
  component sets `risk accepted`.
- Acceptance: risk acceptance records a non-empty reason in the audit entry;
  an empty or whitespace-only reason is rejected and the status does not
  change.

### US-12: Read-only assistant answers exposure questions
As a developer using an AI assistant, I can ask "which assets are affected by
this CVE?" through the read-only MCP server (tools: `list_top_exposures`,
`which_assets_affected`, `get_finding`, `get_asset`). A lookup by any alias id
returns the same finding(s) as a lookup by the primary id.
- Acceptance: asking for a known CVE returns the affected assets.
- Acceptance: a finding stored under a GHSA id with a CVE alias is returned
  when asked by that CVE.
- Acceptance: a CVE known to the system but affecting no registered asset
  returns an empty asset list, not an error, and states that the CVE is known;
  a CVE not known to the system returns an empty asset list, not an error, and
  states that the CVE is unknown. The two results are distinguishable; the
  exact wire shape is fixed in Stage 3.
- Acceptance: the MCP server offers no write operations.

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

### US-16: n8n workflows are exported into the repo
As a security lead, the n8n workflows that route findings are exported as JSON
into the repository, so the workflow the repo runs is reviewable.
- Acceptance: each workflow has a committed JSON file under `n8n/workflows/`,
  named after the workflow, and the exported file is the workflow the repo
  runs.

## Finding statuses

A finding has exactly one status. This is the complete list:

| Status | Set by | Transition and meaning | Audit entry |
|---|---|---|---|
| `open` | Scan or re-scan | Created when a scanned dependency is vulnerable; set again when a `fixed` finding reappears (E7). | Creation and each status change record the previous value, actor and timestamp. |
| `risk accepted` | Asset owner or security lead, in the dashboard | A human accepts the risk; requires a non-empty reason. | Records the signed-in user, timestamp, previous value and the non-empty reason. |
| `fixed` | Re-scan | The installed version no longer falls in any affected range (US-10). | Records the previous value, actor and timestamp. |
| `withdrawn` | Scheduled refresh | `ASSUMPTION:` an addition to the brief's three statuses. The vulnerability is removed from a feed (E4); the finding is not deleted. | Records the previous value, the feed and the timestamp. |

`stale` (E3) is a feed marker, not a finding status. The asset scan status
(E3, E5) is not a finding status either.

## Asset scan status

Each asset has exactly one scan status, with exactly these values: `not yet
scanned`, `scan failed`, `scanned, clean`. A `scan failed` status also records
one failure reason: `feed unavailable` or `lockfile parse error`. Findings are
listed separately. `scanned, clean` means a successful scan matched nothing.
The scan status is not a finding status, and the `stale` feed marker is not a
finding status.

## Non-goals (from the brief)

- Servers, network devices, and commercial software.
- Active scanning or penetration testing (the tool only reads inventory).
- Automatic patching (people approve fixes).
- Write tools in the MCP server.

## Edge cases

| # | Case | Expected behaviour |
|---|---|---|
| E1 | Package with no fixed version yet | The finding has no fixed version for this dependency. It stays `open` and shows the display text "no fixed version" (display text, not a finding status); it is ranked by exploit signals (tier rule in Stage 2). Any brief that names a fix version is rejected, and the structured finding is delivered without the AI brief. |
| E2 | Asset with no owner | Finding is still recorded and ranked; notification is held and the asset is flagged ownerless in the dashboard |
| E3 | A feed (OSV / KEV / EPSS) is unavailable | OSV unavailable on a new asset's first scan: the asset shows `scan failed` with reason `feed unavailable`, no findings are created, and it is not shown as `scanned, clean`. On a later scan with a feed unavailable, last-known data and findings are kept and marked stale, not deleted, and the asset shows `scan failed` with reason `feed unavailable`; the scheduled run retries |
| E4 | A vulnerability is later removed from a feed | Finding status becomes `withdrawn` (`ASSUMPTION:` addition to the brief's three statuses), not deleted, with an audit entry recording the previous value and the feed |
| E5 | Lockfile fails to parse | The asset's scan status is `scan failed` with reason `lockfile parse error`; previous findings are kept; the error is visible in the dashboard |
| E6 | A telemetry backend is unavailable | Buffer in-process and retry; findings, notifications and alerts are unaffected; the gap is visible in Grafana |
| E7 | A `fixed` finding's vulnerable version comes back (downgrade or revert) | The finding returns to `open` with an audit entry giving the previous value and the reason, and starts a new notification lifecycle under the US-8 rules: at most one new GitHub issue and one new owner notification if it enters the top tier |
| E8 | A `risk accepted` finding's signals escalate (for example it becomes KEV-listed) | The status stays `risk accepted` because a human set it, but the finding is flagged "signals changed" and the owner and security lead are notified once. It does not silently reopen or silently stay quiet |
| E9 | One vulnerability is reported under two ids (for example a GHSA and a PYSEC advisory for the same CVE) | `VERIFY:` OSV records carry alias sets. Two records are the same vulnerability when their alias sets intersect; the finding is keyed by the CVE when present, otherwise by the primary advisory id. The asset gets one finding per (asset, package, vulnerability identity), with all advisory ids and affected ranges attached, not two findings. Its fixed version is derived under the "fixed version for this dependency" rule from all merged affected ranges. One finding means at most one US-8 notification per lifecycle |
| E10 | A `requirements.txt` entry has no exact version (`requests>=2`, bare `requests`, an environment marker, or a `-r` include) | Record the entry with "version unknown", show a visible warning, and make no OSV match; an unknown version does not make the asset `scanned, clean`. `-r` includes are resolved only inside the repository; an include outside the repository or a remote URL is refused and reported as a scan warning, never fetched |
| E11 | A vulnerability has no CVE alias | `VERIFY:` KEV and EPSS are keyed by CVE. KEV shows "not listed", EPSS shows "n/a", and the finding is still recorded and ranked. No advisory is dropped only because it has no CVE |

## Open questions

1. What counts as "top-priority" for US-8 notification (which tier)? — the
   top tier is `P1`, defined by Stage 2; this is a blocker for Stage 2
   sign-off.
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
- ASSUMPTION: an asset owner has a name and a contact email. An asset is ownerless when both are unset; if only one is set, the asset is not ownerless and the dashboard shows the missing field. Whether a partial owner is notified is decided in Stage 2.

## Suggested additions (not in the plan unless approved)

- Severity scores (e.g. CVSS) as a display-only field alongside KEV/EPSS, if
  wanted.
