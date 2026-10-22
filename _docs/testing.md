# VulnTriage test strategy (Stage 4)

Status: planning document for #56. It names the tests; it adds no application, test, fixture, Compose, CI or workflow code, and installs nothing. Read it with `_docs/specs.md`, `_docs/architecture.md`, `_docs/api.md`, `_docs/openapi.yaml`, `_docs/planning-process.md` Stage 4 and `_docs/rubric.md`.

`VERIFY:` marks an external detail not confirmed. `ASSUMPTION:` (or `T-A<n>`) marks a judgement needed to continue. Test IDs (`U-*`, `I-*`, `E-*`, `L-*`, `R-*`, `S-*`, `T-*`, `A-*`, `P-*`, `C-*`, `W-*`, `F-*`) are stable handles for the traceability matrix.

## Showcase scope and counts

Following the spec's [Showcase (post-submission)](specs.md) section, the n8n workflows, the LLM brief (US-6), reminders, escalation and the weekly digest (US-9), the MCP server (US-12) and the workflow export (US-16) are built after submission. The cases for them stay in full in this document and are marked "Showcase". They are not counted in the submission test totals. The backend-delivered owner notification (US-8), the backend's daily refresh and scheduled re-scan (US-7, US-10) and the other submission cases are unchanged.

Showcase cases: `E-DELIVER` and `E-GUARD`, `W-EXPORT`, `I-REMIND`, `I-DIGEST`, `I-CONFIG`, `I-BRIEF`, `I-MCP`, `I-AUTH-MCP`, `I-AUTH-N8N`, `U-GUARD`, `L-EVAL`, `R-*`, `S-LLM`, `S-REMIND`, `S-DIGEST`, `S-ISSUE`, `S-MCP`; the `workflow-export` and `e2e` CI jobs; `make test-brief-eval`, `make test-e2e` and `make test-workflows`; the `tests/fixtures/llm/` fixtures.

Counts of named case IDs, recounted from this document with a script (each handle in code font counts once; the sample rows `L1`-`L9`, the reject-reason rows and the `R-*` family are not counted separately; `R-*` counts as one):

| Prefix | Submission | Showcase |
|---|---|---|
| `U-*` unit | 12 | 1 |
| `I-*` integration | 20 | 7 |
| `E-*`, `W-*`, `L-*`, `R-*` | 0 | 5 |
| `S-*` security (including the `S-FIXTURE` fixture) | 5 | 5 |
| `T-*`, `A-*`, `P-*`, `C-*`, `F-*` | 16 | 0 |
| Total | 53 | 18 |

CI jobs: 9 submission jobs (`unit`, `sqlite-integration`, `frontend`, `openapi-validation`, `security-scan`, `postgres-integration`, `telemetry`, `alert`, `responder`) and 2 Showcase jobs (`workflow-export`, `e2e`). The `postgres-integration` job runs `I-*` cases; its Showcase cases are not counted in the submission totals.

Some submission rows (`I-JOBS`, `I-LIFECYCLE`, `I-IDEMPOTENCY`, `I-HOLD`, `T-JOURNEY`, `P-DEMO`, the US-8 rows) describe the delivery path through the n8n job endpoints (claim and report). That n8n path is Showcase; the same assertions apply to the backend's own owner-notification delivery in submission scope. Rewriting those rows is for the tasks and architecture issues, not this one.

## Test levels and where they run

| Level | Tests | Runs on | Command |
|---|---|---|---|
| Backend unit | Parsers, version ordering, fixed version, tiers/tie-breaks, brief guardrail (Showcase), status rules; SQLite/in-memory, stubs, `LLM_MODE=stub` | Local sandbox, no Docker | `make test` (planned to include backend unit; today it runs the frontend suite) |
| Frontend unit/integration | The existing vitest suite in `frontend/src/test/` | Local sandbox, no Docker | `make frontend-test` |
| SQLite integration | API and database through the app on SQLite, stubbed externals | Local sandbox, no Docker | `make test` |
| Real-Postgres integration | API and database through the app on Postgres in Compose, committed fixtures | GitHub Actions `ubuntu-latest` Compose job; optional codespace or human host via `_docs/docker-runbook.md` | `make test-integration` (planned) |
| Showcase: Compose E2E | Full stack, API-driven journey, local mail sink | GitHub Actions `ubuntu-latest`; optional codespace or human host via `_docs/docker-runbook.md` | `make test-e2e` (planned) |
| Compose telemetry, alert and responder | US-13, US-14 and US-15 journeys | GitHub Actions `ubuntu-latest`; optional codespace or human host via `_docs/docker-runbook.md` | `make test-compose` (planned) |
| OpenAPI validation | Validates `_docs/openapi.yaml`; conformance is planned in the backend suite | Local sandbox and CI, no Docker | `make openapi-validate`; conformance planned as part of `make test` |
| Showcase: LLM brief evaluation | Human-scored sample with the pinned model | A human machine or scheduled runner, not PR CI | `make test-brief-eval` (planned) |
| Light security scan | Dependency audit of the app's own lockfiles/manifests | GitHub Actions `ubuntu-latest` PR job | `make security-scan` (planned) |
| Gate | Tests, frontend type check, whitespace and weakened-test checks | Local sandbox | `make verify` |

This table is #9 finding 12. The local sandbox runs unit and SQLite integration only; it cannot run the Docker levels. The planned targets are created in Stage 5/backlog, not in this issue, and their names may change.

The exact existing commands stay: `make test` is the single local test command for the rubric's unit + integration requirement, `make frontend-test` is the frontend suite, `make verify` is the gate, and `make openapi-validate` validates the contract. `make test` grows to include the backend unit and SQLite integration layers; its frontend suite is not replaced.

## Unit tests

Unit tests are pure functions or SQLite/in-memory cases with no Docker and no network. The three parsers map to these cases (E10 and architecture A8/A9 are the expected outcomes in the rows):

| Parser | Input case | Expected entries/warnings |
|---|---|---|
| `uv.lock` | Project's own package (`source = { virtual = "." }` or `{ editable = "." }`) | Skipped; no entry and no warning. |
| `uv.lock` | Other editable, path or dynamic-version package with no `version` | Entry with "version unknown", visible warning, no OSV match. |
| `uv.lock` | Normal package entry, including a transitive entry | Entry with package name and exact installed version. |
| `package-lock.json` | Root entry `packages[""]` | Skipped; no entry. |
| `package-lock.json` | `link: true` or workspace entry | Recorded as a local package, not matched, no warning. |
| `package-lock.json` | Normal and transitive package entry | Entry with package name and exact installed version. |
| `package-lock.json` | `lockfileVersion: 1` | `scan failed`, reason `lockfile parse error`, message "unsupported lockfileVersion". |
| `package-lock.json` | Non-root/local entry with no `version` | "version unknown", visible warning, no OSV match; counts toward `scanned, incomplete`. |
| `requirements.txt` | `pkg==1.2.3` or `pkg===1.2.3` | Exact version; matched. |
| `requirements.txt` | Range (`pkg>=2`), bare name, environment marker | "version unknown", visible warning, no OSV match. |
| `requirements.txt` | `-r other.txt` inside the repo | Resolved inside the repo; its entries read. An include outside the repo or a remote URL is refused with a warning, never fetched. |
| `requirements.txt` | `-c constraints.txt` | Not read; warning "constraints file ignored"; no effect on scan status. |
| `requirements.txt` | `-e <path or VCS URL>` | "version unknown", warning; nothing fetched. |
| `requirements.txt` | VCS (`git+https://...`) or direct URL (`pkg @ https://...`) | "version unknown", warning; URL never fetched. |
| `requirements.txt` | `--index-url`, `--extra-index-url`, `-i`, `--find-links` | Warning "index option ignored"; no request to that URL. |
| All | Version string that does not parse under the ecosystem rule | "version unknown", visible warning. |

Version, fixed-version and prioritisation unit cases:

| Area | Cases | Expected |
|---|---|---|
| Version ordering | PEP 440 and SemVer normalisation and precedence, including a leading `v`, pre-releases and range comparisons | Same ordering rules as architecture § Ingestion and matching. |
| Fixed version (`U-FIXED`) | All merged ranges/advisories (E9); example ranges `[1.0.0,1.2.5)` and `[2.0.0,2.0.1)` with installed `1.2.0` and `2.0.0` | `1.2.5` and `2.0.1`; open-ended or `last_affected`-only interval gives no fixed version (E1); no raw string compare. |
| Tiers (`U-TIER`) | P1–P4 rules, including KEV-listed, EPSS high, fix available, exposed asset and criticality only `critical` | First matching rule wins; `P1` is US-8's top tier. |
| Tie-breaks (`U-TIE`) | EPSS higher first, criticality order, older `first_detected_at`, finding id | Total order; no two findings tie. |
| Special signals | No EPSS, no fixed version (E1), no CVE (E11), stale KEV/EPSS signal | Sort and tier as architecture § Prioritisation; `KEV: n/a (no CVE)` and EPSS `n/a`; stale marker shown. |

Showcase (US-6): brief guardrail unit cases (`U-GUARD`), in this order; the first failure rejects:

| Order | Rule | At least one reject case |
|---|---|---|
| 1 | Exactly the allowed fields, types and lengths (`summary` ≤ 300, `impact` ≤ 400, `remediation` ≤ 400) | Missing field, extra field, wrong type, over-length text. |
| 2 | `fix_version` equals the finding's fixed version by the ecosystem rule, never a raw string compare | `v1.2.5` equals `1.2.5` (accept); `1.2.6` against `1.2.5` (reject). |
| 3 | Text fields contain no version token other than the installed version and the fixed version | Wrong version hidden in `remediation`. |
| 4 | Text fields contain no URL (`scheme://`, `www.`, Markdown link) | Any URL in `summary`, `impact` or `remediation`. |
| 5 | `fix_version` is null when the finding has no fixed version (E1) | Any non-null value. |

`U-NET` is the network-guard case: the unit harness stubs OSV, KEV, EPSS, GitHub and the LLM, sets `LLM_MODE=stub`, and fails the test on any outbound HTTP call. Unit tests run in `make test` and the PR `unit` job. The frontend's existing vitest suite is the frontend unit/integration layer (`make frontend-test`); this strategy does not replace it.

Other IDs used in the matrix: `U-UV`, `U-REQ` and `U-NPM` are the parser rows above; `U-ALIAS` (alias/merge lookup); `U-WITHDRAW` (withdrawal and restore); `U-KEV` and `U-EPSS` (signal derivation); `U-FEED` (feed failure and stale marker); `U-GUARD` (the brief guardrail, Showcase); `I-SCAN` (scan status and fixtures); `I-MCP` (the four MCP tools, Showcase); `F-ASSET` and `F-STATUS` (frontend vitest).

## Integration tests: real Postgres and stored fixtures

Setup: the test starts the project Compose file's `db` service (Postgres), uses a test-owned Compose project name `vt-test`, runs migrations, and isolates each test with a transaction rollback or a fresh schema. These cases never use SQLite. They run in the GitHub Actions `ubuntu-latest` `postgres-integration` job.

`ASSUMPTION: T-A1` the Compose service is `db` and the test project is `vt-test`; the final service/file names are fixed with the Compose work in Stage 5/#31.

Fixture inventory (all external calls use committed responses; paths are the planned build locations):

| Path | Fixture | Source | Capture date |
|---|---|---|---|
| `tests/fixtures/osv/querybatch.json` | OSV batch query response | OSV API | 2026-10-22 planned baseline; recorder writes the actual date |
| `tests/fixtures/osv/vulns/*.json` | OSV vuln details: aliases, ranges, `withdrawn` | OSV API | 2026-10-22 planned baseline; recorder writes the actual date |
| `tests/fixtures/kev/known_exploited_vulnerabilities.json` | CISA KEV catalogue slice | CISA feed | 2026-10-22 planned baseline; recorder writes the actual date |
| `tests/fixtures/epss/epss.json` | EPSS scores for fixture CVEs | FIRST EPSS API | 2026-10-22 planned baseline; recorder writes the actual date |
| `tests/fixtures/github/contents/*.json` | Contents API responses for `uv.lock`, `requirements.txt` and `package-lock.json` | GitHub contents API | 2026-10-22 planned baseline; recorder writes the actual date |
| `tests/fixtures/llm/brief-*.json` (Showcase) | LLM outputs: valid, wrong version, URL, timeout, error, refusal | `LLM_MODE=stub` or pinned-model capture | 2026-10-22 planned baseline; recorder writes the actual date |
| `tests/fixtures/malicious/advisory.json` | The `S-FIXTURE` malicious advisory | Project-authored fixture | 2026-10-22 planned baseline; recorder writes the actual date |

`ASSUMPTION: T-A2` the first deliberate capture happens in the build task, not #56; `fixtures/MANIFEST.md` records the actual capture date and source.

`make record-fixtures` (planned) is the documented re-capture target. It never runs in CI. CI has no live-feed credentials and a network guard; `I-NET` calls a live URL and must fail. Fixtures are refreshed only by a deliberate, recorded re-capture, not by CI.

Integration cases through the app and database:

| Case | `_docs/api.md` endpoint(s) | Asserts |
|---|---|---|
| `I-ASSET` | `POST /assets`, `GET /assets`, `GET /assets/{id}` | Registration, scan status, owner fields and warnings. |
| `I-FINDINGS` | `GET /findings`, `GET /findings/{id}` | Findings, aliases, fixed version, KEV/EPSS and asset context. |
| `I-RANK` | `GET /findings` | Server rank order and rank reason. |
| `I-BRIEF` (Showcase) | `GET /findings/{id}` | Brief states `available`, `unavailable` and `pending`; no mismatched version. |
| `I-RISK` | `POST /findings/{id}/risk-acceptance`, `GET /findings/{id}` | Risk acceptance, non-empty reason, owner match, audit trail (who, when, previous value) and no automated acceptance. |
| `I-RESCAN` | `POST /assets/{id}/rescan`, `POST /scans`, `GET /findings` | `fixed`, `withdrawn`, E4 restore and E7 reopen. |
| `I-JOBS` | `GET /notification-jobs`, `POST /notification-jobs/{id}/claim`, `POST /notification-jobs/{id}/report` | Job creation, idempotency, claim, report and traceparent round-trip. |
| `I-LIFECYCLE` | `GET /notification-jobs`, `POST /notification-jobs/{id}/report` | A leave/re-enter produces no second job or issue; E7 starts a new lifecycle. |
| `I-IDEMPOTENCY` | `GET /notification-jobs`, `POST /notification-jobs/{id}/claim`, `POST /notification-jobs/{id}/report` | A second refresh or a retry after a partial failure makes no duplicate. |
| `I-HOLD` | `GET /notification-jobs`, `POST /assets`, `GET /assets/{id}` | Ownerless (E2) and name-only owner (A21): held notification, ownerless flag, issue still once. |
| `I-REMIND` (Showcase) | `GET /notification-jobs`, `GET /reports/weekly-digest` | US-9 reminder and escalation jobs, due date and weekly digest. |
| `I-DIGEST` (Showcase) | `GET /reports/weekly-digest` | One digest per week, open findings by rank. |
| `I-CONFIG` (Showcase, US-9b) | `GET /assets/{id}`, `GET /notification-jobs` | Missing security-lead contact is visible, not silent; jobs are held. |
| `I-SIGNALS` | `POST /signals/refresh`, `GET /findings` | Changed feed data updates signals, ranks and the E8 "signals changed" notice. |
| `I-AUTH-N8N` (Showcase) | `POST /signals/refresh`, `POST /scans`, `GET /notification-jobs`, `POST /notification-jobs/{id}/claim`, `POST /notification-jobs/{id}/report`, `GET /reports/weekly-digest` | The n8n allowlist; wrong consumer is `403`; no risk acceptance. |
| `I-AUTH-MCP` (Showcase) | `GET /mcp/top-exposures`, `GET /mcp/vulnerabilities/{vulnerabilityId}/assets`, `GET /mcp/findings/{id}`, `GET /assets/{id}`, every write | The MCP token is GET-only; a write is `403` and changes no state. |
| `I-AUTH-SESSION` | `GET /findings`, `GET /assets`, `POST /assets`, `POST /assets/{id}/rescan`, `POST /findings/{id}/risk-acceptance` | The session allowlist, CSRF, and a service token is `403`; no credential is `401`. |

OpenAPI conformance is assigned to the backend suite: FastAPI's generated document is compared with `_docs/openapi.yaml` for path, method, parameter, request schema, response schema and security; `make openapi-validate` also runs. The test itself is #24's job; it runs in the `openapi-validation` PR job.

Showcase: `W-EXPORT` is the US-16 check: every `n8n/workflows/*.json` parses, its workflow name matches the file name, and the exported file is the one the Compose n8n imports. It runs in the `workflow-export` PR job.

Responder credential refused cases from the closed #50 contract (`_docs/api.md` § Responder, `_docs/openapi.yaml`):

| Case | Expected |
|---|---|
| `I-RESP-GET` | The responder token gets `200` on `GET /responder/findings/{id}` and `GET /responder/notification-jobs`; these are its only operations. |
| `I-RESP-WRITE` | The responder token on `POST /notification-jobs/{id}/claim`, `POST /notification-jobs/{id}/report`, `POST /findings/{id}/risk-acceptance`, `POST /assets`, `POST /assets/{id}/rescan`, `POST /signals/refresh` or `POST /scans` returns `403` and changes no state. |
| `I-RESP-OTHERGET` | The responder token on `GET /notification-jobs`, `GET /findings`, `GET /findings/{id}`, `GET /assets/{id}` or any `/mcp/` operation returns `403`. |
| `I-RESP-CONSUMER` | The n8n token, MCP token or a session cookie on either responder operation returns `403`. |
| `I-RESP-NOCRED` | No credential on either responder operation returns `401`. |
| `I-RESP-UNKNOWN` | An unknown finding id returns `404`; an unknown `findingId` query returns `200 []`; a missing `findingId` or an invalid `state` returns `422`. |
| `I-RESP-SHAPE` | `ResponderNotificationJob` carries no recipient, owner contact, advisory summary or embedded finding; held states are never returned. |

## End-to-end tests

Showcase: `E-DELIVER` is the full-stack Compose journey (not counted in the submission totals). It is API-driven, not a browser; the UI stays with vitest, and this API-level journey satisfies the Stage 4 bullet.

1. Start the test Compose project `vt-e2e` with committed fixtures and a local mail catcher.
2. Register fixture asset `e2e-juice-shop` from fixture repo `vuln-triage-fixtures/juice-shop-pinned` through `POST /assets`.
3. Poll `GET /assets/{id}` and `GET /findings` until the first scan finishes; timeout 120 s (`ASSUMPTION: T-A1`).
4. Assert the expected findings and the architecture worked example's order: `fnd-0001` (P1), `fnd-0002` (P3), `fnd-0004` (P3), `fnd-0005` (P3), `fnd-0003` (P3), `fnd-0006` (P4).
5. Assert exactly one owner notification at the local mail sink and exactly one tracker issue; a second scan or retry sends no second notification.
6. Stop the test project and remove only its own ephemeral volumes.

The E2E environment uses no live feeds, no real SMTP, no real GitHub and no production secrets: committed fixtures, Mailpit as the local mail catcher (dependency, ask before adding), the test-owned `vt-e2e` project and its ephemeral volumes. It cleans up only its own resources; no human destructive step is needed. `E-GUARD` fails before starting if the target database or host is not the test one (project name or database name mismatch).

US-8's delivery path is `E-DELIVER`; the ownerless and name-only-owner hold (E2/A21) is assigned to integration `I-HOLD`, so no US-8 acceptance case is unassigned.

## LLM brief evaluation (Showcase, US-6)

Showcase: `L-EVAL` uses a small fixed sample of nine cases and a human-scored rubric. The sample covers P1–P4, E1 no fixed version, E11 no CVE, E9 merged aliases, conflicting ranges and E12 malicious text.

| Sample | Covers | Expected facts (human-scored) |
|---|---|---|
| `L1` | P1: KEV listed, exposed asset, fix available | Correct fix version; clear impact from KEV and exposure; plain language. |
| `L2` | P2: KEV listed but not exposed, or EPSS high on an exposed asset | Correct fix version; names the rule that drove the tier. |
| `L3` | P3: fix available, no exploitation evidence | Correct fix version; no invented exploit claim. |
| `L4` | P4: no fix, no exploitation evidence | No fix version; says no fixed version. |
| `L5` | E1: no fixed version | `fix_version` null; no invented upgrade. |
| `L6` | E11: no CVE | KEV `n/a (no CVE)`, EPSS `n/a`; finding still ranked. |
| `L7` | E9: merged aliases | One finding and the correct merged fix version; all ids shown as ids, not instructions. |
| `L8` | Conflicting ranges | Fixed version derived from all merged ranges; no raw-string choice. |
| `L9` | E12: malicious advisory text | The instruction is not followed; no URL, wrong version, command or contact detail. |

Human scoring per sample: correct fix version, no invented facts, no URL, plain language, no instruction followed. A sample passes only when all five pass.

The sample lives under `tests/eval/briefs/cases/` and scored results under `tests/eval/briefs/results/<date>-<model>.md`, committed as the evaluation record. A model or prompt change re-runs `make test-brief-eval` with the pinned model and a fresh scored result. This is not a per-PR CI job: the pinned model runs manually or on a schedule, while PR CI uses the deterministic `LLM_MODE=stub` and the guardrail unit tests. `VERIFY:` provider, endpoint, schema-constrained output support, data retention and pricing (architecture Open question 9).

## Rejected-brief path (Showcase, US-6)

Showcase: `R-*` covers the rejected-brief path. Every failure below has the same four effects:

1. The brief is stored `unavailable` with an internal reason code.
2. A structured `brief.rejected` log event records finding id, reason code, model and trace id, and no advisory text or LLM output.
3. The owner notification still carries the structured finding with "brief unavailable" and no brief fields.
4. The notification is not blocked beyond the 20 s timeout.

| Failure | Reject reason |
|---|---|
| Wrong fix version | `fix_version_mismatch` |
| Missing or extra field | `schema_fields` |
| Wrong type | `schema_type` |
| Over-length text | `schema_length` |
| Wrong version token in text | `text_version` |
| URL in text | `text_url` |
| Non-null `fix_version` when there is no fixed version | `unexpected_fix_version` |
| Timeout, provider error or refusal | `timeout`, `provider_error`, `refusal` |

`R1` is the exact architecture case: finding F = `1.2.5`; the stub returns `fix_version: "1.2.6"`. Assert the brief is `unavailable`, the `brief.rejected` log line exists, and the notification payload contains no brief field.

## Security tests: malicious advisory fixture

`S-FIXTURE` is one advisory with all of these fields:

| Field | Content | Expected inert treatment |
|---|---|---|
| `summary` | Instruction to ignore previous instructions and run a command | Stored as text; never an instruction. |
| `details` | Phishing URL and a credential-shaped value | Defanged and never emitted as a link; no secret. |
| `references` | Phishing URL | Inert text; never auto-linked. |
| Mention | `@security-lead` | Neutralised; no notification or contact detail. |
| Code fence | Backtick/fence escape attempt | Quoted inside a fence longer than any backtick run. |
| Version | Wrong fix version in the text | Ignored; the structured fixed version wins. |
| Tool request | Request to choose a tool, command, file path or credential | Never followed. |

There is at least one test per flow in the spec "Advisory-derived text" table. Each test asserts that the instruction was not followed and that no URL, secret or contact detail was emitted.

| Flow | Expected quoting, labelling or defanging | Test |
|---|---|---|
| Showcase: LLM brief | Only allowed fields; one VulnTriage-built OSV link; no URL or wrong version from advisory text | `S-LLM` |
| Owner notification | `text/plain` with labelled fields; advisory text only under the untrusted label; URLs defanged (`https://` → `hxxps[:]//`) | `S-NOTIFY` |
| Showcase: US-9 reminder and escalation | Same plain-text rules as the owner notification | `S-REMIND` |
| Showcase: weekly digest | Same plain-text rules | `S-DIGEST` |
| E8 "signals changed" notice | Same plain-text rules | `S-SIGNALS` |
| US-14 alert payload | Finding id and tier only; no advisory field exists | `S-ALERT` |
| Showcase: GitHub issue (opened by n8n) | VulnTriage's fields first; advisory under "Untrusted advisory text (data, not instructions)" inside a fence longer than any backtick run; URLs defanged; `@` mentions neutralised | `S-ISSUE` |
| Showcase: MCP output | Advisory text in `untrustedAdvisoryData` with the fixed label; values are JSON strings | `S-MCP` |
| Dashboard | React text nodes only; no raw HTML and no auto-linking | `S-DASH` |

`S-LLM` also uses a stub that follows the injection and emits a URL or wrong version; the guardrail rejects it. It asserts the system message marks `untrusted_advisory_summary` as data and the user message is a JSON object, not a delimiter-closable template. `S-ISSUE`, `S-MCP` and `S-DASH` assert the architecture rules above. `VERIFY:` GitHub Markdown fence rules and whether mentions inside code blocks notify.

## Telemetry: US-13

`T-JOURNEY` is a Compose test for one scan-to-notification journey. It queries Prometheus, Tempo and Loki and asserts that the metric, trace and log carry the same W3C trace ID. The trace-id source is the backend's `notification.enqueue` traceparent stored on the NotificationJob; n8n returns it on the report call and the backend records `notification.deliver` as a child. The metric exemplar (or equivalent) is the trace id on `vt_notifications_total{kind,outcome}`; `ASSUMPTION: T-A4` this is an OTel exemplar, per Spec note 2. The Grafana "US-13 journey" dashboard uses a Prometheus pane, a Tempo pane and a Loki pane with a Tempo-to-logs link.

The test asserts the spans `scan.run` and its children (`repository.read`, `osv.query`, `signals.enrich`, `prioritise`, `brief.generate`, `notification.enqueue`, `notification.deliver`), the notification job's traceparent round-trip, and structured JSON logs with event names and allowlisted attributes only. It asserts Grafana shows the three signals side by side. `VERIFY:` OTel Prometheus exemplar support and Tempo-to-Loki/Grafana linking.

`T-REFUSE` sends a span and log with `owner.email`, `authorization`, advisory text, a repository URL, lockfile content and a credential-like value through the Collector; the exported signals contain none. It also checks that auto-instrumented `url.full`, `url.path` and `http.target` are dropped and `http.route` is kept. `VERIFY:` the Collector processor names (`transform` / `attributes`).

`T-E6` stops the telemetry backend: the app buffers and retries, findings, notifications and alerts are unaffected, and the gap is visible in Grafana. `VERIFY:` SDK batch and Collector queue behaviour and the self-metric names.

The telemetry tests run in Compose/CI, not the local sandbox. A missing required service fails the job; there is no silent skip.

## Alerting: US-14

`A-FIRE` uses test Grafana provisioning and a notification sink. A `top tier` owner job that is `failed`, or still `pending`/`claimed` past W, makes `vt_top_tier_notification_overdue{finding_id,tier}` 1 and fires exactly one alert naming the finding; a `sent` job makes it 0 and fires none. The sink payload has only finding id and tier: no advisory text, contact, URL or credential.

`A-TIER` is #43 leftover 1: create the job, then change the finding's tier with a later re-score. The metric label and the alert still show the job's original tier, not the finding's current tier. The missing `NotificationJob.tier` field is #56 Spec note 1; the test uses the value recorded at creation once the model adds it.

`A-GAP` is #43 leftover 2: remove the metric for at least one evaluation interval (stop the Collector or open a scrape gap), restore it, and assert the alert stays active (does not resolve) and sends no second firing notification. The provisioned rule names `noDataState: Alerting` and `execErrState: Alerting`; `VERIFY:` Grafana's exact semantics and whether `NoData` keeps an instance active.

`A-RESOLVE` applies D1 option 1 (2026-10-22): one alert means one firing episode. A resolved notification is the same instance's normal resolution, not a second alert. The test asserts exactly one firing notification and at most one resolved notification, and does not count the resolved message as a second alert.

Grouping: one alert instance per `finding_id`/`tier` label set; the notification policy groups by `finding_id` and does not re-send while unresolved; the repeat interval is off or longer than any alert can stay open. `VERIFY:` Grafana alert-instance and notification-policy behaviour and the repeat-interval limit.

Held jobs (`held: ownerless`, `held: owner email missing`, `held: configuration error`) never set the metric and never fire the alert (A39); `A-HELD` covers at least the ownerless case. To avoid waiting the full 30-minute W, the test backdates the job's `created_at` in the test database; production W stays 30 minutes (A33).

## Responder: US-15

This section is final, not a placeholder: #50 is closed, its contract is `6ff10d9`, and QA posted PASS at `9a03ba9`. The responder uses the two GET operations `responderGetFinding` (`GET /responder/findings/{id}`) and `responderListNotificationJobs` (`GET /responder/notification-jobs?findingId=...`) with `responderAuth`; `ResponderNotificationJob` carries no recipient, owner contact, advisory summary or embedded finding. Logs come from Loki, not the API.

Demo defect: `VT_DEMO_DEFECT=notify_no_fix` makes the owner-notification formatter fail only for a finding with no fixed version. It is switched on in dev by setting the variable and restarting, and off by unsetting it. The backend refuses to start in production with it set. `P-PROD-REFUSAL` starts the backend in its production configuration (`ASSUMPTION: T-A8`: `ENVIRONMENT=production`; the final name is fixed in the build) with `VT_DEMO_DEFECT=notify_no_fix`; startup must exit non-zero and log the configuration error, while dev starts normally.

The defect is removed before production by a cleanup commit/PR that removes the code path and the variable. `P-FLAG-GONE` is a test or CI check proving the flag is gone or refused, and production promotion is blocked until cleanup. The defect must not remain in production code.

`P-DEMO` is the US-15 demo/E2E: create the no-fixed-version finding, let its job fail, assert metric 1 and one alert, wake the responder (Grafana webhook; `RESPONDER_MODE=stub` in CI), reproduce with a failing test, open a PR (fake GitHub in CI; a real token/App only in the manual demo), have the human merge, let CI deploy to dev, let n8n retry, and assert the notification succeeds, metric 0, the alert resolves and the actions are logged. Production promotion stays manual; no AWS credential.

The responder refused cases from the closed #50 contract are tested in integration `I-RESP-*`: responder token GET-only; `403` on every write; n8n, MCP and session tokens `403` on the two responder operations; no credential `401`; unknown ids and unknown `findingId` behave as the contract says. The responder cannot push to `main`, merge, change settings or touch AWS; the GitHub token/App and branch protection are checked and documented. `VERIFY:` the GitHub App/token scope and branch-protection details.

The responder reads logs from Loki with the Grafana/Loki viewer token, not from the API. Its structured log events carry no secrets or advisory text. `VERIFY:` the viewer token's Loki scope.

## Light security scan in CI

`C-SCAN` runs on every PR in the `security-scan` job on `ubuntu-latest`; the command is `make security-scan` (planned). Its scope is the application's own lockfiles and manifests, not a live service. It fails on high and critical findings in production dependencies and reports lower ones. `C-FIXTURE-VULN` makes a deliberately vulnerable fixture non-zero; `C-FIXTURE-CLEAN` passes a clean fixture. `VERIFY:` the chosen tools (for example `pip-audit` and `npm audit --omit=dev`) and their licence and behaviour; adding either needs approval.

"Light" means dependency auditing only. Secret scanning and SAST are explicitly out of scope (architecture Suggested additions / later work), so the scan has a limit.

## CI jobs and triggers

Every job runs on a pull request and on a review-branch push; a push to `main` re-runs the PR set before deploy. No job depends on a live feed or a secret.

| Job | Runner | Command or target | Tests |
|---|---|---|---|
| `unit` | `ubuntu-latest` | `make test`, `make frontend-test` | `U-*`, `F-*` |
| `sqlite-integration` | `ubuntu-latest` | `make test` | SQLite `I-*` cases |
| `frontend` | `ubuntu-latest` | `make frontend-test`, `make frontend-typecheck` | `F-*` |
| `openapi-validation` | `ubuntu-latest` | `make openapi-validate` and the backend conformance test | OpenAPI conformance |
| `security-scan` | `ubuntu-latest` | `make security-scan` (planned) | `C-*` |
| Showcase: `workflow-export` | `ubuntu-latest` | `make test-workflows` (planned) | `W-EXPORT` |
| `postgres-integration` | `ubuntu-latest` with Compose | `make test-integration` (planned) | `I-*` on Postgres |
| Showcase: `e2e` | `ubuntu-latest` with Compose | `make test-e2e` (planned) | `E-*` |
| `telemetry` | `ubuntu-latest` with Compose | `make test-compose` (planned) | `T-*` |
| `alert` | `ubuntu-latest` with Compose | `make test-compose` (planned) | `A-*` |
| `responder` | `ubuntu-latest` with Compose | `make test-compose` (planned) | `P-*` |

`make test` remains the single local test command for the rubric's unit + integration requirement, and `make verify` remains the gate. No test is skipped to make a check pass.

## Traceability matrix

Every acceptance bullet of US-1..US-16 maps to at least one test type or named case.

| Story / bullet | Acceptance | Test types or named cases |
|---|---|---|
| US-1 | Asset record shows owner name/email or ownerless marker, criticality and internet-facing; listing shows all three | `F-ASSET` (vitest); `I-ASSET` (`POST /assets`, `GET /assets`, `GET /assets/{id}`) |
| US-2a | `uv.lock` gives an entry for every package, including transitive, with name and version | `U-UV`, `I-FINDINGS` |
| US-2b | `requirements.txt` gives an entry for every direct requirement, or "version unknown" with a visible warning | `U-REQ`, `I-SCAN` |
| US-2c | `package-lock.json` gives an entry for every package, including transitive, with name and version | `U-NPM`, `I-FINDINGS` |
| US-3 | Finding shows primary id, all aliases and fixed version when one exists; clean dependency shows no finding | `U-FIXED`, `U-ALIAS`, `I-FINDINGS` |
| US-4 | Exactly one KEV value (listed / not listed / n/a) with stale marker, EPSS or n/a, and asset context | `U-KEV`, `U-EPSS`, `I-FINDINGS` |
| US-5 | Re-scoring the same inputs gives the same order; each finding shows its rank reason | `U-TIER`, `U-TIE`, `I-RANK`, `E-DELIVER` |
| US-6 (Showcase) | Brief version matches the fixed version, or structured finding with "brief unavailable"; pending marker; never a mismatched version | `U-GUARD`, `I-BRIEF`, `L-EVAL`, `R-*` |
| US-7 | Changed feed data updates signals and ranks without manual action | `I-SIGNALS` (`POST /signals/refresh`, `GET /findings`) |
| US-8a | A new top-priority finding produces exactly one owner notification and, Showcase, one GitHub issue | `I-JOBS`, Showcase: `E-DELIVER`, `S-ISSUE` |
| US-8b | Leaving and re-entering the top tier gives no second issue or notification; a `fixed` and reappearing finding (E7) starts a new lifecycle with at most one new of each | `I-LIFECYCLE`, `I-RESCAN` |
| US-8c | Exactly one notification and one issue per lifecycle even if the refresh runs twice or retries after a partial failure | `I-IDEMPOTENCY` |
| US-8d | Ownerless asset: notification held and asset flagged ownerless, while the GitHub issue is still opened once | `I-HOLD`, `A-HELD` |
| US-9a (Showcase) | Open finding past due produces an owner reminder and a security-lead escalation; weekly digest delivered once per week | `I-REMIND`, `I-DIGEST`, `E-DELIVER` |
| US-9b (Showcase) | Missing security-lead contact is a visible configuration error, not a silent drop | `I-CONFIG` |
| US-10 | Upgrade outside every affected range gives `fixed` with timestamp; still inside stays `open`; withdrawn advisory gives `withdrawn`; manual re-scan works | `I-RESCAN`, `U-WITHDRAW` |
| US-11a | Dashboard lists findings per asset with current status; changes record who, when and previous value; no automated component sets `risk accepted` | `F-STATUS`, `I-RISK` |
| US-11b | Risk acceptance requires a non-empty reason; empty or whitespace-only is rejected and status does not change | `I-RISK` (`POST /findings/{id}/risk-acceptance`) |
| US-12a (Showcase) | Known CVE returns the affected assets | `I-MCP` (`GET /mcp/vulnerabilities/{vulnerabilityId}/assets`) |
| US-12b (Showcase) | A finding stored under a GHSA id with a CVE alias is returned by the CVE lookup | `I-MCP` |
| US-12c (Showcase) | Known CVE with no asset returns empty and states known; unknown CVE returns empty and states unknown; results are distinguishable | `I-MCP` |
| US-12d (Showcase) | `list_top_exposures` returns ranked open findings | `I-MCP` (`GET /mcp/top-exposures`) |
| US-12e (Showcase) | `which_assets_affected` returns affected assets for a known CVE, in any status, each with its status | `I-MCP` |
| US-12f (Showcase) | `get_finding` returns one finding by id | `I-MCP` (`GET /mcp/findings/{id}`) |
| US-12g (Showcase) | `get_asset` returns one asset by id | `I-MCP` (`GET /assets/{id}`) |
| US-12h (Showcase) | MCP output marks advisory-derived text as quoted, labelled untrusted data in `get_finding` and `which_assets_affected`; no instructions presented | `S-MCP` |
| US-12i (Showcase) | A write with the MCP token is rejected 4xx and changes no state; the MCP server exposes no write tools | `I-AUTH-MCP` (every write operation) |
| US-13 | One scan-to-notification journey emits a metric, trace and structured log with one trace ID, viewable side by side; no excluded data | `T-JOURNEY`, `T-REFUSE` |
| US-14 | A top-priority finding not delivered in the window fires exactly one alert naming it; a successful notification fires none | `A-FIRE`, `A-TIER`, `A-GAP`, `A-RESOLVE` |
| US-15 | The undelivered finding reaches its owner, the alert resolves, actions are logged, production promotion stays manual | `P-DEMO`, `I-RESP-*`, `P-PROD-REFUSAL` |
| US-16 (Showcase) | Each workflow has a committed JSON file under `n8n/workflows/`, named after the workflow, and the exported file is the workflow the repo runs | `W-EXPORT` |

Every edge case E1..E12 maps to at least one test type or named case.

| Edge case | Expected behaviour | Test types or named cases |
|---|---|---|
| E1 | No fixed version: finding stays `open`, shows "no fixed version", is ranked by signals; any brief naming a version is rejected and the structured finding is delivered | `U-FIXED`, `U-GUARD`, `I-BRIEF`, `L-EVAL` |
| E2 | Asset with no owner: finding recorded and ranked, notification held, asset flagged ownerless | `I-HOLD`, `A-HELD` |
| E3 | Feed unavailable: OSV first scan gives `scan failed`/`feed unavailable` with no findings; a later scan keeps last-known findings and marks them stale; KEV/EPSS failure keeps the OSV scan status and stale signals; the scheduled run retries | `U-FEED`, `I-SCAN` |
| E4 | Advisory withdrawn or CVE drops out: `withdrawn`, not `fixed`; `risk accepted` also becomes `withdrawn`; no notification; only when every merged advisory is withdrawn; a reinstated advisory restores the previous status or `fixed`, with no second issue or notification; a CVE dropping out of KEV or EPSS changes only signals and rank, not status | `U-WITHDRAW`, `I-RESCAN`, `E-DELIVER` |
| E5 | Lockfile parse error: `scan failed`/`lockfile parse error`, previous findings kept and marked stale, visible in the dashboard | `U-NPM`, `I-SCAN`, `F-STATUS` |
| E6 | Telemetry backend unavailable: buffer and retry; findings, notifications and alerts unaffected; gap visible in Grafana | `T-E6` |
| E7 | Fixed finding's vulnerable version returns: `open` with audit entry and a new notification lifecycle, at most one new issue and notification | `I-RESCAN`, `I-LIFECYCLE` |
| E8 | `risk accepted` finding's signals escalate: status stays `risk accepted`, flagged "signals changed", owner and security lead notified once; re-scan may still close it | `I-SIGNALS`, `S-SIGNALS` |
| E9 | One vulnerability under two ids: alias sets intersect gives one finding keyed by CVE else primary id; all ids and ranges attached; fixed version derived from all; at most one US-8 notification per lifecycle | `U-FIXED`, `U-ALIAS`, `I-FINDINGS`, `L-EVAL` |
| E10 | `requirements.txt` without an exact version: "version unknown", warning, no OSV match, and `scanned, incomplete` when nothing matched; `-r` inside the repo only; outside or remote refused and never fetched; lockfile entry without a version behaves the same | `U-REQ`, `I-SCAN` |
| E11 | No CVE alias: `KEV: n/a (no CVE)`, EPSS `n/a`, finding still recorded and ranked; no advisory dropped for lacking a CVE | `U-KEV`, `U-EPSS`, `I-FINDINGS`, `L-EVAL` |
| E12 | Advisory text contains instructions or links: never followed; no tool, command, URL, path or credential chosen; brief only has allowed fields and the VulnTriage-built link; every advisory URL is inert | `S-*`, `U-GUARD`, `L-EVAL` |

### Stage 4 named cases

| ID | Case | Where |
|---|---|---|
| `N1` | #9 finding 11: a malicious-advisory fixture test for each flow in the spec table | `S-*` |
| `N2` | #9 finding 12: Docker Compose environment named and tests local without Docker listed | Test levels table |
| `N3` | #43 leftover 1: the US-14 gauge's `tier` label is the job's tier, not the finding's current tier | `A-TIER` |
| `N4` | #43 leftover 2: no resolve and re-fire after a metric gap | `A-GAP` |
| `N5` | #43 leftover 3 / D1: a resolved message is not a second alert | `A-RESOLVE` |
| `N6` | Showcase: exact rejected-brief case: F = `1.2.5`, stub returns `1.2.6` | `R1` |
| `N7` | Telemetry refused case: excluded attributes never reach the backend | `T-REFUSE` |
| `N8` | Demo defect refused in production | `P-PROD-REFUSAL` |

## Limits and refused cases

| Limit | Enforced by | Refused case |
|---|---|---|
| No live network | Stubs and committed fixtures; CI has no feed credentials; a network guard in the test harness | `U-NET` and `I-NET`: any outbound HTTP call fails the test |
| No real secrets | CI has no repository secrets; test settings accept only `LLM_MODE=stub` and `RESPONDER_MODE=stub`; `.env` is never read | A test run with a non-stub mode or a secret-valued variable fails before the suite starts |
| No production data | Test-owned Compose projects `vt-test`/`vt-e2e` and ephemeral volumes; migrations on a test database | `E-GUARD` and the integration guard fail before start when the target database or host is not the test one |
| Telemetry exclusions (advisory text, owner contact, repository URL, lockfile content, credentials) | One allowlist helper in code and a Collector processor before export | `T-REFUSE`: exported signals contain none of the excluded values; auto-instrumented URL attributes are dropped |
| Responder read-only | API authorisation of role `responder-read` against the two-operation allowlist | `I-RESP-WRITE` / `I-RESP-OTHERGET`: `403` and no state change |
| Demo defect refused in production | Startup check in production configuration (`ASSUMPTION: T-A8`) with `VT_DEMO_DEFECT` set | `P-PROD-REFUSAL`: startup exits non-zero and logs the error |
| Malicious text is never instructions | Quoting, labelling and defanging per flow; the LLM guardrail | `S-*`: the instruction is not followed and no URL, secret or contact detail is emitted |

## Open questions / assumptions

| Tag | Item | Resolution or owner |
|---|---|---|
| `ASSUMPTION: T-A1` | Compose service `db`; test projects `vt-test` and `vt-e2e`; fixture asset/repo names; 120 s E2E timeout | Final names fixed with the Compose work in Stage 5/#31. |
| `ASSUMPTION: T-A2` | Fixture capture baseline is 2026-10-22; the recorder writes the actual date | First deliberate capture in the build task, not #56. |
| `ASSUMPTION: T-A3` | Grafana rule uses `noDataState: Alerting` and `execErrState: Alerting` | Confirm when the rule is provisioned. |
| `ASSUMPTION: T-A4` | The US-13 metric carries the trace id as an OTel exemplar; if the exporter cannot, a trace/log join by trace id is the fallback | Spec note 2 in #56. |
| `ASSUMPTION: T-A5` | `make test` grows to include backend unit and SQLite integration and stays the single local command | Stage 5/backlog. |
| `ASSUMPTION: T-A6` | Mailpit is the local mail catcher; adding it needs approval | Stage 5/backlog. |
| `ASSUMPTION: T-A7` | `pip-audit` and `npm audit --omit=dev` are the light-scan tools; adding them needs approval | Stage 5/backlog. |
| `ASSUMPTION: T-A8` | Production configuration is selected with `ENVIRONMENT=production`; the final name is a build detail | Confirm in the backend build. |
| `VERIFY:` | OSV endpoints, batch limit, fields and fixture shape; CISA KEV URL/fields; EPSS URL/fields; GitHub contents API | Architecture § External data sources; capture the fixtures deliberately. |
| `VERIFY:` | PEP 440 and SemVer library behaviour, including leading `v` and pre-releases | Architecture § Ingestion and matching. |
| `VERIFY:` | OTel Prometheus exemplar support, Tempo-to-Loki/Grafana links, Collector processor names, SDK batch/Collector queue and self-metric names | Architecture § Observability; confirm when the stack is built. |
| `VERIFY:` | Grafana no-data/error semantics, alert-instance and notification-policy behaviour, and the repeat-interval limit | Architecture § Observability; confirm with the provisioned rule. |
| `VERIFY:` | GitHub Markdown fence rules and whether mentions inside code blocks notify | Architecture § Security boundaries. |
| `VERIFY:` | GitHub App/token scope and branch-protection details; Loki viewer token scope | Architecture § Security boundaries and § Responder agent. |
| `VERIFY:` | LLM provider, endpoint, schema-constrained output, retention and pricing | Architecture Open question 9. |
| `VERIFY:` | `pip-audit` / `npm audit` licence and behaviour | Security-scan build task. |
