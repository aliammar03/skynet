#!/usr/bin/env bash
# obsidian-hygiene-test.sh — shared vault settings stay tracked; personal state and plugin payloads do not.
# TIER: T1 — checks the index and ignore rules only. Run: bash tests/obsidian-hygiene-test.sh
set -uo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_DIR}"
pass=0; fail=0
ok()  { printf '  ✓ %s\n' "$1"; pass=$((pass + 1)); }
bad() { printf '  ✗ %s\n' "$1" >&2; fail=$((fail + 1)); }

expected=$'.obsidian/app.json\n.obsidian/appearance.json\n.obsidian/community-plugins.json\n.obsidian/core-plugins.json\n.obsidian/graph.json'
actual="$(git ls-files .obsidian | sort)"
[ "${actual}" = "${expected}" ] && ok "only shared Obsidian settings are tracked" \
  || bad "tracked Obsidian files differ from the shared-settings allowlist"

for path in .obsidian/workspace.json .obsidian/workspace-mobile.json .obsidian/plugins/obsidian-git/main.js; do
  git check-ignore -q --no-index "${path}" \
    && ok "local artifact is ignored (${path})" || bad "local artifact is not ignored (${path})"
done

echo
echo "obsidian-hygiene-test: ${pass} passed, ${fail} failed"
[ "${fail}" -eq 0 ]
