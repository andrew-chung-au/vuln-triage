#!/usr/bin/env bash
# Light dependency security scan (issue #140, task 20).
#
# Audits the application's own PRODUCTION dependencies — nothing live:
#   - Python: `uv export --no-dev` from a uv.lock, then `pip-audit` on the
#     exported requirements; severity is derived from OSV (Q1 option 2), so the
#     scan FAILS on high/critical and REPORTS lower findings. An advisory with
#     no severity is treated as high (Q2 option 2, fail closed).
#   - npm: `npm audit --omit=dev --audit-level=high` on a package-lock.json;
#     high/critical fail, moderate/low are reported only.
#
# Read-only: no --fix, no audit fix, no lockfile edit, no application install.
# Fail closed: a missing/unreadable lockfile, an advisory-service error, or
# malformed tool output exits non-zero. Secret scanning and SAST are out of
# scope ("light" = dependency auditing only).
#
# Usage:
#   ci/security-scan.sh [TARGET_DIR]
# TARGET_DIR defaults to the repo root and must contain `backend/uv.lock`
# and/or `frontend/package-lock.json`. The self-test points it at fixtures.
#
# Needs network (pip-audit and npm audit query public advisory services) and
# the tools pip-audit==2.10.1 and npm. Run it in CI, a GitHub Codespace, a
# Claude Code cloud session, or any Docker/host with network — not the agent
# sandbox (no shell network).

set -uo pipefail

TARGET_DIR="${1:-.}"
BACKEND_LOCK="$TARGET_DIR/backend/uv.lock"
FRONTEND_LOCK="$TARGET_DIR/frontend/package-lock.json"

fail=0          # 1 => at least one high/critical, or the scan could not run
high_total=0
low_total=0

die() { echo "SECURITY-SCAN ERROR: $*" >&2; exit 2; }

have() { command -v "$1" >/dev/null 2>&1; }

# --- Python --------------------------------------------------------------
scan_python() {
  local lock="$1" dir
  dir="$(dirname "$lock")"
  [ -f "$lock" ] || { echo "python: no uv.lock at $lock (skipped)"; return 0; }
  [ -r "$lock" ] || die "python lockfile $lock is not readable"
  have uv || die "uv is not installed"
  have pip-audit || die "pip-audit is not installed (need pip-audit==2.10.1)"

  echo "== Python (production deps from $lock) =="
  local before after reqs audit_json
  before="$(sha256sum "$lock")"

  # Export production-only requirements WITHOUT touching the lockfile.
  reqs="$(cd "$dir" && uv export --no-dev --no-emit-project --format requirements-txt 2>/dev/null)" \
    || die "uv export failed for $lock"

  # pip-audit over the exported requirements, JSON for post-processing. It exits
  # non-zero on any finding; we drive the pass/fail from severity, not its code,
  # so capture output and ignore its exit here.
  audit_json="$(printf '%s' "$reqs" | pip-audit --requirement /dev/stdin --format json 2>/dev/null)"
  [ -n "$audit_json" ] || die "pip-audit produced no output for $lock (advisory service error?)"

  # Post-process OSV severity: high/critical fail; lower report; unknown => high
  # (Q2 fail closed). The python helper prints a line per finding and the counts.
  local result
  result="$(SCAN_JSON="$audit_json" python3 "$(dirname "$0")/security_severity.py")" \
    || die "severity post-processing failed for $lock"
  echo "$result"
  # The helper's last line is "COUNTS <high> <low>".
  local counts
  counts="$(printf '%s\n' "$result" | awk '/^COUNTS /{print $2" "$3}' | tail -1)"
  [ -n "$counts" ] || die "severity post-processing gave no counts for $lock"
  high_total=$((high_total + ${counts% *}))
  low_total=$((low_total + ${counts#* }))

  after="$(sha256sum "$lock")"
  [ "$before" = "$after" ] || die "python lockfile changed during the scan (must be read-only)"
}

# --- npm -----------------------------------------------------------------
scan_npm() {
  local lock="$1" dir
  dir="$(dirname "$lock")"
  [ -f "$lock" ] || { echo "npm: no package-lock.json at $lock (skipped)"; return 0; }
  [ -r "$lock" ] || die "npm lockfile $lock is not readable"
  have npm || die "npm is not installed"

  echo "== npm (production deps from $lock) =="
  local before after audit_json high low
  before="$(sha256sum "$lock")"

  # --omit=dev: production deps only. --json for counts. Reads the lockfile; no
  # node_modules needed. npm audit exits non-zero on findings; parse the JSON.
  audit_json="$(cd "$dir" && npm audit --omit=dev --json 2>/dev/null)"
  [ -n "$audit_json" ] || die "npm audit produced no output for $lock (advisory service error?)"

  # Vulnerability counts by severity from the npm audit JSON.
  high="$(printf '%s' "$audit_json" | python3 -c 'import json,sys; v=json.load(sys.stdin).get("metadata",{}).get("vulnerabilities",{}); print(v.get("high",0)+v.get("critical",0))')" \
    || die "could not parse npm audit output for $lock"
  low="$(printf '%s' "$audit_json" | python3 -c 'import json,sys; v=json.load(sys.stdin).get("metadata",{}).get("vulnerabilities",{}); print(v.get("moderate",0)+v.get("low",0)+v.get("info",0))')" \
    || die "could not parse npm audit output for $lock"

  echo "npm: high/critical=$high  moderate/low/info=$low (reported only)"
  high_total=$((high_total + high))
  low_total=$((low_total + low))

  after="$(sha256sum "$lock")"
  [ "$before" = "$after" ] || die "npm lockfile changed during the scan (must be read-only)"
}

# At least one lockfile must be present, or it is a usage/fail-closed error.
if [ ! -f "$BACKEND_LOCK" ] && [ ! -f "$FRONTEND_LOCK" ]; then
  die "no backend/uv.lock or frontend/package-lock.json under $TARGET_DIR"
fi

scan_python "$BACKEND_LOCK"
scan_npm "$FRONTEND_LOCK"

echo
echo "== Summary =="
echo "high/critical: $high_total   (lower, reported only: $low_total)"
if [ "$high_total" -gt 0 ]; then
  echo "SECURITY-SCAN: FAIL ($high_total high/critical finding(s))"
  exit 1
fi
echo "SECURITY-SCAN: PASS (no high/critical; $low_total lower finding(s) reported)"
exit 0
