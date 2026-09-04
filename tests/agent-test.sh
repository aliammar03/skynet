#!/usr/bin/env bash
# agent-test.sh — unit tests for bin/agent's construction-helper role resolution (SKY-022 P4).
# TIER: T1 — exercises --dry-run only: no codex process, network, or repository writes. Run: bash tests/agent-test.sh
set -uo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_DIR}"

pass=0; fail=0
ok()   { printf '  \342\234\223 %s\n' "$1"; pass=$(( pass + 1 )); }
bad()  { printf '  \342\234\227 %s\n' "$1" >&2; fail=$(( fail + 1 )); }
eq()   { if [ "$2" = "$3" ]; then ok "$1"; else bad "$1 — expected [$3], got [$2]"; fi; }
# rc <label> <expected-rc> <fn> <args...> : assert a function's exit code
rc()   { local l="$1" want="$2"; shift 2; "$@" >/dev/null 2>&1; local got=$?; eq "${l}" "${got}" "${want}"; }

assert_token() {
  local label="$1" resolution="$2" token="$3"
  if printf '%s\n' "${resolution}" | grep -qE "(^|[[:space:]])${token}([[:space:]]|$)"; then
    ok "${label}: ${token}"
  else
    bad "${label}: missing ${token} in [${resolution}]"
  fi
}

assert_resolution() {
  local label="$1" role="$2" tier="$3" model="$4" effort="$5" sandbox="$6"
  shift 6
  local out got resolution
  out="$(
    unset AGENT_MODEL_SOL AGENT_MODEL_TERRA AGENT_MODEL_LUNA
    bin/agent "${role}" "noop" "$@" --dry-run 2>&1
  )"
  got=$?
  eq "${label}: dry-run exits 0" "${got}" "0"
  resolution="$(printf '%s\n' "${out}" | grep '^role=' || true)"
  assert_token "${label}" "${resolution}" "role=${role}"
  assert_token "${label}" "${resolution}" "tier=${tier}"
  assert_token "${label}" "${resolution}" "model=${model}"
  assert_token "${label}" "${resolution}" "effort=${effort}"
  assert_token "${label}" "${resolution}" "sandbox=${sandbox}"
}

echo "== bin/agent: role resolution (dry-run only) =="
assert_resolution "lead"     lead     terra gpt-5.6-terra xhigh  workspace-write
assert_resolution "builder"  builder  terra gpt-5.6-terra high   workspace-write
assert_resolution "mechanic" mechanic luna  gpt-5.6-luna  high   workspace-write
assert_resolution "scout"    scout    luna  gpt-5.6-luna  medium read-only
assert_resolution "lead --hard" lead sol gpt-5.6-sol xhigh workspace-write --hard

echo "== bin/agent: invalid role options =="
rc "builder --hard fails (lead-only)" 1 bin/agent builder noop --hard --dry-run
rc "unknown role fails" 1 bin/agent foo noop --dry-run

echo
echo "agent-test: ${pass} passed, ${fail} failed"
[ "${fail}" -eq 0 ]
