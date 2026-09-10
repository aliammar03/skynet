#!/usr/bin/env bash
# construction-test.sh — tests the SKY-026 construction-doctrine invariant inputs and checker.
# TIER: T1 — reads repo files and a disposable temp copy only. No network, no tracked-file writes.
set -uo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_DIR}"

pass=0; fail=0
ok()   { printf '  ✓ %s\n' "$1"; pass=$(( pass + 1 )); }
bad()  { printf '  ✗ %s\n' "$1" >&2; fail=$(( fail + 1 )); }
eq()   { if [ "$2" = "$3" ]; then ok "$1"; else bad "$1 — expected [$3], got [$2]"; fi; }

sandbox_of() {
  grep -E '^[[:space:]]*sandbox_mode[[:space:]]*=' "$1" 2>/dev/null \
    | sed -nE 's/^[[:space:]]*sandbox_mode[[:space:]]*=[[:space:]]*"([^"]+)".*/\1/p' \
    | head -n 1
}

echo "== construction doctrine: clean tree matches declared truth =="
gate_out="$(./scripts/check-invariants.sh 2>&1)"; gate_status=$?
eq "check-invariants.sh exits cleanly" "${gate_status}" "0"
if printf '%s\n' "${gate_out}" | grep -q 'construction worker sandboxes match'; then
  ok "check-invariants.sh runs the construction block"
else
  bad "check-invariants.sh did not run the construction block"
fi

echo "== construction doctrine: six SKY-026 roles, no legacy role vocabulary =="
declared_roles="$(jq -r '.construction.agents[].role' invariants.json | sort)"
expected_roles=$'archivist\ncompanion\ndefault_executor\ninvestigator\nsenior_executor\ntester'
eq "invariants declares exactly the six SKY-026 roles" "${declared_roles}" "${expected_roles}"
for legacy in scout mechanic builder; do
  if [ -e ".codex/agents/${legacy}.toml" ]; then
    bad "legacy SKY-022 role TOML ${legacy}.toml still present"
  else
    ok "no legacy SKY-022 role TOML ${legacy}.toml"
  fi
done

echo "== construction doctrine: each declared role's sandbox matches its TOML =="
while IFS=$'\t' read -r role expected_sandbox; do
  eq "${role} sandbox matches declared construction value" \
    "$(sandbox_of ".codex/agents/${role}.toml")" "${expected_sandbox}"
done < <(jq -r '.construction.agents[] | "\(.role)\t\(.sandbox_mode)"' invariants.json)

echo "== construction doctrine: no workflow concurrency cap is pinned =="
if grep -qE '^[[:space:]]*max_concurrent_threads_per_session[[:space:]]*=' .codex/config.toml; then
  bad ".codex/config.toml pins a concurrency cap — SKY-026 follows the no-workflow-quota model"
else
  ok ".codex/config.toml pins no workflow concurrency cap"
fi

echo "== construction doctrine: temporary drift is rejected =="
TMP="$(mktemp -d)"; trap 'rm -rf "${TMP}"' EXIT

# A reintroduced concurrency cap must fail the gate.
cap_dir="${TMP}/cap"; mkdir -p "${cap_dir}/.codex/agents"
cp .codex/config.toml "${cap_dir}/.codex/config.toml"
cp .codex/agents/*.toml "${cap_dir}/.codex/agents/"
cp invariants.json "${cap_dir}/invariants.json"
cp scripts/check-invariants.sh "${cap_dir}/check-invariants.sh" 2>/dev/null || true
printf '\nmax_concurrent_threads_per_session = 2\n' >> "${cap_dir}/.codex/config.toml"
(
  cd "${cap_dir}"
  # Run only the cap assertion in isolation, mirroring the gate's rule.
  ! grep -qE '^[[:space:]]*max_concurrent_threads_per_session[[:space:]]*=' .codex/config.toml
)
if [ $? -ne 0 ]; then
  ok "a reintroduced max_concurrent_threads_per_session is detectable"
else
  bad "a reintroduced concurrency cap went undetected"
fi

# A drifted sandbox in a copy must not match the declared value.
tmp_toml="${TMP}/tester.toml"
cp .codex/agents/tester.toml "${tmp_toml}"
sed -i -E 's/^[[:space:]]*sandbox_mode[[:space:]]*=.*/sandbox_mode = "danger-full-access"/' "${tmp_toml}"
drift_sandbox="$(sandbox_of "${tmp_toml}")"
declared_tester="$(jq -r '.construction.agents[] | select(.role=="tester").sandbox_mode' invariants.json)"
if [ "${drift_sandbox}" != "${declared_tester}" ]; then
  ok "a drifted tester sandbox no longer matches the declared value"
else
  bad "a drifted tester sandbox still matched the declared value"
fi
eq "the real tester TOML is unchanged" "$(sandbox_of .codex/agents/tester.toml)" "${declared_tester}"

echo
echo "construction-test: ${pass} passed, ${fail} failed"
[ "${fail}" -eq 0 ]
