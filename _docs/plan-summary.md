# VulnTriage plan summary (Stage 6)

Status: Stage 6 deliverable, draft for review

Sources: [`_docs/rubric.md`](rubric.md), [`_docs/project-brief.md`](project-brief.md), [`_docs/specs.md`](specs.md), [`_docs/architecture.md`](architecture.md), [`_docs/api.md`](api.md), [`_docs/testing.md`](testing.md), [`_docs/tasks.md`](tasks.md), [`_docs/roadmap.md`](roadmap.md) and [`_docs/reviews/2026-10-16-final-rubric-impact.md`](reviews/2026-10-16-final-rubric-impact.md).

## How to read

- This is **planned coverage, not evidence**. [`_docs/rubric-evidence.md`](rubric-evidence.md) is the only record of what is currently MET, PARTIAL or MISSING; no row here awards points or claims a status.
- Criterion names, order and maximum points are copied verbatim from [`_docs/rubric.md`](rubric.md) (12 criteria, 24 points, 10 to pass).
- `task N` means the `## N.` heading in [`_docs/tasks.md`](tasks.md); it is not a GitHub issue number. Issue numbers, where they exist, are cross-references only.
- Milestones A, B and C and their targets (A 12, B 19, C 24 points) are the targets in [`_docs/reviews/2026-10-16-final-rubric-impact.md`](reviews/2026-10-16-final-rubric-impact.md) §5 and [`_docs/roadmap.md`](roadmap.md) §Tier B and Tier C milestones. They are targets, not current evidence.
- Duplicate coverage is explicit and allowed: a task may serve several criteria, and a criterion may need several tasks.
- In the register, keys are `file:tag` because tags repeat across files (for example `architecture.md:A1` and `api.md:A1 (#27)` are different entries). Status values are `open`, `proposed answer`, `resolved`, `deferred` and `VERIFY`. Line numbers were read at commit `1edc468` and may move.

## Rubric map

| # | Criterion | Max | Tasks (`_docs/tasks.md`) | Documents (section) | Earliest milestone |
|---|---|---|---|---|---|
| 1 | Problem Description | 2 | task 2 | [`README.md`](../README.md) §The problem, §What VulnTriage does, §Expected behaviour | A |
| 2 | Product Specification | 2 | task 2 | [`_docs/specs.md`](specs.md) §User stories (acceptance line per story); [`_docs/tasks.md`](tasks.md) §Coverage summary; public [issue tracker](https://github.com/andrew-chung-au/vuln-triage/issues) | A |
| 3 | Agent Team Specification | 2 | task 2 | [`_docs/agent-team.md`](agent-team.md) §Roles and handover; [`_docs/agent-kit/process.md`](agent-kit/process.md) §Roles and §Lifecycle | A |
| 4 | Context Management | 2 | task 2 | [`AGENTS.md`](../AGENTS.md) §Where to read more; [`_docs/agent-kit/process.md`](agent-kit/process.md); [`_docs/agent-kit/team/software-engineer.md`](agent-kit/team/software-engineer.md) | A |
| 5 | Application | 2 | task 1, task 3, task 4, task 5, task 6, task 7, task 8, task 9, task 10, task 11, task 12, task 14; task 15¹ | [`_docs/architecture.md`](architecture.md) §Components, §Data model, §Rubric enablement; [`_docs/api.md`](api.md) §Endpoint table; [`_docs/tasks.md`](tasks.md) task 15 (Compose) | A |
| 6 | Testing | 2 | task 1, task 13, task 14, task 16, task 20, task 31, task 36 | [`_docs/testing.md`](testing.md) §Test levels and where they run, §CI jobs and triggers, §Traceability matrix | A |
| 7 | Containerization | 2 | task 15 | [`_docs/tasks.md`](tasks.md) task 15; [`_docs/architecture.md`](architecture.md) §Development environment, §Rubric enablement; [`_docs/testing.md`](testing.md) §Integration tests (T-A1) | B |
| 8 | Deployment | 2 | task 17, task 18 | [`_docs/architecture.md`](architecture.md) §Deployment; [`_docs/roadmap.md`](roadmap.md) §Tier B (B4-B6) | B |
| 9 | CI/CD | 3 | task 19, task 20, task 21 | [`_docs/architecture.md`](architecture.md) §Deployment (Pipeline); [`_docs/testing.md`](testing.md) §CI jobs and triggers | B |
| 10 | Observability | 2 | task 23, task 24, task 25 | [`_docs/architecture.md`](architecture.md) §Observability; [`_docs/testing.md`](testing.md) §Telemetry: US-13 | C |
| 11 | Alerting on User Impact | 1 | task 26, task 27 | [`_docs/architecture.md`](architecture.md) §Observability (US-14 alert rule); [`_docs/testing.md`](testing.md) §Alerting: US-14 | C |
| 12 | On-Call Agent | 2 | task 28, task 29 | [`_docs/architecture.md`](architecture.md) §Responder agent; [`_docs/testing.md`](testing.md) §Responder: US-15 | C |

**Total: 24 points; pass mark 10** ([`_docs/rubric.md`](rubric.md) line 4). The 12 rows above are in rubric order.

¹ `_docs/tasks.md` §Coverage summary assigns the end-to-end application to tasks 1, 3-12 and 14, and notes that task 15 (the Compose stack) supplies the criterion's "runs locally with a single command" clause; [`_docs/roadmap.md`](roadmap.md) B2 assigns Application to task 15 for that clause. Task 15's own `Covers:` line names only Containerization. The sources now agree on task 15's clause-level role; see Source discrepancies D1 (resolved). The caveat does not unmask the row: tasks 1, 3-12 and 14 already cover the end-to-end application.

## Source discrepancies

| # | Sources | Difference | Handling |
|---|---|---|---|
| D1 | [`_docs/tasks.md`](tasks.md) §Coverage summary vs [`_docs/roadmap.md`](roadmap.md) B2 | tasks.md lists Application tasks as 1, 3-12 and 14; roadmap B2 assigns Application to task 15 (Compose stack, the "single command" clause), but task 15's `Covers:` line names only Containerization | **Resolved in #95:** [`_docs/tasks.md`](tasks.md) §Coverage summary now separates the two Application clauses: the row lists tasks 1, 3-12 and 14 for the end-to-end application, and a note records that task 15 (the Compose stack) supplies the criterion's "runs locally with a single command" clause. [`_docs/roadmap.md`](roadmap.md) B2 assigns Application to task 15 for that clause. Task 15's own `Covers:` line still names only Containerization, and no task was renumbered, added or removed. Cross-referenced from the Application row's footnote ¹. |
| D2 | [`_docs/specs.md`](specs.md) line 3 vs §Open questions | The status line says "reviewed", but Open questions 2-4 remain open while architecture proposes answers | Register keeps Q2-Q4 as `proposed answer`; spec wording change is a proposed follow-up, not applied. |
| D3 | [`_docs/specs.md`](specs.md) Open question 2 vs [`_docs/architecture.md`](architecture.md) A27 | Q2 is open; A27 proposes P1 7 / P2 14 / P3 30 / P4 90 days | Both kept; A27 is a proposed answer pending human confirmation. |
| D4 | [`_docs/specs.md`](specs.md) Open questions 3-4 vs [`_docs/architecture.md`](architecture.md) A26, A33 | Q3 (channel) and Q4 (US-14 window) are open; A26 proposes email/SMTP and A33 proposes 30 minutes | Both kept; no answer is treated as resolved. |
| D5 | [`_docs/roadmap.md`](roadmap.md) D1 vs [`_docs/architecture.md`](architecture.md) Open question 6 | D1 proposes closing Q6 with the Module 4 pattern; Q6 is still listed as open | Both kept; D1 is a proposed answer, not an approval. |
| D6 | [`README.md`](../README.md) line 27 vs [`_docs/specs.md`](specs.md) §Finding statuses | README lists dashboard statuses as `open`, `risk accepted`, `fixed`; the spec's complete list adds `withdrawn` | Recorded only. This summary does not copy the three-value list; README fix is out of scope (proposed follow-up). |
| D7 | [`_docs/roadmap.md`](roadmap.md) §Open decisions | The table numbers 11 rows; rows 1-4 are resolved/withdrawn and rows 5-11 carry the live labels D1-D7 | Register keys the live decisions `roadmap.md:D1`-`roadmap.md:D7`; rows 1-4 are noted as resolved/withdrawn, not open. |

## Top risks

Every mitigation has an owner. A mitigation labelled `human` is a human-only action (account, domain, dev-container rebuild, production approval, teardown); no destructive or account-creating step is assigned to the Engineer.

| # | Risk (coverage area) | Source | Trigger / impact | Mitigation | Owner | Step / milestone | Residual risk |
|---|---|---|---|---|---|---|---|
| R1 | No Docker in the local sandbox; Docker/Compose environment is human-dependent (a) | [`AGENTS.md`](../AGENTS.md) §Project gotchas; [`_docs/roadmap.md`](roadmap.md) step 16, prerequisites; #31/#48 | `docker compose up`, Postgres integration and the Compose telemetry/alert jobs cannot run in the sandbox; Containerization, the Application single-command clause and Compose Testing wait | Compose dev-container recipe (#31), cloud `docker-start` (#48), Compose jobs in CI; Tier A uses only the local no-Docker rows ([`_docs/architecture.md`](architecture.md) §Development environment) | `human` for the dev-container rebuild; agents for the CI jobs | Step 16; B2, C3 | Rebuild or cloud route can slip; Tier A is unaffected |
| R2 | AWS account, budget, domain/TLS and the GitHub `production` environment (b) | [`_docs/roadmap.md`](roadmap.md) prerequisites, B4-B6; [`_docs/architecture.md`](architecture.md) §Deployment, Open question 7 | B4-B6 cannot deploy; Deployment and the CD half of CI/CD stay at 0-1 points | Budget alert before any stack (A37), decide domain/TLS (D3), VERIFY the `production` protection rules, and use the "If AWS is slow" order if it delays | `human` for the account, budget, domain and production approval; agents write templates | B4-B6; step 17 | Schedule risk; D5 fallback (Compose/kind demo) is named but not chosen |
| R3 | Unresolved LLM provider/model and responder runtime (c) | [`_docs/architecture.md`](architecture.md) A23, Open question 9, §Responder agent; [`_docs/roadmap.md`](roadmap.md) prerequisites | Task 30 and C6 cannot pin a model or runtime; tests and CI must not call a paid provider | Choose with the human before task 30/C6; `LLM_MODE=stub` and `RESPONDER_MODE=stub` in tests; 20 s timeout and the "brief unavailable" path keep the product working | `human` chooses; agents implement the stubs | Task 30 (Committed), C6 | Provider capabilities, pricing and retention remain `VERIFY:` |
| R4 | External API unknowns, fixture capture and no live feeds in CI (d) | [`_docs/architecture.md`](architecture.md) §External data sources; `VERIFY:` items in [`_docs/api.md`](api.md) and [`_docs/testing.md`](testing.md) | OSV/KEV/EPSS/GitHub/SES/LLM/Grafana details may differ; live feeds would make tests flaky or need secrets | Committed fixtures plus `U-NET`/`I-NET` network guards; deliberate `make record-fixtures` capture; resolve each `VERIFY:` at its build task | Agents; `human` approves dependency additions and deliberate captures | Tasks 5, 6, 13, 16; B2/B3 | Fixtures drift from live feeds until re-captured |
| R5 | Telemetry exclusions and advisory prompt injection (e) | [`_docs/specs.md`](specs.md) US-13, US-15; [`_docs/architecture.md`](architecture.md) §Security boundaries, §Observability | Excluded data (advisory text, owner contact, repository URL, lockfile content, credentials) could reach telemetry; advisory text could steer the brief, responder or a notification | Allowlist helper in code plus a Collector processor; `T-REFUSE`; `S-*` per flow; responder read-only tokens and "untrusted data" instructions; alert labels carry finding id and tier only | Agents | Tasks 23-25, 28-29; C2-C6 | Auto-instrumented attributes can leak if the allowlist misses a key |
| R6 | Scope and schedule: Tier C estimate above the course's ~20 hours; committed LLM/MCP/n8n scope (f) | [`_docs/reviews/2026-10-16-final-rubric-impact.md`](reviews/2026-10-16-final-rubric-impact.md) §5; [`_docs/tasks.md`](tasks.md) Committed scope | 26-30 h estimate exceeds ~20 h; committed scope competes with the scoring path | Scoring path first (Milestones A-B-C), committed scope last; Tier A passes at 12 points; shrink the application slice or accept the overrun at the human's decision | `human` owns scope/time; orchestrator/PM own sequence | Step 17; all milestones | Tier C overrun is accepted or the application shrinks |
| R7 | Step 12 backlog filing is `doing`; step 14 depends on steps 12 and 13 (g) | [`_docs/roadmap.md`](roadmap.md) steps 12-14 and check-in 2026-10-22 | B/C/Committed issues are not all filed, so step 14 cannot start and the plan review waits | This summary maps task numbers, not issue numbers; finish the B/C/Committed filing at each milestone boundary before step 14; the summary does not claim those issues exist | Orchestrator/PM; `human` approves filing | Steps 12-14 | Step 14 cannot start until step 12 is `done` |
| R8 | The demo defect must be removed before production (h) | [`_docs/tasks.md`](tasks.md) task 29; [`_docs/testing.md`](testing.md) §Responder (`P-FLAG-GONE`); [`_docs/architecture.md`](architecture.md) A35 | `VT_DEMO_DEFECT=notify_no_fix` could remain in production code, leaving a deliberate failure path | Production startup refuses the flag (`P-PROD-REFUSAL`); `P-FLAG-GONE` blocks promotion until the path is gone; cleanup commit/PR; promotion stays manual | Agents write and remove the path; `human` merges and promotes | Task 29; C6-C7 | A bypass of the manual gate could still promote the flag, so the test is the guard |
| R9 | Mapping and points drift as stage documents change (i) | [`_docs/rubric.md`](rubric.md); [`_docs/tasks.md`](tasks.md); any later stage edit | A later edit can add/remove a task or change a `Covers:` line, invalidating a row; scores could be read as current | Task numbers are canonical; re-check this map after any stage-document change; the auditor alone updates [`_docs/rubric-evidence.md`](rubric-evidence.md); this document records conflicts instead of editing sources | Orchestrator/PM; reviewer at step 14 | Steps 12-14 and after any stage change | A stale row can survive until the next check |

## Open questions and assumptions

Scope per source follows the Stage 6 issue: `specs.md` open questions 1-5 and every `ASSUMPTION:` (including inline ones); `architecture.md` open questions 1-11 and A1-A41; `api.md` `ASSUMPTION:` items and unresolved `VERIFY:` items; `testing.md` `T-A1`-`T-A8` and `VERIFY:` rows; `tasks.md` `ASSUMPTION:` and `VERIFY:` lines; `roadmap.md` live decisions D1-D7 as a separate group. The brief has no labelled items. No item is renumbered or deleted; resolved items keep their entry.

### `_docs/specs.md`

| Key | Item | Status | Owner / where resolved |
|---|---|---|---|
| `specs.md:Q1` | What counts as "top-priority" for the US-8 notification (which tier)? | resolved | [`_docs/architecture.md`](architecture.md) §Prioritisation: `P1`; task 7 |
| `specs.md:Q2` | What are the US-9 overdue and escalation windows? | proposed answer | A27 (7/14/30/90 days); `human` confirms; tasks 35 |
| `specs.md:Q3` | Which notification channel (email or chat) does the pilot use? | proposed answer | A26: email over SMTP/SES; `human` confirms; task 33 |
| `specs.md:Q4` | What is the US-14 notification window? | proposed answer | A33: 30 minutes; `human` confirms; task 26 |
| `specs.md:Q5` | What credential does the responder use and how is it scoped; does a human or automation merge? | resolved | [`_docs/architecture.md`](architecture.md) §Responder agent (D2: human merges); task 28 |
| `specs.md:Assumptions bullet 1` | "Asset criticality" is a small fixed set; final values in Stage 2 | proposed answer | A16 final values; `human` at step 14; task 3 |
| `specs.md:Assumptions bullet 2` | Pilot repos plus OWASP Juice Shop give real findings; pilot list in a later stage | proposed answer | Task 22; `human` supplies repository URLs; A41 fallback |
| `specs.md:Assumptions bullet 3` | An asset owner has a name and contact email; ownerless only when both are unset; partial-owner notification decided in Stage 2 | proposed answer | A21: email-only owner notified, name-only held; tasks 9, 10 |
| `specs.md:withdrawn status ASSUMPTION` | `withdrawn` is an addition to the brief's three finding statuses (also stated in the status table and E4) | proposed answer | Tasks 8, 12; spec status table, E4 |

### `_docs/architecture.md`: open questions

| Key | Item | Status | Owner / where resolved |
|---|---|---|---|
| `architecture.md:Q1` | Spec Q1 (top tier) | resolved | §Prioritisation: `P1`; task 7 |
| `architecture.md:Q2` | Spec Q2 (US-9 windows) | proposed answer | A27; `human` confirms; task 35 |
| `architecture.md:Q3` | Spec Q3 (channel) | proposed answer | A26: email; `human` confirms; task 33 |
| `architecture.md:Q4` | Spec Q4 (US-14 window) | proposed answer | A33: 30 minutes; `human` confirms; task 26 |
| `architecture.md:Q5` | Spec Q5 (responder credential and merge) | resolved | §Responder agent; D2; task 28 |
| `architecture.md:Q6` | What exactly is the "Module 3/4 pattern" the human referred to? | open | Roadmap D1 proposes closing it with the Module 4 notes; `human` approves |
| `architecture.md:Q7` | Which domain name and TLS approach does the public URL use? | open | Roadmap D3; `human` decides before B5 |
| `architecture.md:Q8` | Confirm EPSS threshold T = 0.10 and the "exposed asset" definition | open | A17/A18; `human` at step 14; task 7 |
| `architecture.md:Q9` | Which LLM provider and model? | open | A23; `human` before task 30; risks R3 |
| `architecture.md:Q10` | An exploited vulnerability with no CVE can never reach P1/P2: accept, or add a rule? | open | `human` at step 14; task 7 |
| `architecture.md:Q11` | Does Juice Shop commit a supported lockfile? | open | A41 fallback; `human` confirms before task 22 |

### `_docs/architecture.md`: assumptions

All entries are listed under §Assumptions. A7, A12 and A14 were retired into spec rules in the second #43 spec commit; their numbers are not reused, so active IDs are A1-A6, A8-A11, A13, A15-A41.

| Key | Item | Status | Owner / where resolved |
|---|---|---|---|
| `architecture.md:A1` | Tiers: Postgres and n8n are Tier B; the MCP server is Tier A on the developer's machine | proposed answer | Engineer, tasks 1/15/32; step 14 |
| `architecture.md:A2` | n8n and Grafana use their default embedded stores on their own volumes | proposed answer | Engineer, task 15 |
| `architecture.md:A3` | Re-scans: daily n8n schedule after refresh plus a person's on-demand action; registration starts the first scan | proposed answer | Engineer, tasks 8/33 |
| `architecture.md:A4` | Scans and briefs run as background jobs in the backend with a job table and one worker | proposed answer | Engineer, task 10 |
| `architecture.md:A5` | Lockfiles are looked for at the repository root only | proposed answer | Engineer, task 4 |
| `architecture.md:A6` | One finding per package across several files; highest per-entry fixed version; `fixed` only when every entry is clear | proposed answer | Engineer, task 5 |
| `architecture.md:A8` | `uv.lock` and `package-lock.json` entry handling, including lockfileVersion 1 as a parse error | proposed answer | Engineer, task 4 |
| `architecture.md:A9` | `requirements.txt` handling for `-c`, `-e`, VCS/URL requirements and index options | proposed answer | Engineer, task 4 |
| `architecture.md:A10` | OSV's match is the candidate set; a range disagreement keeps the finding with a warning | proposed answer | Engineer, task 5 |
| `architecture.md:A11` | `last_affected`-only or open-ended intervals give no fixed version | proposed answer | Engineer, task 5 |
| `architecture.md:A13` | Enum values are stored and sent exactly as the spec writes them | proposed answer | Engineer, task 3 |
| `architecture.md:A15` | Alias-joined vulnerabilities merge; the earlier finding keeps its id and lifecycle | proposed answer | Engineer, task 5 |
| `architecture.md:A16` | Criticality values are final as `low`, `medium`, `high`, `critical` | proposed answer | `human` at step 14; task 3 |
| `architecture.md:A17` | Only criticality `critical` counts as "critical" in the tier rules | proposed answer | `human` at step 14; task 7 |
| `architecture.md:A18` | The EPSS threshold T is 0.10 | proposed answer | `human` at step 14; task 7 |
| `architecture.md:A19` | "Oldest finding" uses first detection time; the final tie-break is finding id | proposed answer | Engineer, task 7 |
| `architecture.md:A20` | Tiers cover `open` and `risk accepted`; the ranked list is `open` only; E8 escalation means a tier rise or becoming `KEV: listed` | proposed answer | Engineer, task 7 |
| `architecture.md:A21` | An email-only owner is notified; a name-only owner's notification is held | proposed answer | Engineer, task 10 |
| `architecture.md:A22` | The brief prompt includes the advisory summary, truncated to 500 characters | proposed answer | Engineer, task 30 |
| `architecture.md:A23` | LLM provider chosen with the human; 20 s timeout; brief cached per lifecycle, fixed version, prompt version and model | open | `human` chooses; Engineer task 30; R3 |
| `architecture.md:A24` | The brief output check rejects other version tokens and any URL in text fields | proposed answer | Engineer, task 30 |
| `architecture.md:A25` | n8n polls every 5 minutes; refresh 06:00 UTC; digest Monday 08:00 UTC | proposed answer | Engineer, tasks 33/35 |
| `architecture.md:A26` | Email over SMTP; a mail catcher in development and Amazon SES in AWS | proposed answer | `human` confirms spec Q3; task 33 |
| `architecture.md:A27` | US-9 windows P1 7, P2 14, P3 30, P4 90 days; reminders and escalation at due and weekly after | proposed answer | `human` confirms spec Q2; task 35 |
| `architecture.md:A28` | A missing security-lead contact shows on `/health` and a dashboard banner, and holds escalation and digest jobs | proposed answer | Engineer, task 35 |
| `architecture.md:A29` | The MCP server runs over stdio on the developer's machine; `get_asset` includes owner contact | proposed answer | Engineer, task 32 |
| `architecture.md:A30` | Dashboard authentication values (Argon2id, session lifetimes, lockout, CSRF header) and the owner-match rule | proposed answer | Engineer, task 9 |
| `architecture.md:A31` | URL defanging and `@` mention handling in emails and issue bodies | proposed answer | Engineer, tasks 34/35 |
| `architecture.md:A32` | The telemetry attribute allowlist | proposed answer | Engineer, task 23; R5 |
| `architecture.md:A33` | US-14 window 30 minutes, 1-minute evaluation; no-repeat was the human's 2026-10-20 decision | proposed answer | `human` confirms spec Q4; task 26 |
| `architecture.md:A34` | The responder runs as a container in the observability stack; branch `responder/<fingerprint>`; failed jobs retried each poll for up to 7 days | proposed answer | Engineer, task 28 |
| `architecture.md:A35` | The demo defect is switched by `VT_DEMO_DEFECT` and refused in production | proposed answer | Engineer, tasks 28/29; R8 |
| `architecture.md:A36` | One EC2 instance per environment running Compose; `t3.small`/`t3.medium`; Postgres in a container on EBS | proposed answer | `human` approves via D1; Engineer task 17 |
| `architecture.md:A37` | Budget amount set by the human; nightly stop of dev and observability; 7-day telemetry retention | proposed answer | `human` sets the budget amount; Engineer task 17 |
| `architecture.md:A38` | The pilot seed list lives in the repository as a data file, registered through the API | proposed answer | Engineer, task 22 |
| `architecture.md:A39` | Held notification jobs never fire the US-14 alert | proposed answer | Engineer, task 26 |
| `architecture.md:A40` | Instrumentation is a no-op without a Collector endpoint | proposed answer | Engineer, task 23 |
| `architecture.md:A41` | If Juice Shop has no supported lockfile, an open-source repository pinned to older versions replaces it | open | `human` confirms Q11; task 22 |

### `_docs/api.md`

| Key | Item | Status | Owner / where resolved |
|---|---|---|---|
| `api.md:A1 (#27)` | The n8n and MCP tokens are static opaque bearer tokens from environment variables and AWS Secrets Manager; no refresh or rotation in the MVP | proposed answer | `human` provisions the tokens; Engineer task 10 |
| `api.md:A1 (#50)` | The responder token follows A1: static opaque bearer from `RESPONDER_API_TOKEN` and Secrets Manager; no refresh or rotation | proposed answer | `human` provisions the token; Engineer task 10 |
| `api.md:VERIFY FastAPI 422 header` | FastAPI returns 422 for a missing required `Header()` on the pinned version; #24 maps it to 403 forbidden | VERIFY | Engineer, task 10/24 |
| `api.md:VERIFY query validation order` | FastAPI validates query parameters before the handler runs | VERIFY | Engineer, task 10 |
| `api.md:VERIFY GitHub naming` | GitHub owner and repository naming rules match the `repositoryUrl` pattern | VERIFY | Engineer, task 4 |
| `api.md:VERIFY OpenAPI 3.1 generation` | The pinned FastAPI version generates OpenAPI 3.1.0 | VERIFY | Engineer, task 14 |
| `api.md:VERIFY validator 3.1` | `uvx openapi-spec-validator` validates OpenAPI 3.1 | VERIFY | Engineer, task 14; `make openapi-validate` |
| `api.md:VERIFY n8n headers` | n8n's HTTP Request node sends a custom `traceparent` and bearer `Authorization` header | VERIFY | Engineer, tasks 23/34 |
| `api.md:VERIFY MCP SDK` | The Python MCP SDK and stdio transport work as assumed | VERIFY | Engineer, task 32 |
| `api.md:VERIFY traceparent` | The W3C Trace Context `traceparent` format matches the contract pattern | VERIFY | Engineer, task 23 |
| `api.md:VERIFY tracker issue numbers` | GitHub tracker issue numbers are positive integers | VERIFY | Engineer, task 34 |
| `api.md:VERIFY Secrets Manager injection` | AWS Secrets Manager injects `N8N_API_TOKEN`, `MCP_API_TOKEN` and `RESPONDER_API_TOKEN` at container start (lines 75, 76 and 340) | VERIFY | `human`/Engineer, tasks 10/17 |
| `api.md:VERIFY Loki scope` | The Grafana/Loki viewer token and its Loki access scope | VERIFY | Engineer, task 28 |

### `_docs/testing.md`

| Key | Item | Status | Owner / where resolved |
|---|---|---|---|
| `testing.md:T-A1` | Compose service `db`; test projects `vt-test`/`vt-e2e`; fixture asset/repo names; 120 s E2E timeout | proposed answer | Engineer, tasks 15/16; final names at Compose work |
| `testing.md:T-A2` | Fixture capture baseline is 2026-10-22; the recorder writes the actual date | proposed answer | Engineer, task 13 |
| `testing.md:T-A3` | The Grafana rule uses `noDataState: Alerting` and `execErrState: Alerting` | proposed answer | Engineer, task 26 |
| `testing.md:T-A4` | The US-13 metric carries the trace id as an OTel exemplar; otherwise a trace/log join by trace id | proposed answer | Engineer, tasks 23/25 |
| `testing.md:T-A5` | `make test` grows to include backend unit and SQLite integration and stays the single local command | proposed answer | Engineer, task 13 |
| `testing.md:T-A6` | Mailpit is the local mail catcher; adding it needs approval | proposed answer | `human` approves the dependency; tasks 16/33 |
| `testing.md:T-A7` | `pip-audit` and `npm audit --omit=dev` are the light-scan tools; adding them needs approval | proposed answer | `human` approves; Engineer task 20 |
| `testing.md:T-A8` | Production configuration is selected with `ENVIRONMENT=production`; the final name is a build detail | proposed answer | Engineer, task 28 |
| `testing.md:VERIFY OSV` | OSV endpoints, batch limit, fields and fixture shape | VERIFY | Engineer, task 5; architecture §External data sources |
| `testing.md:VERIFY KEV` | CISA KEV URL and fields | VERIFY | Engineer, task 6 |
| `testing.md:VERIFY EPSS` | FIRST EPSS URL and fields | VERIFY | Engineer, task 6 |
| `testing.md:VERIFY GitHub contents` | The GitHub contents API endpoint and fixture shape | VERIFY | Engineer, task 4 |
| `testing.md:VERIFY version libraries` | PEP 440 and SemVer library behaviour, including leading `v` and pre-releases | VERIFY | Engineer, tasks 4/5 |
| `testing.md:VERIFY OTel exemplar` | OTel Prometheus exemplar support | VERIFY | Engineer, task 25 |
| `testing.md:VERIFY Tempo-Loki link` | Tempo-to-Loki/Grafana data-source links | VERIFY | Engineer, task 24 |
| `testing.md:VERIFY Collector processor` | Collector processor names (`transform` / `attributes`) and `keep_keys` behaviour | VERIFY | Engineer, task 24 |
| `testing.md:VERIFY OTel batch/queue` | SDK batch buffering, Collector queue behaviour and self-metric names | VERIFY | Engineer, task 24 |
| `testing.md:VERIFY Grafana no-data` | Grafana no-data/error semantics and whether NoData keeps an instance active | VERIFY | Engineer, task 26 |
| `testing.md:VERIFY Grafana instances` | Grafana alert-instance and notification-policy behaviour and repeat-interval limit | VERIFY | Engineer, task 26 |
| `testing.md:VERIFY Markdown fence` | GitHub Markdown fence rules and whether mentions inside code blocks notify | VERIFY | Engineer, task 34 |
| `testing.md:VERIFY GitHub scope` | GitHub App/token scope and branch-protection details | VERIFY | `human`/Engineer, task 28 |
| `testing.md:VERIFY Loki viewer` | The Loki viewer token scope | VERIFY | Engineer, task 28 |
| `testing.md:VERIFY LLM` | LLM provider, endpoint, schema-constrained output, retention and pricing | VERIFY | `human`/Engineer, task 30; R3 |
| `testing.md:VERIFY audit tools` | `pip-audit` / `npm audit` licence and behaviour | VERIFY | `human`/Engineer, task 20 |

### `_docs/tasks.md`

| Key | Item | Status | Owner / where resolved |
|---|---|---|---|
| `tasks.md:ASSUMPTION` | `ASSUMPTION:` Task 15's Compose file and service names follow testing T-A1; task 17's AWS resource names and region follow architecture §Deployment and carry its `VERIFY:` tags | proposed answer | Engineer, tasks 15/17 |
| `tasks.md:VERIFY Juice Shop lockfile` | The exact Juice Shop lockfile in task 22 is confirmed by the human before the first registration | VERIFY | `human`, task 22 |

### `_docs/roadmap.md`: live decisions D1-D7

Rows 1-4 of the roadmap's decision table are resolved or withdrawn and are not live; D1-D7 are table rows 5-11.

| Key | Item | Status | Owner / next step |
|---|---|---|---|
| `roadmap.md:D1` | Close architecture Open question 6 with the Module 4 description (one EC2 instance per environment, Compose, ECR, CloudFormation) | open | `human` approves; architecture Q6 |
| `roadmap.md:D2` | Adopt the course image tag `YYYYMMDD-HHMMSS-shortsha` and add `service.version` (the tag) to the telemetry allowlist (A32) | open | `human` approves; architecture A32 edit, tasks 17/21 |
| `roadmap.md:D3` | Domain name and TLS approach for the public URL | open | `human`; architecture Q7, B5 |
| `roadmap.md:D4` | Add to US-15 that a false positive or test alert makes the responder explain and change nothing | open | `human`; `specs.md` is protected; C6 |
| `roadmap.md:D5` | Fallback if AWS is not available in time (kind cluster or local Compose demo) | open | `human` names the fallback date at B4 |
| `roadmap.md:D6` | Move n8n tasks 33 and 34 ahead of task 25 and add task 34 to tasks 25 and 28's `Depends on:` | open | `human`/PM; tasks.md dependency edit, C1/C3 |
| `roadmap.md:D7` | At filing, split task 21 (dev vs prod) and task 24 (Compose vs `vt-observability`) | open | `human`/PM at step 12 filing; B5/C3 |

### `_docs/project-brief.md`

No labelled items: 0 open questions, 0 `ASSUMPTION:` and 0 `VERIFY:` (read-only `.scratch/` extraction). It is the fixed input, not a source of open items.

### `_docs/plan-summary.md` (self-assumptions)

| Key | Item | Status | Owner / where resolved |
|---|---|---|---|
| `plan-summary.md:P-A1` | `ASSUMPTION:` The earliest milestone in a rubric row is the earliest milestone among the `tasks.md` tasks that §Coverage summary assigns to that criterion; the Application/task 15 caveat does not move its milestone | proposed answer | PM/orchestrator at step 14 |
| `plan-summary.md:P-A2` | `ASSUMPTION:` `_docs/specs.md`'s `VERIFY:` markers are external-detail checks, outside the Stage 1 register scope; they are tracked in architecture §External data sources and risk R4 | proposed answer | PM/orchestrator at step 14 |

## Completeness check

Counts come from the read-only label-only `.scratch/` extraction (`count_labels.py`), which matches only the literal tags `ASSUMPTION:` and `VERIFY:`. Prose, headings, `make verify` and the unlabelled word "assumption" are not counted. An unexplained difference would be a FAIL; every difference below is explained, and the exact line locations follow the table.

| Source | Open questions / decisions | `ASSUMPTION:` labels (occurrences / lines) | `VERIFY:` labels (occurrences / lines) | Captured | Difference and explanation |
|---|---|---|---|---|---|
| `_docs/project-brief.md` | 0 | 0 / 0 | 0 / 0 | 0 | No labelled items |
| `_docs/specs.md` | 5 | 6 / 6 | 14 / 13 (out of scope) | 9 | The 6 assumption labels are 5 distinct meanings: line 152 is the US-9 windows assumption and is recorded in `specs.md:Q2`; lines 256 and 345 are the same `withdrawn` addition (one row); lines 371, 373 and 375 are the three §Assumptions rows. Spec `VERIFY:` labels are external-detail checks outside the Stage 1 register scope (P-A2) |
| `_docs/architecture.md` | 11 | 38 / 29 | 56 / 47 (out of scope) | 49 | The 38 labelled tags are exactly A1-A6, A8-A11, A13 and A15-A41; A7/A12/A14 are retired and not reused, so there is no assumption difference. `VERIFY:` labels are tracked per §External data sources and risk R4, not as separate register rows |
| `_docs/api.md` | 0 | 2 / 2 | 13 / 12 | 13 | Both A1 labels (#27 at line 75, #50 at line 76) are separate rows. The 13 VERIFY occurrences are 11 distinct items: line 332 carries two labels (OpenAPI generation and the validator), and the Secrets Manager item occurs on lines 75, 76 and 340 and is one row listing all three |
| `_docs/testing.md` | 0 | 15 / 15 (14 tagged; 8 distinct T-A) | 19 / 19 | 24 | Line 5 is the conventions definition, so the 14 tagged occurrences are the 8 T-A rows. The 19 VERIFY labels are 18 item mentions (line 5 is a definition) and 16 distinct rows: line 224 supplies the exemplar and Tempo-Loki rows, and the table at lines 378-385 repeats items already named inline |
| `_docs/tasks.md` | 0 | 2 / 2 | 2 / 1 | 2 | Lines 95 and 267 are one assumption row (task 15/17 follow T-A1 and architecture §Deployment). Line 267 carries two VERIFY labels: one is a cross-reference to architecture's existing tags, the other is the Juice Shop lockfile row |
| `_docs/roadmap.md` | 7 live decisions (D1-D7) | 0 / 0 | 3 / 3 (out of scope) | 7 | The decision table has 11 rows; rows 1-4 are resolved/withdrawn and not live, so 7 D-rows are captured. The 3 VERIFY labels (65, 66, 114) are step/check-in external details outside the decision register; the `(ASSUMPTION)` at line 207 is prose, not a label |
| `_docs/plan-summary.md` | 0 | 2 / 2 (self) | 0 / 0 | 2 | P-A1 and P-A2 are labelled `ASSUMPTION:` and added here |

Register total: 9 + 49 + 13 + 24 + 2 + 7 + 2 = **106 entries** (104 from Stages 1-5 plus 2 self-assumptions).

Label locations (1-based line numbers, read at `1edc468`):

- `_docs/specs.md` — `ASSUMPTION:` 152, 256, 345, 371, 373, 375. `VERIFY:` 30, 33, 72, 84, 133, 138, 256, 318, 326, 345, 350, 351, 352 (14 occurrences on 13 lines; line 345 carries two).
- `_docs/architecture.md` — `ASSUMPTION:` 25, 29, 44, 45, 51, 53, 72, 83, 92, 115, 132, 179, 196, 223, 227, 242, 250, 269, 271, 288, 301, 336, 353, 356, 365, 379, 393, 407, 433. `VERIFY:` 5, 14, 29, 49, 59, 60, 61, 62, 63, 80, 81, 86, 87, 94, 104, 240, 242, 267, 269, 277, 278, 279, 280, 281, 282, 283, 288, 301, 317, 320, 332, 334, 348, 352, 355, 360, 371, 383, 393, 398, 403, 404, 405, 412, 415, 417, 433 (56 occurrences; lines 29, 80, 81, 87, 277, 332, 348, 355 and 360 carry two each).
- `_docs/api.md` — `ASSUMPTION:` 75, 76. `VERIFY:` 47, 72, 75, 76, 158, 205, 332, 336, 337, 338, 339, 340 (13 occurrences; line 332 carries two).
- `_docs/testing.md` — `ASSUMPTION:` 5, 77, 91, 139, 222, 250, 363, 370, 371, 372, 373, 374, 375, 376, 377. `VERIFY:` 5, 166, 218, 224, 226, 228, 238, 242, 256, 258, 262, 378, 379, 380, 381, 382, 383, 384, 385.
- `_docs/tasks.md` — `ASSUMPTION:` 95, 267. `VERIFY:` 267 (two labels on the line).
- `_docs/roadmap.md` — `ASSUMPTION:` none. `VERIFY:` 65, 66, 114.
- `_docs/project-brief.md` — none.

## Stage 6 checklist

| Item | Result | How checked |
|---|---|---|
| All 12 criteria appear | PASS | [`_docs/rubric.md`](rubric.md) has 12 `######` criterion headings; the map has exactly 12 data rows in the same order with the same names (`.scratch/check_map.py`) |
| Max points total 24 and the pass mark is 10 | PASS | [`_docs/rubric.md`](rubric.md) line 4 and the per-criterion headings; the map's Max column is 2+2+2+2+2+2+2+2+3+2+1+2 = 24, and the total line states 24/10 |
| Nothing is unmapped | PASS | Every map row has at least one `task N` and at least one resolving document link; the Gaps table is empty. The Application/task 15 difference is recorded as D1, and the row is still covered by tasks 1, 3-12 and 14 |
| Every task number exists | PASS | `.scratch/check_map.py` matched every `task N` to a `## N.` heading in [`_docs/tasks.md`](tasks.md) and found no number outside 1-36 |
| Every risk has a mitigation | PASS | Top risks has 9 rows (more than 8); every row has a non-empty mitigation, owner and residual risk. Human-only actions are labelled `human` |
| All open questions and assumptions are collected | PASS | Corrected label-only recount: 6 specs assumption labels (5 meanings; `specs.md:Q2` covers line 152), 38 architecture A tags, 2 api A1 entries, 14 tagged testing T-A occurrences (8 items), 2 tasks labels, 0 roadmap labels, plus 2 self-assumptions = 106 register entries; every difference is explained and the locations are listed above |
| Links resolve | PASS | `.scratch/check_links.py` checked every relative Markdown link in this file and the new README line; all resolve |
| File limit | PASS | `git diff --name-only 1edc468` lists only `_docs/plan-summary.md` and `README.md`; `git diff --stat 1edc468` is 2 files with 0 deletions |

## Gaps

None. Every criterion has at least one `_docs/tasks.md` task and at least one existing repository document. The Application/task 15 difference is a source discrepancy (D1), not an unmapped criterion.
