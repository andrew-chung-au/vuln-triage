# dev-only/ — expects the scan to PASS (production-only exclusion)

A high or critical finding that exists **only in a development dependency**, so
the production-only scan (`uv export --no-dev`, `npm audit --omit=dev`) does not
see it and the scan passes.

Generate (network; see ../README.md):

- `backend/`: `pyproject.toml` with the vulnerable package under
  `[dependency-groups]` `dev` (NOT in `[project].dependencies`), then `uv lock`.
  Reuse the `vuln/` Python candidate so the finding is genuinely high/critical.
- `frontend/`: `package.json` with the vulnerable package under
  `devDependencies` (NOT `dependencies`), then `npm install --package-lock-only`.
  Reuse the `vuln/` npm candidate.

`VERIFY:` with the package in dev only, `uv export --no-dev` and
`npm audit --omit=dev` report zero high/critical — i.e. the same package that
makes `vuln/` fail must make `dev-only/` pass purely because it is dev-scoped.
