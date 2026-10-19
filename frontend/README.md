# VulnTriage frontend

A React client for VulnTriage: it lists vulnerable dependencies ranked P1 to P4 by
real-world exploit risk, shows each finding's brief and audit trail, and routes
the fix to the owning team. It is the long-lived client for the project; it
serves with no backend today because every call goes through the mock services
layer.

## Development

You need Node.js and npm (the project is developed with Node.js 24 and npm 11).
Install dependencies and start the Vite dev server with the make targets below;
installing by hand would rewrite the lockfile outside the committed resolution.

```sh
git clone <this-repository-url>
cd <repository-name>
make install
make frontend-start
```

The dev server listens on `127.0.0.1:5173` (log: `.scratch/frontend.log`, PID:
`.scratch/frontend.pid`). `make frontend-stop` stops the server that
`make frontend-start` started.

## Make targets

Run these from the repository root; they wrap the frontend commands:

| Target | Does |
|---|---|
| `make install` | Installs all dependencies (currently the frontend's). |
| `make frontend-install` | Installs dependencies from `package-lock.json` (`npm ci`). |
| `make frontend-test` | Runs the unit tests once (`vitest run`, the 35 cases in `src/test/`). |
| `make test` | Runs all the project's tests (currently the frontend's). |
| `make frontend-start` | Starts the Vite dev server in the background on host `127.0.0.1`, port `5173` (log: `.scratch/frontend.log`, PID: `.scratch/frontend.pid`). |
| `make frontend-stop` | Stops the server that `make frontend-start` started (only the recorded PID). |
| `make frontend-build` | Builds the production SPA to `frontend/dist/` (`vite build`). |

`frontend-start` passes `--host 127.0.0.1 --port 5173` explicitly, so it does not
depend on app-builder sandbox detection. The app serves with no backend running:
every backend call is mocked in the services layer.

## Render mode and build

Render mode (human decision on #21, 2026-10-19): **plain TanStack Router + Vite**,
a client-only SPA. `vite.config.ts` runs the `tanstackRouter` plugin (not
`@tanstack/react-start`), and `index.html` plus `src/main.tsx` mount the router.
There is no server renderer and no Node runtime.

`make frontend-build` writes the production output to **`frontend/dist/`**, with
`frontend/dist/index.html` as the entry point. Serve that folder as static files
and rewrite unmatched routes to `index.html` (SPA fallback). `frontend/dist/` is
git-ignored.

## Architecture notes

- All backend calls go through `src/services` (the `Services` interface);
  `mockServices` is the in-memory implementation. Why: swap in a real API later
  without touching screens.
- The services layer returns findings pre-ranked; the UI must never re-sort them.
  Why: ranking is a backend responsibility per the spec.
- The services layer owns the signed-in session and persists it in
  `sessionStorage`, so the session survives a reload. The login and sign-out
  screens keep the UI's `src/lib/auth.ts` session in sync from the returned
  `User`. Why: the service session behaves like a real API's; #25 replaces the
  local copy in `lib/auth.ts` with `currentUser()`.

The mock data lives in module memory (`src/services/mockService.ts`, seeded from
`src/services/mockData.ts`). The app is client-only, so there is no server-side
copy today; issue #25 must not carry this in-memory mock into the HTTP services.

## Supply-chain guard

`frontend/.npmrc` sets `min-release-age=1`, so npm skips package versions
published less than one day ago. This replaces the Bun `minimumReleaseAge` guard
that was removed with `bunfig.toml` (review item E in
`_docs/reviews/2026-10-18-review-issues-15-20.md`). The install step only reads
this file when it runs from `frontend/`; the make targets do that with
`npm --prefix frontend`.

## Services layer

Every backend call goes through the `Services` interface in
`src/services/types.ts`. `src/services/index.ts` exports `services`, which is
the in-memory mock (`src/services/mockService.ts`, data in
`src/services/mockData.ts`), plus `demoCredentials` for the login screen. No
method makes a network call today.

Every method is async and returns a `Promise`. Rejections are `ServiceError`
instances exported from `src/services/index.ts`; the mock never throws a plain
`Error` or a string. `ServiceError` has a `message` and one of four `code`
values, which #23 maps to HTTP status codes:

| Code | HTTP (proposed) | When |
|---|---|---|
| `validation` | 422 | an empty or whitespace-only reason, an empty asset name |
| `not_found` | 404 | no finding or asset has that id |
| `conflict` | 409 | accepting risk on a finding that is not `open` |
| `unauthenticated` | 401 | no signed-in session, or wrong/empty credentials |

`login` establishes the services session; `logout` clears it and is idempotent;
`currentUser` returns the signed-in `User`. Every other method rejects
`unauthenticated` when nobody is signed in. The session is persisted in
`sessionStorage`, so a page reload keeps it.

`acceptRisk` records `who` from the signed-in user's name. Audit entries store
the wire status values (`open`, `risk_accepted`, `fixed`, `withdrawn`) and the
screen renders them through `STATUS_LABEL`, so the table shows "risk accepted".

An asset is ownerless only when both `ownerName` and `ownerEmail` are `null`
(`specs.md` E2). A partial owner keeps the one value that is set and is not
ownerless (no notification rule is decided here).

The table marks each HTTP call "proposed until #23":

| Method | Parameters | Returns | Error codes | Proposed HTTP call (until #23) |
|---|---|---|---|---|
| `login` | `username: string`, `password: string` | `Promise<User>` | `unauthenticated` | `POST /auth/login` |
| `logout` | none | `Promise<void>` | none (idempotent) | `POST /auth/logout` |
| `currentUser` | none | `Promise<User>` | `unauthenticated` | `GET /auth/me` |
| `listFindings` | none | `Promise<FindingWithAsset[]>`, already ranked (tier, then EPSS high first with n/a last, then asset criticality high first, then oldest `firstSeen` first) | `unauthenticated` | `GET /findings` |
| `getFinding` | `id: string` | `Promise<FindingWithAsset>` (the finding joined with its asset) | `unauthenticated`, `not_found` | `GET /findings/{id}` |
| `acceptRisk` | `id: string`, `reason: string` | `Promise<FindingWithAsset>`, updated to `risk_accepted` with a new audit entry | `unauthenticated`, `validation`, `not_found`, `conflict` | `POST /findings/{id}/risk-acceptance` |
| `listAssets` | none | `Promise<Asset[]>` | `unauthenticated` | `GET /assets` |
| `getAsset` | `id: string` | `Promise<Asset>` | `unauthenticated`, `not_found` | `GET /assets/{id}` |
| `registerAsset` | `input: NewAssetInput` (`name`, `ownerName`, `ownerEmail`, `criticality`, `internetFacing`, `repositoryUrl`) | `Promise<Asset>`, the new asset with `scanStatus: "not_scanned"` | `unauthenticated`, `validation` | `POST /assets` |

The types (`User`, `Asset`, `Finding`, `FindingWithAsset`, `AffectedRange`,
`Brief`, `AuditEntry`, `NewAssetInput`) are defined in the same file. This
section is the input to `_docs/api.md` (issue #23).

## Provenance

Provenance: generated by [Lovable](https://lovable.dev/projects/f9cb1f93-46d1-4d9b-baa6-4e09b65a57f3) from commit `0dd108a` and built on 2026-10-18; the compared Bolt alternative is at commit `fea6fb7` (see `_docs/reviews/2026-10-18-frontend-comparison.md`).
