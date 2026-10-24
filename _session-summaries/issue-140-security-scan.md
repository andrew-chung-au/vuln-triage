# Issue #140 (task 20): light security scan

**Date:** 2026-10-24
**Branch:** `feat/140-security-scan`

## What changed and why

Task 20 of Milestone B (S2/B3): `make security-scan` audits the application's
own production dependencies, fails on high/critical and reports lower; a fixture
self-test proves the pass/fail rules; a `security-scan` CI job runs both on every
PR. Depends on task 19 (done) and #111 (the known Vite high finding), now closed.

## Human decisions applied

- **Q1 = option 2:** the Python side post-processes each advisory's OSV severity (pip-audit's JSON carries no severity), failing on high/critical and reporting lower. No new tool.
- **Q2 = option 2:** an advisory with no severity is treated as high (fail closed).
- Tools: `pip-audit==2.10.1` + `npm audit --omit=dev` (approved 2026-10-23).

## Files

- `ci/security-scan.sh` — scans `backend/uv.lock` (`uv export --no-dev` → `pip-audit -f json`) and `frontend/package-lock.json` (`npm audit --omit=dev`). Read-only (before/after lockfile checksum), fail-closed on missing/unreadable lockfile or advisory-service error, prints a severity summary. Takes a target dir (default repo root) so the self-test can point it at fixtures.
- `ci/security_severity.py` — the Q1-opt2 post-processor: OSV `database_specific.severity` label, else CVSS score band, else HIGH (Q2). Prints a line per finding and `COUNTS <high> <low>`; exit 2 on malformed input.
- `ci/security-scan-selftest.sh` — runs the scanner against the fixtures and checks: `vuln/` non-zero (C-FIXTURE-VULN), `clean/` zero (C-FIXTURE-CLEAN), `low/` zero, `dev-only/` zero, `missing/` non-zero.
- `tests/fixtures/security/` — `README.md` + per-fixture `SPEC.md` (vuln/clean/low/dev-only) recording the package/version/advisory to pin, and `missing/.gitkeep`. The lockfiles themselves are generated with network (see below).
- `Makefile` (protected, human-approved) — `security-scan` and `security-scan-selftest` targets.
- `.github/workflows/verify.yml` — a `security-scan` job (`timeout-minutes: 10`, `permissions: contents: read`, no secret, pinned Python/uv/Node, `uv tool install pip-audit==2.10.1`) running the self-test then the real scan.
- `_docs/testing.md` — the § Light security scan prose and the CI-jobs cell updated for the Q1-opt2 behaviour and the self-test.

## Verified here (offline)

- `bash -n` on both scripts; `security_severity.py` compiles.
- The severity helper, tested standalone: HIGH → FAIL; no-severity → HIGH/FAIL (Q2); MODERATE → reported-only; CVSS 9.8 → CRITICAL, 5.0 → MODERATE; malformed JSON → exit 2.

## ⚠️ Needs network — the human / CI / Codespace / Claude Code cloud

The agent sandbox has no shell network, so these are done elsewhere (the human
noted Codespaces / Claude Code cloud are good options):

1. **Generate the fixture lockfiles** per each `tests/fixtures/security/*/SPEC.md` (`uv lock`, `npm install --package-lock-only`). `VERIFY:` each advisory ID/severity is still reported on the day of generation.
2. **Run `make security-scan-selftest`** — all five fixtures pass their expected outcome.
3. **Run `make security-scan`** on the real tree — exit 0 after #111 (if the backend lockfile still has a high/critical, report it; no ignore list, no silent bump).
4. **`make verify`** stays green (network-free; the scan is not part of it).

The `security-scan` CI job runs 1-of-those-checks (2 and 3) automatically on the PR.

## Out of scope (unchanged)

Secret scanning and SAST; app dependency upgrades or an ignore/allowlist; SBOM /
image scanning / DAST; making the job a required branch-protection check (human);
deploy gating (tasks 17, 21).

## Follow-up / spec notes

The PM's spec notes 5 (add SAST to architecture § Suggested additions) and 6/8
(record #111 as a B3 prerequisite in the roadmap) are small doc edits left as
notes here; not blocking.
