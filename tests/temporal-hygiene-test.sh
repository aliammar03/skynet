#!/usr/bin/env bash
# temporal-hygiene-test.sh — reject historical provenance from current-authority artifacts.
# TIER: T1 — reads the tracked tree and temporary fixtures; no network, credentials, or writes.
set -uo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_DIR}"

pass=0; fail=0
ok()  { printf '  ✓ %s\n' "$1"; pass=$((pass + 1)); }
bad() { printf '  ✗ %s\n' "$1" >&2; fail=$((fail + 1)); }
TMP="$(mktemp -d)"; trap 'rm -rf "${TMP}"' EXIT

current_files=(AGENTS.md README.md flake.nix .sops.yaml templates/runbook.md templates/script.sh)
while IFS= read -r file; do current_files+=("${file}"); done < <(
  find docs -type f -name '*.md' ! -path 'docs/generated/*' ! -path 'docs/history/*' ! -path 'docs/decisions/*'
  find runbooks -type f -name '*.md'
  find scripts bin -type f
  find tofu -type f -name '*.tf'
  find nix hosts -type f -name '*.nix'
  find compose -type f ! -name '*.sops'
)

numeric_violations() {
  rg -n 'SKY-[0-9]{3}' "$@" 2>/dev/null \
    | grep -vE '^bin/plan:[0-9]+:.*SKY-000' || true
}

narrative_violations() {
  rg -n -i 'used to|previously|formerly|retired|replaced|introduced by|validated during|SKY-[0-9]{3}[[:space:]]+P[0-9]+' "$@" 2>/dev/null || true
}

echo "== current-authority temporal hygiene =="
numeric="$(numeric_violations "${current_files[@]}")"
[ -z "${numeric}" ] && ok "no numeric directive provenance in current authority" \
  || bad "numeric directive provenance remains:\n${numeric}"
narrative="$(narrative_violations "${current_files[@]}")"
[ -z "${narrative}" ] && ok "no high-signal archaeology phrase in current authority" \
  || bad "historical narration remains:\n${narrative}"

echo "== temporal-hygiene regression fixtures =="
bad_directive="${TMP}/bad-directive.sh"
bad_narrative="${TMP}/bad-narrative.md"
good_compatibility="${TMP}/good-compatibility.tf"
printf '# SKY-021 P3 — temporary provenance\n' >"${bad_directive}"
printf 'This replaced the old CT during a migration.\n' >"${bad_narrative}"
printf '# Import does not round-trip vm_id; retain this compatibility ignore.\n' >"${good_compatibility}"

[ -n "$(numeric_violations "${bad_directive}")" ] \
  && ok "numeric directive fixture is rejected" \
  || bad "numeric directive fixture passed"
[ -n "$(narrative_violations "${bad_narrative}")" ] \
  && ok "historical narration fixture is rejected" \
  || bad "historical narration fixture passed"
[ -z "$(numeric_violations "${good_compatibility}")$(narrative_violations "${good_compatibility}")" ] \
  && ok "current import compatibility rationale passes" \
  || bad "current compatibility rationale was rejected"

echo
echo "temporal-hygiene-test: ${pass} passed, ${fail} failed"
[ "${fail}" -eq 0 ]
