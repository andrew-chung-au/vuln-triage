# Test fixture manifest

Task 4 (#76) adds the first rows. The `fixture-owner__*` GitHub fixtures are
project-authored (hand-written, not captured); their rows say so. The human
confirmed three public repositories and ran the live capture on 2026-10-23;
their captured rows follow.

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
| tests/fixtures/github/astral-sh__uv-docker-example/repo.json | repository info, default branch `main` | https://github.com/astral-sh/uv-docker-example | 2026-10-23 | 694c26ad90e4cee1d42f4575dc850a4ae056828b | make record-fixtures SOURCE=github | checked: no token, key or credential (`temp_clone_token` is null); public repository metadata only |
| tests/fixtures/github/astral-sh__uv-docker-example/commit.txt | head commit SHA | https://github.com/astral-sh/uv-docker-example | 2026-10-23 | 694c26ad90e4cee1d42f4575dc850a4ae056828b | make record-fixtures SOURCE=github | checked: a commit SHA only |
| tests/fixtures/github/astral-sh__uv-docker-example/contents/uv.lock | uv.lock (935 lines, pinned with hashes) | https://github.com/astral-sh/uv-docker-example | 2026-10-23 | 694c26ad90e4cee1d42f4575dc850a4ae056828b | make record-fixtures SOURCE=github | checked: no token, key, credential or email address; package names, versions and hashes only |
| tests/fixtures/github/heroku__python-getting-started/repo.json | repository info, default branch `main` | https://github.com/heroku/python-getting-started | 2026-10-23 | 561bc55e4aaf22f98c040611fd613994547b31bb | make record-fixtures SOURCE=github | checked: no token, key or credential (`temp_clone_token` is null); public repository metadata only |
| tests/fixtures/github/heroku__python-getting-started/commit.txt | head commit SHA | https://github.com/heroku/python-getting-started | 2026-10-23 | 561bc55e4aaf22f98c040611fd613994547b31bb | make record-fixtures SOURCE=github | checked: a commit SHA only |
| tests/fixtures/github/heroku__python-getting-started/contents/requirements.txt | requirements.txt (version ranges only, no `==` pins, no `-r` include) | https://github.com/heroku/python-getting-started | 2026-10-23 | 561bc55e4aaf22f98c040611fd613994547b31bb | make record-fixtures SOURCE=github | checked: no token, key, credential or email address; four package ranges and a comment |
| tests/fixtures/github/adeyosemanputra__pygoat/repo.json | repository info, default branch `master` (a deliberately vulnerable Django app) | https://github.com/adeyosemanputra/pygoat | 2026-10-23 | 46fef968f3f44d1191363baf936aaa3335dc5c6d | make record-fixtures SOURCE=github | checked: no token, key or credential (`temp_clone_token` is null); public repository metadata only |
| tests/fixtures/github/adeyosemanputra__pygoat/commit.txt | head commit SHA | https://github.com/adeyosemanputra/pygoat | 2026-10-23 | 46fef968f3f44d1191363baf936aaa3335dc5c6d | make record-fixtures SOURCE=github | checked: a commit SHA only |
| tests/fixtures/github/adeyosemanputra__pygoat/contents/requirements.txt | requirements.txt (31 entries, nearly all pinned with `==`, older versions, no `-r` include) | https://github.com/adeyosemanputra/pygoat | 2026-10-23 | 46fef968f3f44d1191363baf936aaa3335dc5c6d | make record-fixtures SOURCE=github | checked: no token, key, credential or email address; package names and versions only |
| tests/fixtures/github/heroku__nodejs-getting-started/repo.json | repository info (GitHub redirects `heroku/node-js-getting-started` to this name), default branch `main` | https://github.com/heroku/nodejs-getting-started | 2026-10-23 | 8b8dec11fcf027522a857e0c831ee01b7124f673 | make record-fixtures SOURCE=github | checked: no token, key or credential (`temp_clone_token` is null); public repository metadata only |
| tests/fixtures/github/heroku__nodejs-getting-started/commit.txt | head commit SHA | https://github.com/heroku/nodejs-getting-started | 2026-10-23 | 8b8dec11fcf027522a857e0c831ee01b7124f673 | make record-fixtures SOURCE=github | checked: a commit SHA only |
| tests/fixtures/github/heroku__nodejs-getting-started/contents/package-lock.json | package-lock.json (lockfileVersion 3, 5366 lines) | https://github.com/heroku/nodejs-getting-started | 2026-10-23 | 8b8dec11fcf027522a857e0c831ee01b7124f673 | make record-fixtures SOURCE=github | checked: no token, key or credential; one npm package's public deprecation text contains its maintainer's public contact address (line 4997), which is registry metadata and not private data |
