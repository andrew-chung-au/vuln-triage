Status: DRAFT

# Lovable prompt: mocked VulnTriage frontend (issue #14)

Purpose: the prompt the human pastes into Lovable to generate a mocked React
frontend. Its services layer becomes the input to `_docs/api.md` (Stage 3 of
`_docs/planning-process.md`).

v1 is a discovery build: what it reveals feeds #3, #4 and `_docs/api.md`, and
later changes are made by coding agents after import, not by rebuilding in
Lovable.

Sources, read at commit `123e37a`:
- `_docs/specs.md` (US-1, US-4, US-5, US-10, US-11; edge cases E1, E2, E4, E5;
  Assumptions)
- `_docs/project-brief.md` (fixed stack: React frontend with all backend calls
  in one service layer)
- issue #6 (acceptance criteria on the finding-status list)

Open dependencies (the prompt uses each assumption until the issue is
resolved; where unsure, it uses the richer model):
- #3 (which fixed version applies): ASSUMPTION: a finding has one or more
  affected version ranges, each with its own fixed version or a
  `no fixed version` state (`specs.md` E1).
- #4 (advisory aliases): ASSUMPTION: a finding shows its vulnerability id plus
  a list of alias ids (zero or more; for example a GHSA id with a CVE alias).
- #5 (feeds, matching and ingestion): ASSUMPTION: an asset never scanned shows
  `not yet scanned`, distinct from "no findings" (review finding 9); the
  repository reference is a URL text field (finding 7).
- #6 (status, brief display, audit trail): ASSUMPTION: a rejected brief shows
  the structured finding with a `brief unavailable` marker; statuses are
  `open`, `risk accepted`, `fixed` (`specs.md` US-11) and `withdrawn`
  (`specs.md` E4; named in #6), where `withdrawn` is set only when a feed
  drops the vulnerability, adds an audit entry, and keeps the finding listed
  ("stale" in #6 is not a status: `specs.md` E3 uses it for feed data); any
  signed-in user may accept risk with a non-empty reason; login is one mocked fictional user whose name is the
  audit "who" (finding 13). Login and the reason are not in `specs.md` yet.
- Stage 2 (`_docs/architecture.md`, not written): ASSUMPTION: tiers P1-P4 from
  `_docs/planning-process.md` § Stage 2, ordered within a tier as the data
  gives; criticality is low/medium/high/critical (`specs.md` Assumptions).

Everything under `## Prompt`, and nothing else, is pasted into Lovable.

## Prompt

Build a React single-page app called VulnTriage. It ranks vulnerable software dependencies by real-world exploit risk and shows who owns each fix. This is a prototype with no backend.

Architecture
- Centralise every backend call in one services layer, and create a mock implementation of it so the whole app runs without a real backend.
- No backend, database, auth provider or third-party integration. Make no network calls outside the services layer; the mock returns in-memory data.
- Keep the services layer to small typed functions, one per read or write, so they can later call a real API.

Screens: build exactly these six, and no others.

1. Login: a mocked sign-in with one fictional user. Wrong credentials show an error message and do not sign in. The signed-in user's name is the "who" in audit entries.

2. Findings dashboard: findings ranked by priority tier, P1 (highest) to P4; within a tier, keep the order the data gives. Each row shows tier, asset, package, status, and why it ranks there: KEV yes/no, EPSS score (or "EPSS: n/a" when missing), asset criticality and internet-facing flag. Status is one of open, risk accepted, fixed or withdrawn; withdrawn findings stay listed and visibly marked, never removed. Findings can be filtered or grouped by asset and filtered by status. With no findings, show an empty state.

3. Finding detail, showing:
- the vulnerability id and all alias ids
- each affected version range with its own fixed version, or "no fixed version" for a range without one; a finding can have several ranges
- the AI brief or, when the brief was rejected, the structured finding with a visible "brief unavailable" marker
- KEV, EPSS and the asset context (owner, criticality, internet-facing)
- status: open, risk accepted, fixed or withdrawn; fixed shows its fixed timestamp; withdrawn notes the vulnerability left its feed
- the audit trail: who, when, previous value, new value

4. Risk acceptance: reached from finding detail and done by the signed-in user. A reason is required: an empty or whitespace-only reason is rejected with a message, and the status does not change. Success sets the status to "risk accepted" and adds an audit entry that includes the reason. Only this human action sets "risk accepted"; nothing automated does.

5. Asset list: name, owner, criticality and internet-facing flag. An asset with no owner is flagged "ownerless". An asset whose lockfile failed to parse shows "scan error". An asset never scanned shows "not yet scanned", which is different from "no findings".

6. Asset registration: a form with name (required), owner (optional), criticality (low, medium, high or critical), internet-facing flag, and repository URL (a text field). Submitting without a name is rejected with a message.

Out of scope: Grafana, n8n and MCP screens; any real API; visual polish beyond a clean, readable layout.

Mock data: realistic, with fictional assets, owners and packages. Include at least:
- one finding in each tier P1, P2, P3 and P4
- one finding whose only affected range has no fixed version
- one finding with two or more affected ranges, one of which has "no fixed version"
- one finding with at least two ids (for example a GHSA id with a CVE alias), and one with no aliases
- one finding with "brief unavailable"
- one "risk accepted" finding with its audit entry
- one "fixed" finding with a fixed timestamp
- one "withdrawn" finding with its audit entry
- one finding with "EPSS: n/a"
- one ownerless asset
- one asset with a scan error
- one asset not yet scanned

Owner emails use only the example.com, example.org or example.net domains. Mock brief text contains no links other than one advisory reference. No real people's names, secrets or API keys.

Tests: write tests for the core logic:
- rank ordering (tier first, then data order within a tier)
- validation of the risk acceptance reason (empty and whitespace-only reasons are rejected and the status is unchanged)
- the mock services layer (it returns the mock data, and accepting risk records an audit entry with the reason)
- affected range display (each range shows its fixed version, or "no fixed version" when it has none)

## Follow-up prompts

None yet.
