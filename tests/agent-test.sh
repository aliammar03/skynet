#!/usr/bin/env bash
# agent-test.sh — unit tests for bin/agent's SKY-026 construction-worker role resolution.
# TIER: T1 — exercises --dry-run only: no codex process, network, or repository writes. Run: bash tests/agent-test.sh
set -uo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_DIR}"

ROLES=(companion investigator default_executor senior_executor tester archivist)

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

toml_value() {  # toml_value <role> <key>
  sed -nE "s/^[[:space:]]*$2[[:space:]]*=[[:space:]]*\"([^\"]+)\".*/\1/p" ".codex/agents/$1.toml" | head -n 1
}

echo "== bin/agent: each role resolves to its TOML model/effort/sandbox (source TOML wins) =="
for role in "${ROLES[@]}"; do
  model="$(toml_value "${role}" model)"
  effort="$(toml_value "${role}" model_reasoning_effort)"
  sandbox="$(toml_value "${role}" sandbox_mode)"
  out="$(bin/agent "${role}" "noop" --dry-run 2>&1)"; got=$?
  eq "${role}: dry-run exits 0" "${got}" "0"
  resolution="$(printf '%s\n' "${out}" | grep '^role=' || true)"
  assert_token "${role}" "${resolution}" "role=${role}"
  assert_token "${role}" "${resolution}" "model=${model}"
  assert_token "${role}" "${resolution}" "effort=${effort}"
  assert_token "${role}" "${resolution}" "sandbox=${sandbox}"
  # The launched codex command must pin the same model + effort.
  assert_contains "${role}: renders --model" "${out}" "--model ${model}"
  # The dry-run renders the command with %q shell-quoting, so the inner quotes are backslash-escaped.
  assert_contains "${role}: renders reasoning effort" "${out}" "model_reasoning_effort=\\\"${effort}\\\""
  assert_contains "${role}: renders --sandbox" "${out}" "--sandbox ${sandbox}"
done

echo "== bin/agent: read-only roles run read-only; write roles never get danger-full-access =="
for role in companion investigator; do
  eq "${role} is read-only" "$(toml_value "${role}" sandbox_mode)" "read-only"
done
for role in default_executor senior_executor tester archivist; do
  sandbox="$(toml_value "${role}" sandbox_mode)"
  eq "${role} is workspace-write" "${sandbox}" "workspace-write"
  [ "${sandbox}" != "danger-full-access" ] && ok "${role} is not danger-full-access" || bad "${role} is danger-full-access"
done

echo "== bin/agent: SKY-022 role vocabulary and flags are gone =="
for legacy in scout mechanic builder lead review; do
  rc "legacy role '${legacy}' is rejected" 1 bin/agent "${legacy}" noop --dry-run
done
rc "unknown role fails" 1 bin/agent foo noop --dry-run
rc "obsolete --tier flag fails" 1 bin/agent default_executor noop --tier astra --dry-run
rc "obsolete --hard flag fails" 1 bin/agent default_executor noop --hard --dry-run
rc "missing prompt fails" 1 bin/agent companion

echo "== bin/agent: --cwd validation and rendering =="
agent_cwd="$(mktemp -d)"
trap 'rm -rf -- "${agent_cwd}"' EXIT
canonical_cwd="$(cd "${REPO_DIR}" && pwd -P)"
cwd_out="$(bin/agent default_executor noop --cwd "${REPO_DIR}" --dry-run 2>&1)"
cwd_rc=$?
eq "--cwd registered root dry-run exits 0" "${cwd_rc}" "0"
assert_contains "--cwd reports canonical registered root" "${cwd_out}" "cwd=${canonical_cwd}"
assert_contains "--cwd renders canonical registered root" "${cwd_out}" "-C ${canonical_cwd}"
rc "--cwd nonexistent fails" 1 bin/agent default_executor noop --cwd "${agent_cwd}/definitely-nonexistent" --dry-run
rc "--cwd plain directory fails" 1 bin/agent default_executor noop --cwd "${agent_cwd}" --dry-run
rc "--cwd worktree subdirectory fails" 1 bin/agent default_executor noop --cwd "${REPO_DIR}/tests" --dry-run
mkdir "${agent_cwd}/unrelated"
git -C "${agent_cwd}/unrelated" init -q
rc "--cwd unrelated repository fails" 1 bin/agent default_executor noop --cwd "${agent_cwd}/unrelated" --dry-run

echo
echo "agent-test: ${pass} passed, ${fail} failed"
[ "${fail}" -eq 0 ]
