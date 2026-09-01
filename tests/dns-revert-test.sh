#!/usr/bin/env bash
# dns-revert-test.sh — the L7 DNS rollback executor (SKY-018 P6) must record an inverse and replay it.
#   A dumb replayer: record undo → list shows it pending → undo runs it → it's marked reverted.
# TIER: T1 — uses a temp revert log + a safe (echo) undo command; no network, no writes.
set -uo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "${REPO_DIR}"
pass=0; fail=0
ok()  { printf '  \342\234\223 %s\n' "$1"; pass=$((pass+1)); }
bad() { printf '  \342\234\227 %s\n' "$1" >&2; fail=$((fail+1)); }

export DNS_REVERT_LOG="$(mktemp)"; trap 'rm -f "${DNS_REVERT_LOG}"' EXIT
R="scripts/dns-revert.sh"

# a completed marker file the "undo" command touches, proving the inverse actually ran.
marker="$(mktemp -u)"
DNS_REVERT_PRIOR="absent (new record)" "${R}" record cloudflare probe.aliammar.net -- touch "${marker}" >/dev/null

# list shows the pending entry
"${R}" list | grep -q "probe.aliammar.net" && ok "record → list shows the pending inverse" || bad "record/list failed"
# dry-run changes nothing
"${R}" undo --dry-run --last | grep -q "would run" && ok "undo --dry-run prints without running" || bad "dry-run failed"
[ ! -e "${marker}" ] && ok "dry-run did not run the inverse" || bad "dry-run ran the inverse (should not)"
# real undo runs the inverse (the marker appears) and marks it reverted
"${R}" undo --last >/dev/null
[ -e "${marker}" ] && ok "undo replayed the inverse (marker created)" || bad "undo did not run the inverse"
[ -z "$("${R}" list | grep probe.aliammar.net || true)" ] && ok "reverted entry no longer pending" || bad "entry still pending after undo"
rm -f "${marker}"

echo
echo "dns-revert-test: ${pass} passed, ${fail} failed"
[ "${fail}" -eq 0 ]
