# low/ — expects the scan to PASS (lower findings are reported, not failed)

At least one **moderate or low** finding per ecosystem, and **no** high or
critical. Proves "lower findings reported only" on both ecosystems (Python via
the Q1 option-2 OSV severity post-processing; npm via `--audit-level=high`).

Generate (network; see ../README.md):

- `backend/`: pin a Python package whose only current advisory is moderate/low,
  then `uv lock`. `VERIFY:` the advisory is MODERATE/LOW, not HIGH.
- `frontend/`: pin an npm package whose only current advisory is moderate/low,
  then `npm install --package-lock-only`.

Record package, version, advisory ID and severity once generated. If the only
available Python advisory is high (no clean moderate/low candidate), record that
here and rely on the npm low case; note the gap in #140.
