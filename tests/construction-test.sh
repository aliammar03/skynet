#!/usr/bin/env bash
# construction-test.sh — validate the native construction worker role files + the invariant checker.
# The six roles spawn ONLY through Codex's native subagent mechanism (Codex loads each role's full
# contract — instructions, model, effort, sandbox — from .codex/agents/<role>.toml). There is no shell
# launcher to mirror, so this gate validates the real role source files, not a reproduction of a parser.
# TIER: T1 — reads repo files and a disposable temp copy only. No network, no tracked-file writes.
set -uo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_DIR}"

EXPECTED_ROLES=(archivist companion default_executor investigator senior_executor tester)
LEGACY_ROLES=(scout mechanic builder)

pass=0; fail=0
ok()   { printf '  ✓ %s\n' "$1"; pass=$(( pass + 1 )); }
bad()  { printf '  ✗ %s\n' "$1" >&2; fail=$(( fail + 1 )); }
eq()   { if [ "$2" = "$3" ]; then ok "$1"; else bad "$1 — expected [$3], got [$2]"; fi; }

sandbox_of() {
  grep -E '^[[:space:]]*sandbox_mode[[:space:]]*=' "$1" 2>/dev/null \
    | sed -nE 's/^[[:space:]]*sandbox_mode[[:space:]]*=[[:space:]]*"([^"]+)".*/\1/p' | head -n 1
}

echo "== construction doctrine: the invariant gate runs and passes on a clean tree =="
gate_out="$(./scripts/check-invariants.sh 2>&1)"; gate_status=$?
eq "check-invariants.sh exits cleanly" "${gate_status}" "0"
printf '%s\n' "${gate_out}" | grep -q 'construction worker sandboxes match' \
  && ok "check-invariants.sh runs the construction block" \
  || bad "check-invariants.sh did not run the construction block"

echo "== role files: exactly the six native roles, no legacy vocabulary =="
present="$(cd .codex/agents && ls *.toml 2>/dev/null | sed 's/\.toml$//' | sort | tr '\n' ' ')"
expected="$(printf '%s ' "${EXPECTED_ROLES[@]}")"
eq "exactly the six role TOMLs are present" "${present}" "${expected}"
for legacy in "${LEGACY_ROLES[@]}"; do
  [ -e ".codex/agents/${legacy}.toml" ] && bad "legacy role TOML ${legacy}.toml still present" \
    || ok "no legacy role TOML ${legacy}.toml"
done

echo "== role files: each parses and carries its full native contract =="
# Parse every role file with a real TOML parser and emit one validated TSV row per file. A parse error,
# a name that does not match the filename, a missing/empty required field, or a forbidden sandbox fails
# here (non-zero exit) and is reported below. This validates the source Codex actually loads, not a shim.
contract_tsv="$(python3 - "${EXPECTED_ROLES[@]}" <<'PY'
import sys, tomllib, pathlib
expected = set(sys.argv[1:])
rows, errors, seen = [], [], set()
for stem in sorted(expected):
    p = pathlib.Path(".codex/agents", f"{stem}.toml")
    try:
        d = tomllib.load(open(p, "rb"))
    except Exception as e:                       # parse failure is a hard fail
        errors.append(f"{stem}: does not parse as TOML: {e}")
        continue
    name = d.get("name", "")
    if name != stem:
        errors.append(f"{stem}: name is {name!r}, expected {stem!r} (name must match filename)")
    if name in seen:
        errors.append(f"{stem}: duplicate role name {name!r}")
    seen.add(name)
    for field in ("model", "model_reasoning_effort", "sandbox_mode", "description",
                  "developer_instructions"):
        if not str(d.get(field, "")).strip():
            errors.append(f"{stem}: missing or empty {field}")
    if d.get("sandbox_mode") == "danger-full-access":
        errors.append(f"{stem}: sandbox danger-full-access is forbidden for a construction worker")
    rows.append("\t".join([stem, name, str(d.get("model","")), str(d.get("model_reasoning_effort","")),
                            str(d.get("sandbox_mode","")), str(len(str(d.get("description","")))),
                            str(len(str(d.get("developer_instructions",""))))]))
if errors:
    sys.stderr.write("\n".join(errors) + "\n")
    sys.exit(1)
print("\n".join(rows))
PY
)"
parse_rc=$?
if [ "${parse_rc}" -ne 0 ]; then
  bad "role contract validation failed:"$'\n'"${contract_tsv}"
else
  while IFS=$'\t' read -r stem name model effort sandbox dlen ilen; do
    [ -n "${stem}" ] || continue
    ok "${stem}: parses; name=${name}; model=${model}; effort=${effort}; sandbox=${sandbox}; desc ${dlen}B; instructions ${ilen}B"
  done <<< "${contract_tsv}"
fi

echo "== invariants.json and the role files agree on the six roles and their sandboxes =="
declared_roles="$(jq -r '.construction.agents[].role' invariants.json | sort | tr '\n' ' ')"
eq "invariants declares exactly the six roles" "${declared_roles}" "${expected}"
while IFS=$'\t' read -r role expected_sandbox; do
  eq "${role} TOML sandbox matches the declared value" \
    "$(sandbox_of ".codex/agents/${role}.toml")" "${expected_sandbox}"
done < <(jq -r '.construction.agents[] | "\(.role)\t\(.sandbox_mode)"' invariants.json)

echo "== no workflow concurrency cap is pinned =="
grep -qE '^[[:space:]]*max_concurrent_threads_per_session[[:space:]]*=' .codex/config.toml \
  && bad ".codex/config.toml pins a concurrency cap — the no-workflow-quota model is in effect" \
  || ok ".codex/config.toml pins no workflow concurrency cap"

echo "== temporary drift is rejected =="
TMP="$(mktemp -d)"; trap 'rm -rf "${TMP}"' EXIT
# A reintroduced cap is detectable by the same rule the gate uses.
cp .codex/config.toml "${TMP}/config.toml"
printf '\nmax_concurrent_threads_per_session = 2\n' >> "${TMP}/config.toml"
grep -qE '^[[:space:]]*max_concurrent_threads_per_session[[:space:]]*=' "${TMP}/config.toml" \
  && ok "a reintroduced max_concurrent_threads_per_session is detectable" \
  || bad "a reintroduced concurrency cap went undetected"
# A drifted sandbox in a copy no longer matches the declared value.
cp .codex/agents/tester.toml "${TMP}/tester.toml"
sed -i -E 's/^[[:space:]]*sandbox_mode[[:space:]]*=.*/sandbox_mode = "danger-full-access"/' "${TMP}/tester.toml"
declared_tester="$(jq -r '.construction.agents[] | select(.role=="tester").sandbox_mode' invariants.json)"
[ "$(sandbox_of "${TMP}/tester.toml")" != "${declared_tester}" ] \
  && ok "a drifted tester sandbox no longer matches the declared value" \
  || bad "a drifted tester sandbox still matched the declared value"
eq "the real tester TOML is unchanged" "$(sandbox_of .codex/agents/tester.toml)" "${declared_tester}"

echo
echo "construction-test: ${pass} passed, ${fail} failed"
[ "${fail}" -eq 0 ]
