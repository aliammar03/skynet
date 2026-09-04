#!/usr/bin/env bash
# construction-test.sh — tests the SKY-022 construction-doctrine invariant inputs and checker.
# TIER: T1 — reads repo files and a disposable temp copy only. No network, no tracked-file writes.
set -uo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_DIR}"

pass=0; fail=0
ok()   { printf '  ✓ %s\n' "$1"; pass=$(( pass + 1 )); }
bad()  { printf '  ✗ %s\n' "$1" >&2; fail=$(( fail + 1 )); }
eq()   { if [ "$2" = "$3" ]; then ok "$1"; else bad "$1 — expected [$3], got [$2]"; fi; }
# rc <label> <expected-rc> <fn> <args...> : assert a function's exit code
rc()   { local l="$1" want="$2"; shift 2; "$@" >/dev/null 2>&1; local got=$?; eq "${l}" "${got}" "${want}"; }

cap_of() {
  grep -E '^[[:space:]]*max_concurrent_threads_per_session[[:space:]]*=' "$1" 2>/dev/null \
    | sed -nE 's/^[[:space:]]*max_concurrent_threads_per_session[[:space:]]*=[[:space:]]*([^[:space:]#]+).*/\1/p' \
    | head -n 1
}

config_cap_matches_declared() {
  local file="$1" declared found
  declared="$(jq -r '.construction.max_concurrent_threads_per_session' invariants.json)"
  found="$(cap_of "${file}")"
  [ -n "${found}" ] && [ "${found}" = "${declared}" ]
}

sandbox_of() {
  grep -E '^[[:space:]]*sandbox_mode[[:space:]]*=' "$1" 2>/dev/null \
    | sed -nE 's/^[[:space:]]*sandbox_mode[[:space:]]*=[[:space:]]*"([^"]+)".*/\1/p' \
    | head -n 1
}

echo "== construction doctrine: clean tree matches declared truth =="
gate_out="$(./scripts/check-invariants.sh 2>&1)"; gate_status=$?
eq "check-invariants.sh exits cleanly" "${gate_status}" "0"
if printf '%s\n' "${gate_out}" | grep -q 'construction helper cap and sandboxes match'; then
  ok "check-invariants.sh runs the construction block"
else
  bad "check-invariants.sh did not run the construction block"
fi
rc "config cap matches construction.max_concurrent_threads_per_session" 0 \
  config_cap_matches_declared .codex/config.toml
while IFS=$'\t' read -r role expected_sandbox; do
  eq "${role} sandbox matches declared construction value" \
    "$(sandbox_of ".codex/agents/${role}.toml")" "${expected_sandbox}"
done < <(jq -r '.construction.agents[] | "\(.role)\t\(.sandbox_mode)"' invariants.json)

echo "== construction doctrine: temporary drift is rejected =="
TMP="$(mktemp -d)"; trap 'rm -rf "${TMP}"' EXIT
tmp_config="${TMP}/config.toml"
cp .codex/config.toml "${tmp_config}"
sed -i -E 's/^[[:space:]]*max_concurrent_threads_per_session[[:space:]]*=.*/max_concurrent_threads_per_session = 3/' "${tmp_config}"
rc "same cap-check logic rejects a temporary cap of 3" 1 config_cap_matches_declared "${tmp_config}"
eq "temporary copy alone was changed" "$(cap_of .codex/config.toml)" \
  "$(jq -r '.construction.max_concurrent_threads_per_session' invariants.json)"

echo
echo "construction-test: ${pass} passed, ${fail} failed"
[ "${fail}" -eq 0 ]
