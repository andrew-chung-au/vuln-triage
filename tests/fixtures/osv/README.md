# OSV fixtures (issue #77, task 5)

Committed OSV responses replayed by `tests/osv_stub.py` through
`httpx.MockTransport`, so the matcher is tested with no outbound call (the
network guard fails any real request).

Layout:

- `querybatch.json` — the response shape of `POST /v1/querybatch`. The stub maps
  each `(ecosystem, name, version)` query to a `results[]` entry here keyed by
  `"<ecosystem>|<name>|<version>"` in `by_query`; an unknown query returns an
  empty `vulns` list (OSV returns an empty result, not an error).
- `vulns/<id>.json` — the full advisory returned by `GET /v1/vulns/{id}`, in the
  real OSV schema fields the matcher reads: `id`, `aliases`, `modified`,
  `withdrawn` (when withdrawn), `summary`, `details`, `affected[]`
  (`package.{ecosystem,name}`, `ranges[].{type,events[]}`, `versions[]`) and
  `references[]`.

These are **project-authored** fixtures (hand-written, not captured) built to
exercise the `U-FIXED`, `U-ALIAS` and `U-WITHDRAW` cases deterministically; the
versions line up with packages in the recorded GitHub fixtures
(`urllib3`, `PyYAML`, `requests`). `make record-fixtures SOURCE=osv` can recapture
live OSV responses over the public API (human-run, its own approved commit);
see `tests/fixtures/MANIFEST.md`.
