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

assert_contains() {
  local label="$1" text="$2" needle="$3"
  if printf '%s\n' "${text}" | grep -Fq -- "${needle}"; then
    ok "${label}: ${needle}"
  else
    bad "${label}: missing ${needle} in [${text}]"
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

echo "== bin/agent: --cwd validation and rendering =="
agent_cwd="$(mktemp -d)"
trap 'rm -rf -- "${agent_cwd}"' EXIT
canonical_cwd="$(cd "${REPO_DIR}" && pwd -P)"
cwd_out="$(bin/agent mechanic noop --cwd "${REPO_DIR}" --dry-run 2>&1)"
cwd_rc=$?
eq "--cwd registered root dry-run exits 0" "${cwd_rc}" "0"
assert_contains "--cwd reports canonical registered root" "${cwd_out}" "cwd=${canonical_cwd}"
assert_contains "--cwd renders canonical registered root" "${cwd_out}" "-C ${canonical_cwd}"
rc "--cwd nonexistent fails" 1 bin/agent mechanic noop --cwd "${agent_cwd}/definitely-nonexistent" --dry-run
rc "--cwd plain directory fails" 1 bin/agent mechanic noop --cwd "${agent_cwd}" --dry-run
rc "--cwd worktree subdirectory fails" 1 bin/agent mechanic noop --cwd "${REPO_DIR}/tests" --dry-run
mkdir "${agent_cwd}/unrelated"
git -C "${agent_cwd}/unrelated" init -q
rc "--cwd unrelated repository fails" 1 bin/agent mechanic noop --cwd "${agent_cwd}/unrelated" --dry-run

echo
echo "agent-test: ${pass} passed, ${fail} failed"
[ "${fail}" -eq 0 ]
