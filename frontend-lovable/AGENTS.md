<!-- LOVABLE:BEGIN -->
> [!IMPORTANT]
> This project is connected to [Lovable](https://lovable.dev). Avoid rewriting
> published git history — force pushing, or rebasing/amending/squashing commits
> that are already pushed — as it rewrites history on Lovable's side and the
> user will likely lose their project history.
>
> Commits you push to the connected branch sync back to Lovable and show up in
> the editor, so keep the branch in a working state.
<!-- LOVABLE:END -->

## Architecture
- All backend calls go through `src/services` (the `Services` interface); `mockServices` is the in-memory implementation. Why: swap in a real API later without touching screens.
- The services layer returns findings pre-ranked; UI must never re-sort them. Why: ranking is a backend responsibility per spec.
- Auth is a mocked client-side session (`src/lib/auth.ts`); protected screens live under the `_authed` layout. Why: prototype has no backend.
