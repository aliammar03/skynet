#!/usr/bin/env bash
# repo-surface-test.sh — prove every tracked text path receives one explicit repository surface.
# TIER: T1 — reads the local repository and temporary fixtures only. USAGE: bash tests/repo-surface-test.sh.
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_DIR}"
source scripts/repo-surface.sh

pass=0; fail=0
ok()  { printf '  ✓ %s\n' "$1"; pass=$((pass + 1)); }
bad() { printf '  ✗ %s\n' "$1" >&2; fail=$((fail + 1)); }
TMP="$(mktemp -d)"; trap 'rm -rf "${TMP}"' EXIT

repo_surface_check && ok "all tracked text has exactly one class" || bad "tracked text classifier failed"
[ "$(repo_surface_classify_path .codex/config.toml)" = current ] && ok "Codex config is current authority" || bad "Codex config was not current"
[ "$(repo_surface_classify_path .githooks/pre-commit)" = current ] && ok "hooks are current authority" || bad "hooks were not current"
[ "$(repo_surface_classify_path ca/README.md)" = current ] && ok "CA documentation is current authority" || bad "CA documentation was not current"
[ "$(repo_surface_classify_path CLAUDE.md)" = current ] && ok "engine shim is current authority" || bad "engine shim was not current"
printf '# new top-level operational text\nSKY-123\n' >"${TMP}/new-root.md"
[ "$(repo_surface_classify_path "${TMP}/new-root.md")" = current ] && ok "unknown text defaults to current" || bad "unknown text did not default to current"
[ "$(repo_surface_classify_path planning/README.md)" = planning ] && ok "planning stays exempt" || bad "planning classification changed"
[ "$(repo_surface_classify_path journal/README.md)" = history-evidence ] && ok "journal stays exempt" || bad "journal classification changed"
[ "$(repo_surface_classify_path docs/generated/README.md)" = generated ] && ok "generated docs stay exempt" || bad "generated classification changed"
[ "$(repo_surface_classify_path tests/temporal-hygiene-test.sh)" = fixture-test-data ] && ok "test fixtures stay exempt" || bad "test classification changed"
REPO_SURFACE_TEST_FORCE_UNCLASSIFIED=README.md repo_surface_classify_path README.md >/dev/null 2>&1 \
  && bad "unclassified path passed" || ok "unclassified path fails closed"
REPO_SURFACE_TEST_EXTRA_CLASS='README.md:history-evidence' repo_surface_classify_path README.md >/dev/null 2>&1 \
  && bad "ambiguous path passed" || ok "ambiguous path fails closed"

echo
echo "repo-surface-test: ${pass} passed, ${fail} failed"
[ "${fail}" -eq 0 ]
