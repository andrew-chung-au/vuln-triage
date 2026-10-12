# VulnTriage planning process

You are the planning engineer for VulnTriage. Your job is to produce a
complete, reviewable build plan. Do NOT write application code, create the app
scaffold, or add dependencies. Planning documents only.

Inputs: `_docs/project-brief.md` (the brief) and `_docs/rubric.md` (the final
project criteria). Read both before every stage.

## How to work
- Work in STAGES, one stage per response. At the end of each stage: save the
  file, commit it with a clear message, run the stage's checklist, report
  PASS/FAIL per item, then STOP and wait for me.
- If something is unclear, write it under "Open questions" in the stage's file
  and make a labelled assumption ("ASSUMPTION: ...") so you can continue. Never
  silently fill gaps.
- Do not invent details about external APIs (endpoints, fields, rate limits,
  licence terms). If you are not certain, write "VERIFY:" next to it.
- Stay inside the brief. If you think something important is missing, propose
  it under "Suggested additions"; do not add it to the plan.
- Keep documents concise: short sections, tables where items share attributes.
- For each planning file you create, add a link to it in README.md.
- Commit locally. Never push.

## Stage 0: Save the brief (done)
`_docs/project-brief.md` exists.

## Stage 1: Product spec → `_docs/specs.md`
- Users and roles (e.g. asset owner, security lead, developer using an AI assistant)
- User stories, each with checkable acceptance criteria ("someone can point at
  the result and say yes or no")
- Non-goals (copy the out-of-scope list from the brief, plus any you add, labelled)
- Edge cases (e.g. a package with no fixed version yet, an asset with no owner,
  a feed that is unavailable, a vulnerability later removed from a feed)
- Leave the prioritisation formula, LLM guardrails, API and tests to their stages.
Checklist: every MVP feature in the brief has at least one story; every story
has acceptance criteria; non-goals match the brief.

## Stage 2: Architecture → `_docs/architecture.md`
- Components and responsibilities: React frontend, FastAPI backend, Postgres,
  n8n, MCP server, LLM. State which component owns each step of the workflow.
- The workflow end to end: inventory → match → enrich → prioritise → brief →
  route → re-scan, including what triggers each run.
- Data model: entities, key fields, relationships (assets, dependencies,
  vulnerabilities, findings, status history/audit trail).
- Prioritisation: tiered and deterministic. Refine these rules, mark every
  threshold as ASSUMPTION, define tie-breaks fully, and give a worked example
  with at least three findings:
  - P1: on CISA KEV and the asset is internet-facing or critical
  - P2: on KEV elsewhere, or EPSS ≥ threshold on an internet-facing or
    critical asset
  - P3: fix available, no exploitation evidence
  - P4: everything else
  - Within a tier: EPSS (higher first), then asset criticality, then oldest
    finding first
- The LLM brief: inputs, structured output schema, and the guardrail that
  rejects any brief whose fix version differs from OSV's fixed version. The
  model and version are pinned in configuration. A rejected brief is logged,
  and the owner still receives the structured finding without the AI brief:
  the guardrail must never block a notification. Advisory text is untrusted
  data.
- External data sources and how each is called, cached and refreshed (mark
  unknowns VERIFY:).
- MCP server: the read-only tools, their inputs and outputs, and how it calls
  the API (never the database directly) with its own read-only token.
- Security boundaries: authentication, secrets handling, prompt-injection
  handling, and what each credential can and cannot do.
Checklist: every user story maps to at least one component; no component calls
the database except the backend; the formula has a worked example with
tie-breaks; every external call is listed with its caching approach; the
rejected-brief path is specified.

## Stage 3: API contract → `_docs/openapi.yaml`
Draft the OpenAPI spec the frontend, n8n and MCP server will all use: every
endpoint, method, request and response body, and which endpoints need
authentication.
Checklist: every user story that needs data has an endpoint; n8n's and the MCP
server's calls are covered; schemas match the data model.

## Stage 4: Test strategy → `_docs/testing.md`
- Unit tests: dependency file parsers, prioritisation tiers and tie-breaks,
  brief guardrail
- Integration tests: real Postgres via Docker Compose; external APIs replaced by
  stored response fixtures so CI never depends on live feeds
- End-to-end: register asset → findings appear → ranked correctly → owner notified
- LLM brief evaluation: how a small sample of briefs is checked
- Rejected-brief path: a wrong fix version is rejected, logged, and the owner
  still receives the structured finding
- Security tests: a malicious advisory text fixture that tries to instruct the LLM
Checklist: every acceptance criterion is covered by at least one test type.

## Stage 5: Backlog → `_docs/tasks.md`
Use this template for each task:

  ## <number>. <title>
  Goal: <one line>
  Description: <two or three sentences>
  Depends on: <task numbers, or "none">
  Covers: <user stories / rubric criteria it serves>

Rules: task 1 is an empty project with one passing test. Each task is small
enough for one session and independent enough to hand to someone who has not
read the others. Order by dependency. Dependencies must be one-way: check for
cycles and list the dependency chain at the end.
Checklist: no cycles; every user story is covered by a task; every criterion in
`_docs/rubric.md` is covered by a task.

## Stage 6: Rubric map and risks → `_docs/plan-summary.md`
- A table mapping each criterion in `_docs/rubric.md` to the tasks and
  documents that satisfy it
- Top risks with mitigations
- All open questions and assumptions collected from every stage
Checklist: all 14 criteria appear; nothing is unmapped.  Also update the Reviewer prompt’s reading list to match the new paths:Read `_docs/project-brief.md` and `_docs/rubric.md`, then `_docs/specs.md`,
`_docs/architecture.md`, `_docs/openapi.yaml`, `_docs/testing.md`,
`_docs/tasks.md` and `_docs/plan-summary.md`.
