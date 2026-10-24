# vuln/ — expects the scan to FAIL (C-FIXTURE-VULN)

A high or critical finding in **each** ecosystem, in a **production** dependency.

Generate (network; see ../README.md):

- `backend/`: a minimal `pyproject.toml` pinning a Python package with a known
  high/critical advisory, then `uv lock`.
  - Candidate: `urllib3==1.26.4` (`VERIFY:` the advisory ID and HIGH/CRITICAL
    severity on the day you generate).
- `frontend/`: a minimal `package.json` with the vulnerable package under
  `dependencies`, then `npm install --package-lock-only`.
  - Candidate: `lodash@4.17.20` (`VERIFY:` a high-severity advisory is reported
    by `npm audit --omit=dev --audit-level=high`).

Record here, once generated: package, exact version, advisory ID, severity,
generation date. A withdrawn/re-rated advisory is replaced, not skipped.
