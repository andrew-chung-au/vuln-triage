#!/usr/bin/env bash
# Security-scan self-test (issue #140, task 20).
#
# Runs ci/security-scan.sh (the SAME scanner code path as `make security-scan`)
# against the committed fixtures and checks each expected outcome. Proves the
# pass/fail rules without touching the application's own lockfiles:
#
#   vuln/      -> FAIL (non-zero): a high/critical finding in each ecosystem.
#   clean/     -> PASS (0):        no findings.
#   low/       -> PASS (0):        only moderate/low (reported, not failed).
#   dev-only/  -> PASS (0):        a high/critical finding only in dev deps.
#   missing/   -> ERROR (non-zero): no lockfiles (fail closed).
#
# Needs network and pip-audit/npm, like the real scan: run it in CI, a GitHub
# Codespace or a Claude Code cloud session, not the agent sandbox.

set -uo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
scan="$here/security-scan.sh"
fixtures="$here/../tests/fixtures/security"

fail=0

# expect_exit <fixture> <wanted: zero|nonzero>
expect_exit() {
  local name="$1" want="$2" dir="$fixtures/$name" code
  if [ ! -d "$dir" ]; then
    echo "SELFTEST ERROR: fixture $name missing at $dir"; fail=1; return
  fi
  bash "$scan" "$dir" >/tmp/scan-$name.out 2>&1
  code=$?
  if { [ "$want" = "zero" ] && [ "$code" -eq 0 ]; } ||
     { [ "$want" = "nonzero" ] && [ "$code" -ne 0 ]; }; then
    echo "SELFTEST ok: $name -> exit $code (wanted $want)"
  else
    echo "SELFTEST FAIL: $name -> exit $code, wanted $want. Output:"
    sed 's/^/    /' "/tmp/scan-$name.out"
    fail=1
  fi
}

# C-FIXTURE-VULN and C-FIXTURE-CLEAN plus the PM-added cases.
expect_exit vuln     nonzero   # C-FIXTURE-VULN
expect_exit clean    zero      # C-FIXTURE-CLEAN
expect_exit low      zero
expect_exit dev-only zero
expect_exit missing  nonzero

if [ "$fail" -ne 0 ]; then
  echo "SECURITY-SCAN-SELFTEST: FAIL"
  exit 1
fi
echo "SECURITY-SCAN-SELFTEST: PASS"
exit 0
