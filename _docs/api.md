# VulnTriage API (Stage 3)

Status: draft for review (#23). The wire contract is [`_docs/openapi.yaml`](openapi.yaml); this page is the Stage 3 endpoint table and the reader's guide. It follows [`_docs/specs.md`](specs.md) and [`_docs/architecture.md`](architecture.md).

The contract is OpenAPI 3.1.0. It covers the ten operations the frontend uses: the nine `Services` methods in `frontend/src/services/types.ts`, plus `reScan` from architecture A3 and #23 decision D5.

## Endpoint table

Every row is consumed by the frontend. "Session cookie" means the `vt_session` cookie required by `cookieAuth`. "CSRF" means the required header `X-Requested-With: XMLHttpRequest`.

| Method | Path | Request | Response | Auth | Consumer |
|---|---|---|---|---|---|
| `POST` | `/auth/login` | `LoginRequest` `{username, password}` | `200` `User`; sets `vt_session` | None (this is the sign-in) | frontend |
| `POST` | `/auth/logout` | none | `204` (no body; clears `vt_session`) | None (idempotent; no session needed) | frontend |
| `GET` | `/auth/me` | none | `200` `User` | Session cookie | frontend |
| `GET` | `/findings` | none | `200` `FindingWithAsset[]`, in server rank order | Session cookie | frontend |
| `GET` | `/findings/{id}` | path `id` | `200` `FindingWithAsset` | Session cookie | frontend |
| `POST` | `/findings/{id}/risk-acceptance` | path `id`; body `RiskAcceptanceRequest` `{reason}`; CSRF | `200` `FindingWithAsset` | Session cookie | frontend |
| `GET` | `/assets` | none | `200` `Asset[]` | Session cookie | frontend |
| `GET` | `/assets/{id}` | path `id` | `200` `Asset` | Session cookie | frontend |
| `POST` | `/assets` | body `NewAssetInput`; CSRF | `201` `Asset` with `scanStatus: "not yet scanned"` | Session cookie | frontend |
| `POST` | `/assets/{id}/rescan` | path `id`; CSRF | `202`, no body | Session cookie | frontend |

`POST /assets` starts the first scan asynchronously. `POST /assets/{id}/rescan` starts a scan and returns immediately; the asset's current scan status does not change until the scan finishes, and a later `GET /assets/{id}` reports the new status. `POST /auth/logout` is idempotent and does not require a session.

## Authentication, session and CSRF

- `POST /auth/login` takes `{username, password}` and returns `User`. It sets a `vt_session` cookie (`HttpOnly`, `Secure`, `SameSite=Strict`) and returns no bearer token. The contract has no `bearerAuth` scheme.
- `POST /auth/logout` clears the cookie and returns `204`; it is idempotent and does not require a session.
- `GET /auth/me` returns the signed-in `User`, or `401` when there is no session.
- Every operation except login and logout requires `cookieAuth` and returns `401 unauthenticated` when the session is missing, expired or was logged out.
- Every non-GET operation except login and logout requires `X-Requested-With: XMLHttpRequest`. A missing or different value returns `403 forbidden` and changes no state. This is custom CSRF header A30 requires. Logout is exempt so it stays idempotent and only clears the caller's own cookie.
- A locked username (five failed logins in 15 minutes) returns `401 unauthenticated`, the same status and code as wrong credentials; the contract does not reveal whether the username exists.
- `User` is `{id, username, displayName, email, role}`, with `role` one of `security lead` or `asset owner`. Server-side identity data is not in the schema.

## Authorization

`POST /findings/{id}/risk-acceptance` takes exactly `{reason}`; `additionalProperties: false` means `who`, `actor` and `status` are not accepted, so a body containing one returns `422 validation` and changes nothing.

A `security lead` may accept risk on any finding. An `asset owner` may accept risk only when the finding's asset `ownerEmail` equals the signed-in user's `email`. Otherwise the response is `403 forbidden` and nothing changes.

## Errors, check order and responses

`Error` is `{code, message}` with both fields required and `message` non-empty, human-readable text. No error body contains a stack trace, SQL, a token, a repository URL or owner contact details.

The `Error.code` enum is exactly:

| Code | HTTP | When |
|---|---|---|
| `validation` | `422` | The body is invalid. |
| `not_found` | `404` | No finding or asset has that id. |
| `conflict` | `409` | Accepting risk on a finding that is not `open`. |
| `unauthenticated` | `401` | No/expired/logged-out session, bad login, or a locked username. |
| `forbidden` | `403` | The caller is signed in but not allowed (owner mismatch or missing CSRF). |

The check order is fixed and uses only the steps an operation has: `401` first, then `404` for an unknown id, then `403` for an authenticated caller who is not allowed, then `422` for body validation, then `409` for state.

| Operation | Responses |
|---|---|
| `login` | `200`, `401` |
| `logout` | `204` |
| `currentUser` | `200`, `401` |
| `listFindings` | `200`, `401` |
| `getFinding` | `200`, `401`, `404` |
| `acceptRisk` | `200`, `401`, `403`, `404`, `409`, `422` |
| `listAssets` | `200`, `401` |
| `getAsset` | `200`, `401`, `404` |
| `registerAsset` | `201`, `401`, `422` |
| `reScan` | `202`, `401`, `404` |

Per-operation order:

- `acceptRisk`: `401` no session, `404` unknown finding, `403` owner mismatch (or missing/incorrect CSRF header), `422` empty/whitespace-only `reason` or extra fields, `409` finding not `open`.
- `registerAsset`: `401`, then `422`.
- `getFinding` and `getAsset`: `401`, then `404`.
- Every other operation has only its `401` check (login has only its `401`).

Refused cases the contract fixes: an unknown finding with an empty reason returns `404`, not `422`; an owner mismatch with an empty reason returns `403`, not `422`; a non-open finding with a valid reason returns `409`.

## Wire schemas

Enums are exactly these strings:

| Enum | Values |
|---|---|
| `Tier` | `P1`, `P2`, `P3`, `P4` |
| `Criticality` | `low`, `medium`, `high`, `critical` |
| `FindingStatus` | `open`, `risk accepted`, `fixed`, `withdrawn` |
| `ScanStatus` | `not yet scanned`, `scan failed`, `scanned, findings`, `scanned, incomplete`, `scanned, clean` |
| `ScanFailureReason` | `feed unavailable`, `lockfile parse error`, `repository unavailable`, `no dependency files` |
| `KevValue` | `KEV: listed`, `KEV: not listed`, `KEV: n/a (no CVE)` |
| `UserRole` | `security lead`, `asset owner` |
| `BriefStatus` | `available`, `unavailable`, `pending` |

No wire value is `risk_accepted`, `not_scanned`, `scan_error`, or a boolean `kev`.

Schemas match the architecture Data model and the spec:

- `Asset` always carries `ownerName` and `ownerEmail` as required keys that are `string` or `null`. `scanFailureReason` is `null` unless `scanStatus` is `scan failed`. `scanWarnings` is an array of `{kind, file, line, message}` from the latest scan. `lastScanAt` and `lastCommitSha` are nullable.
- `Finding` uses `vulnerabilityId` (the primary advisory id), `aliases`, `cveId`, `package` and `ecosystem`. `dependencies` is an array of `{version, sourceFile, direct}` with a nullable `version`; there is no single installed-version field. `fixedVersion` is nullable. `affectedRanges` is a read-only display projection of the merged advisories' ranges, each `{range, fixedVersion}`, and does not say which range contains the installed version. `kev` is a `KevValue`; `kevStale` and `epssStale` are booleans; `rankReason` is a non-empty string. `statusBeforeWithdrawal` is `null` except while a withdrawn finding can be restored.
- `Brief` is `{summary, impact, remediation, fixVersion, referenceLink}`. `fixVersion` is nullable. `referenceLink` is built by VulnTriage from the primary id, never from advisory text. `brief` is `null` unless `briefStatus` is `available`; the internal rejection reason is never sent. `briefStatus` is `pending` when the current lifecycle has no brief row yet.
- `AuditEntry` is `{id, actor, createdAt, field, previousValue, newValue, reason, source, restoresEntryId}`. `previousValue` is nullable (`null` on creation); `reason` is required and non-empty for an entry whose `newValue` is `risk accepted`, otherwise nullable; `actor` is a user id, `re-scan` or `system`; `restoresEntryId` is nullable.
- `NewAssetInput` is `{name, ownerName, ownerEmail, criticality, internetFacing, repositoryUrl}`. The owner fields are nullable; `name` is non-empty after trimming; `repositoryUrl` must match `https://github.com/<owner>/<repo>` by schema pattern and description. `http://`, `git@github.com:...`, a non-GitHub host or an extra path returns `422 validation` and starts no scan.
- `FindingWithAsset` is `Finding` plus `asset: Asset`. Both `GET /findings` and `GET /findings/{id}` return it, including `auditTrail`, `rankReason` and `brief`/`briefStatus`.
- `GET /findings` states that the response order is the server's ranking and the client must not re-sort.

No endpoint exposes server-side-only data. No response schema contains a password hash, a session row, raw signal fetch timestamps or percentiles, advisory details or references, notification-job internals, or lifecycle internals.

## Differences from `frontend/src/services/types.ts` (D4)

The contract follows the spec and architecture, not the mock. The D4 follow-up aligns `types.ts`, `mockService.ts`, `mockData.ts`, the screens and the 35 tests with this table. Every row below is a change in that follow-up unless the last column says otherwise.

| `types.ts` today | This contract | `types.ts` / mock change in D4 |
|---|---|---|
| `ServiceErrorCode` has four values | Adds `forbidden` (`403`) | Yes: add the fifth code. |
| `User.name` | `username`, `displayName`, `role` (plus `id`, `email`) | Yes: replace `name`; add `username`, `displayName`, `role`. |
| `ScanStatus` is `scanned \| scan_error \| not_scanned` | Five values: `not yet scanned`, `scan failed`, `scanned, findings`, `scanned, incomplete`, `scanned, clean` | Yes: replace the enum. |
| `Asset` has no scan detail | Adds `scanFailureReason`, `scanWarnings`, `lastScanAt`, `lastCommitSha` | Yes: add the fields and the mock values. |
| `Asset.ownerName` / `ownerEmail` | Required nullable keys, always present | No: the current type already requires them. |
| `repositoryUrl: string` on `Asset` and `NewAssetInput` | Schema pattern allows only `https://github.com/<owner>/<repo>` | No type change; the mock's validation and fixtures change in D4. |
| `FindingStatus` value `risk_accepted` | `risk accepted` | Yes: change the enum value and `STATUS_LABEL`. |
| `Finding.packageName` | `package` plus `ecosystem` | Yes: rename and add the field. |
| `Finding.installedVersion: string` | `dependencies: {version, sourceFile, direct}[]` with nullable `version` | Yes: replace the string with the array. |
| `Finding.affectedRanges` only | Same display projection plus a finding-level `fixedVersion` | Yes: add `fixedVersion`. |
| `Finding.kev: boolean` | `kev: KevValue`, plus `kevStale` | Yes: replace the boolean; add the stale flag. |
| `Finding.epss: number \| null` | Same, plus `epssStale` | Yes: add `epssStale`. |
| `Finding.cveId` absent | `cveId: string \| null` | Yes: add the field. |
| `Finding` has no stale, signals-changed or withdrawal fields | `stale`, `staleSince`, `signalsChanged`, `statusBeforeWithdrawal` | Yes: add the fields. |
| `Finding.firstSeen` | `firstDetectedAt` | Yes: rename. |
| `briefStatus: "available" \| "rejected"` | `available`, `unavailable`, `pending` | Yes: replace `rejected`; add `pending`. |
| `Brief.advisoryReference` | `referenceLink` plus nullable `fixVersion` | Yes: rename and add the field. |
| `AuditEntry.who`, `when` | `actor`, `createdAt` | Yes: rename. |
| `AuditEntry.previousValue: string` | Nullable string | Yes: allow `null`. |
| `AuditEntry.reason?` optional | Required key; non-empty for `risk accepted`, otherwise nullable | Yes: change the type and the mock's audit writes. |
| `AuditEntry` has no source or restore link | Adds `source` and `restoresEntryId` | Yes: add the fields. |
| `Finding.structuredSummary` | Removed; the structured finding is the finding's own fields | Yes: remove the field and its uses. |
| `Finding` has no rank reason | Adds non-empty `rankReason` | Yes: add the field. |
| `Services` has nine methods | Adds `reScan(assetId): Promise<void>` for `POST /assets/{id}/rescan` | Yes: add the method to the interface and the mock. |

## Stage 3 checklist

Every frontend story that needs data maps to at least one operation:

| User story | Endpoint(s) |
|---|---|
| US-1: register an asset | `POST /assets`, `GET /assets`, `GET /assets/{id}` |
| US-2: dependencies read automatically | `POST /assets` (starts the first scan), `GET /assets/{id}` (scan status and warnings), `GET /findings` (the resulting dependency entries) |
| US-3: match vulnerabilities with fixed versions | `GET /findings`, `GET /findings/{id}` |
| US-4: enrich with KEV, EPSS and asset context | `GET /findings`, `GET /findings/{id}` |
| US-5: deterministic, explainable ranking | `GET /findings` |
| US-6: plain-language fix brief | `GET /findings`, `GET /findings/{id}` |
| US-10: re-scan closes fixed findings | `POST /assets/{id}/rescan`, `GET /assets/{id}`, `GET /findings` |
| US-11: dashboard with status, audit trail and risk acceptance | `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`, `GET /findings`, `GET /findings/{id}`, `POST /findings/{id}/risk-acceptance` |

The remaining stories are not frontend data paths here:

- US-7, US-8, US-9 and US-16 are n8n work; #27 owns their endpoints. They do not need a frontend operation.
- US-12 is the MCP server; #27 owns its tool wire shape and read-only token.
- US-13, US-14 and US-15 are telemetry, alerting and the responder. They add no frontend data path.
- US-15's responder reads the API through service credentials; that is part of #27's service-token design, not this frontend contract.

## n8n and MCP server (to add, #27)

These rows are placeholders only. #27 owns their method, path, request body and response; they are deliberately not designed here.

| Method | Path | Request | Response | Auth | Consumer |
|---|---|---|---|---|---|
| to add | to add | to add | to add | to add | [n8n (#27)](https://github.com/andrew-chung-au/vuln-triage/issues/27) |
| to add | to add | to add | to add | to add | [MCP server (#27)](https://github.com/andrew-chung-au/vuln-triage/issues/27) |

## Wire decisions made in this issue

These are the choices #23 makes where the spec and architecture left the wire shape open; the issue body records the human's D1-D5 answers:

- Authentication is the A30 session cookie plus the CSRF header (D1), not a bearer token.
- `forbidden` (`403`) is the fifth error code, for an authenticated caller who is not allowed (D2).
- `GET /findings` returns the server's rank order and the client does not re-sort.
- The returned brief is the latest row for the current lifecycle; a missing row is `pending`, an unavailable row is `unavailable`, and an earlier lifecycle's brief is never returned (D3).
- `reScan` is a tenth operation (D5).
- `scanWarnings.line` is nullable when a warning is not tied to a line.

`VERIFY:` the FastAPI version pinned in #24 generates OpenAPI 3.1.0, so #24's conformance test compares like with like. `VERIFY:` `uvx openapi-spec-validator` (the `openapi-spec-validator` package) validates OpenAPI 3.1.
