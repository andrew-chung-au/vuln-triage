# Test fixture manifest

Task 4 (#76) adds the first rows. Until the human confirms three public
repositories and runs the live capture, the GitHub fixtures are
project-authored (hand-written, not captured); their rows say so and are
replaced by captured rows after the capture.

## Rules

- Captures come from public repositories only. No token, credential or private
  data is used or stored.
- `make record-fixtures SOURCE=<github|osv|kev|epss|all>` validates the value
  inside make before any shell command runs. It is never called by `make test`,
  `make verify` or CI.
- Every row records the source URL, the actual capture date, the GitHub commit
  SHA (or `n/a` for a non-GitHub feed) and the Engineer's token/private-data
  check.
- GitHub layout: `tests/fixtures/github/<owner>__<repo>/repo.json`,
  `commit.txt` and `contents/<path>` (raw file text, as the contents API
  returns it with `Accept: application/vnd.github.raw+json`).

## Fixtures

| path | fixture | source URL | capture date | GitHub commit SHA | capture method | token/private-data check |
|---|---|---|---|---|---|---|
| tests/fixtures/github/fixture-owner__uv-app/repo.json | repository info, default branch `main` | n/a (not a real repository) | n/a (written 2026-10-23) | n/a | project-authored | no token or private data (hand-written) |
| tests/fixtures/github/fixture-owner__uv-app/commit.txt | head commit SHA | n/a (not a real repository) | n/a (written 2026-10-23) | 1111111111111111111111111111111111111111 (invented) | project-authored | no token or private data (hand-written) |
| tests/fixtures/github/fixture-owner__uv-app/contents/uv.lock | uv.lock with two packages | n/a (not a real repository) | n/a (written 2026-10-23) | 1111111111111111111111111111111111111111 (invented) | project-authored | no token or private data (hand-written) |
| tests/fixtures/github/fixture-owner__pip-app/repo.json | repository info, default branch `main` | n/a (not a real repository) | n/a (written 2026-10-23) | n/a | project-authored | no token or private data (hand-written) |
| tests/fixtures/github/fixture-owner__pip-app/commit.txt | head commit SHA | n/a (not a real repository) | n/a (written 2026-10-23) | 2222222222222222222222222222222222222222 (invented) | project-authored | no token or private data (hand-written) |
| tests/fixtures/github/fixture-owner__pip-app/contents/requirements.txt | requirements.txt with `-r dev/extra.txt`, one pin, one range | n/a (not a real repository) | n/a (written 2026-10-23) | 2222222222222222222222222222222222222222 (invented) | project-authored | no token or private data (hand-written) |
| tests/fixtures/github/fixture-owner__pip-app/contents/dev/extra.txt | included requirements file | n/a (not a real repository) | n/a (written 2026-10-23) | 2222222222222222222222222222222222222222 (invented) | project-authored | no token or private data (hand-written) |
| tests/fixtures/github/fixture-owner__npm-app/repo.json | repository info, default branch `trunk` | n/a (not a real repository) | n/a (written 2026-10-23) | n/a | project-authored | no token or private data (hand-written) |
| tests/fixtures/github/fixture-owner__npm-app/commit.txt | head commit SHA | n/a (not a real repository) | n/a (written 2026-10-23) | 3333333333333333333333333333333333333333 (invented) | project-authored | no token or private data (hand-written) |
| tests/fixtures/github/fixture-owner__npm-app/contents/package-lock.json | package-lock.json (lockfileVersion 3) with two packages | n/a (not a real repository) | n/a (written 2026-10-23) | 3333333333333333333333333333333333333333 (invented) | project-authored | no token or private data (hand-written) |
