# Test fixture manifest

Task 1 adds the manifest shell only: there are no fixture payloads yet. Task 4
adds the first rows when the GitHub contents captures are recorded.

## Rules

- Captures come from public repositories only. No token, credential or private
  data is used or stored.
- `make record-fixtures SOURCE=<github|osv|kev|epss|all>` validates the value
  inside make before any shell command runs. It is never called by `make test`,
  `make verify` or CI.
- Every row records the source URL, the actual capture date, the GitHub commit
  SHA (or `n/a` for a non-GitHub feed) and the Engineer's token/private-data
  check.

## Fixtures

| path | fixture | source URL | capture date | GitHub commit SHA | capture method | token/private-data check |
|---|---|---|---|---|---|---|
