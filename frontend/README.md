# VulnTriage frontend

The React client for VulnTriage. It lists vulnerable dependencies ranked P1 to P4 by real-world exploit risk, shows each finding's rank reason and audit trail, lets a signed-in user register assets and accept risk, and flags ownerless assets. It talks to the FastAPI backend over one origin: the API is served under `/api` and the proxy (Vite in dev, nginx in Compose) strips the prefix.

**Stack:** React 19, TypeScript, Vite, TanStack Router (a client-only SPA, no server renderer), Vitest.

## Development

Use the make targets from the repository root. Installing by hand would rewrite the lockfile outside the committed resolution.

```sh
make install              # npm ci for the frontend (and the backend and responder dependencies)
make dev                  # backend (SQLite) and frontend together; frontend on http://127.0.0.1:5173
make frontend-start       # the Vite dev server alone, in the background (log: .scratch/frontend.log)
make frontend-stop        # stops only the server frontend-start recorded
make frontend-test        # Vitest, once (the cases in src/test/)
make frontend-typecheck   # tsc --noEmit (vite build does not type-check)
make frontend-build       # production build to frontend/dist/
```

The full local and Compose workflows are in [`docs/development.md`](../docs/development.md).

## Build output

`make frontend-build` writes the production SPA to `frontend/dist/` (git-ignored), with `index.html` as the entry point. Serve it as static files and rewrite unmatched routes to `index.html` (SPA fallback). In Compose, `frontend/nginx.conf` does both and routes `/api/*` to the backend.

## Architecture notes

- **One services layer.** Every backend call goes through the `Services` interface in `src/services/types.ts`. `src/services/index.ts` exports `services`, the real implementation (`src/services/httpService.ts`). The in-memory mock (`mockService.ts`, `mockData.ts`) is exported as `mockServices` for the test suite only. Wire shapes follow [`docs/openapi.yaml`](../docs/openapi.yaml), so no field remapping happens in the HTTP service.
- **The UI never re-sorts findings.** Ranking is a backend responsibility; the services layer returns findings already ranked (tier, then EPSS high first with n/a last, then asset criticality, then oldest `firstSeen`).
- **Typed errors.** Rejections are `ServiceError` instances with one of four codes, mapped to HTTP status codes: `validation` (422), `not_found` (404), `conflict` (409) and `unauthenticated` (401).
- **Session.** The session is a first-party `vt_session` cookie set by the backend; mutating requests also carry a CSRF header. The UI's `src/lib/auth.ts` copy is kept in sync from the returned `User`.
- **Ownerless assets.** An asset is ownerless only when both `ownerName` and `ownerEmail` are `null` ([spec](../docs/specs.md), E2). A partial owner keeps the value that is set and is not ownerless.
- **Statuses.** Audit entries store the wire status values (`open`, `risk_accepted`, `fixed`, `withdrawn`); the screens render them through `STATUS_LABEL`, so the table shows "risk accepted".

| Method | Returns | HTTP call |
|---|---|---|
| `login` / `logout` / `currentUser` | `User` / `void` / `User` | `POST /auth/login`, `POST /auth/logout`, `GET /auth/me` |
| `listFindings` / `getFinding` | `FindingWithAsset[]` (ranked) / `FindingWithAsset` | `GET /findings`, `GET /findings/{id}` |
| `acceptRisk` | the finding, now `risk_accepted`, with a new audit entry | `POST /findings/{id}/risk-acceptance` |
| `listAssets` / `getAsset` | `Asset[]` / `Asset` | `GET /assets`, `GET /assets/{id}` |
| `registerAsset` / `updateAsset` | `Asset` (a new asset starts scanning) | `POST /assets`, `PATCH /assets/{id}` |
| `reScan` | `void` | `POST /assets/{id}/rescan` |

The full contract is [`docs/api.md`](../docs/api.md).

## Supply-chain guard

`frontend/.npmrc` sets `min-release-age=1`, so npm skips package versions published less than one day ago. npm reads this file only when it runs from `frontend/`, which the make targets do with `npm --prefix frontend`.

## Provenance

The screens were scaffolded from a mocked prototype generated with Lovable, then rebuilt around the services layer, wired to the real backend, and covered by Vitest.
