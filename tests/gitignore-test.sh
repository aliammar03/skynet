#!/usr/bin/env bash
# gitignore-test.sh — regression tests for the disposable .agent/ checkpoint directory (SKY-022 P3).
# TIER: T1 — checks git ignore rules only. No network, no writes. Run: bash tests/gitignore-test.sh
set -uo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_DIR}"

pass=0; fail=0
ok()   { printf '  \342\234\223 %s\n' "$1"; pass=$(( pass + 1 )); }
bad()  { printf '  \342\234\227 %s\n' "$1" >&2; fail=$(( fail + 1 )); }
eq()   { if [ "$2" = "$3" ]; then ok "$1"; else bad "$1 — expected [$3], got [$2]"; fi; }
# rc <label> <expected-rc> <fn> <args...> : assert a function's exit code
rc()   { local l="$1" want="$2"; shift 2; "$@" >/dev/null 2>&1; local got=$?; eq "${l}" "${got}" "${want}"; }

echo "== .agent/ checkpoint isolation =="
rc ".agent/CHECKPOINT.md is ignored" 0 git check-ignore .agent/CHECKPOINT.md
rc ".agent/anything-else is ignored" 0 git check-ignore .agent/anything-else
rc "AGENTS.md is not ignored" 1 git check-ignore AGENTS.md

echo
echo "gitignore-test: ${pass} passed, ${fail} failed"
[ "${fail}" -eq 0 ]
