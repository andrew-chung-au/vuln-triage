# clean/ — expects the scan to PASS (C-FIXTURE-CLEAN)

No known findings in either ecosystem.

Generate (network; see ../README.md):

- `backend/`: a minimal `pyproject.toml` pinning a current, advisory-free
  package (e.g. a recent `packaging`), then `uv lock`.
- `frontend/`: a minimal `package.json` with a current, advisory-free package
  (e.g. a recent small utility), then `npm install --package-lock-only`.

`VERIFY:` at generation, `pip-audit` and `npm audit --omit=dev` both report zero
findings. If a dependency later gains an advisory, bump it to a clean version
and update this spec.
