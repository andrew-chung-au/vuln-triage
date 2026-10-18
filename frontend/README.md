# Pixel Perfect Clone

Implement exactly the screenshot and nothing else

This project was built with [Lovable](https://lovable.dev).

## Build with Lovable

Continue developing this project in the [Lovable editor](https://lovable.dev/projects/f9cb1f93-46d1-4d9b-baa6-4e09b65a57f3) (private).

- **Ship faster**: describe what you want to build and Lovable handles the code.
- **Stay in sync**: every change made in Lovable is committed straight to this repository.
- **Full ownership**: this code is yours. Push to `main` on GitHub and your changes sync back into Lovable, ready for your next prompt.

## Development

Prefer working locally? You need Node.js and npm — [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating).

```sh
git clone <this-repository-url>
cd <repository-name>
npm i
npm run dev
```

## Services layer

Every backend call goes through the `Services` interface in
`src/services/types.ts`. `src/services/index.ts` exports `services`, which is
the in-memory mock (`src/services/mockService.ts`, data in
`src/services/mockData.ts`). No method makes a network call today.

Every method is async: it returns a `Promise`. Errors are untyped: a failing
call rejects with a plain `Error` whose `message` is shown to the user.

| Method | Parameters | Returns | Throws today |
|---|---|---|---|
| `login` | `username: string`, `password: string` | `Promise<User>` | `Error("Incorrect username or password.")` when the credentials don't match the demo user |
| `listFindings` | none | `Promise<FindingWithAsset[]>`, already ranked (tier, then EPSS high first with n/a last, then asset criticality high first, then oldest `firstSeen` first) | nothing |
| `getFinding` | `id: string` | `Promise<FindingWithAsset \| null>`; `null` when no finding has that id | nothing (not found is `null`, not an error) |
| `acceptRisk` | `id: string`, `reason: string`, `user: User` | `Promise<FindingWithAsset>`, the updated finding with status `risk_accepted` and a new audit entry | `Error("A reason is required to accept this risk.")` for an empty or whitespace-only reason; `Error("Finding not found.")`; `Error("Only open findings can be risk accepted.")` |
| `listAssets` | none | `Promise<Asset[]>` | nothing |
| `registerAsset` | `input: NewAssetInput` (`name`, `owner`, `criticality`, `internetFacing`, `repositoryUrl`) | `Promise<Asset>`, the new asset with `scanStatus: "not_scanned"`; an empty `owner` is stored as `null` | `Error("Asset name is required.")` for an empty or whitespace-only name |

The types (`User`, `Asset`, `Finding`, `FindingWithAsset`, `AffectedRange`,
`Brief`, `AuditEntry`, `NewAssetInput`) are defined in the same file. This
section is the input to `_docs/api.md` (issue #23); the rest of this README is
rewritten in issue #21.
