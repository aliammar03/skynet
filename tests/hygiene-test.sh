#!/usr/bin/env bash
# hygiene-test.sh — prove the T1 hygiene entry point composes its deterministic report.
# TIER: T1 — runs local repository checks only. USAGE: bash tests/hygiene-test.sh.
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_DIR}"

pass=0; fail=0
ok()  { printf '  ✓ %s\n' "$1"; pass=$((pass + 1)); }
bad() { printf '  ✗ %s\n' "$1" >&2; fail=$((fail + 1)); }

output="$(mktemp)"; trap 'rm -f "${output}"' EXIT
HYGIENE_BASE_REF=HEAD bin/ops hygiene >"${output}" 2>&1 && ok "hygiene command exits cleanly" || bad "hygiene command failed"
grep -q '^== temporal-hygiene: pass ==$' "${output}" && ok "hygiene composes temporal gate" || bad "temporal gate missing from hygiene report"
grep -q '^== documentation-drift: pass ==$' "${output}" && ok "hygiene composes documentation drift gate" || bad "documentation drift gate missing from hygiene report"
grep -q '^== advisory review candidates ==$' "${output}" && ok "hygiene reports advisory candidates" || bad "advisory candidates missing from hygiene report"
grep -q '^== context budget ==$' "${output}" && ok "hygiene reports context budget" || bad "context budget missing from hygiene report"

echo
echo "hygiene-test: ${pass} passed, ${fail} failed"
[ "${fail}" -eq 0 ]
