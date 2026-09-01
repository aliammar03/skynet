#!/usr/bin/env bash
# digest-test.sh — the cold-boot digest must not resurface threads about DESTROYED guests.
#   The journal is append-only, so a thread resolved later still sits in its original entry and the
#   nightly re-copies it forward (SKY-018 review found CT 526 / CT 1035 — both destroyed — reported as
#   live). render-digest.sh drops an open-thread bullet naming only guests absent from inventory.
# TIER: T1 — renders to a TEMP page against a fixture journal + the real inventory. No network, no writes.
# Run: bash tests/digest-test.sh
set -uo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "${REPO_DIR}"
pass=0; fail=0
ok()  { printf '  \342\234\223 %s\n' "$1"; pass=$((pass+1)); }
bad() { printf '  \342\234\227 %s\n' "$1" >&2; fail=$((fail+1)); }

command -v jq >/dev/null || { echo "digest-test: jq required" >&2; exit 2; }

tmpj="$(mktemp -d)"; tmpp="$(mktemp)"; trap 'rm -rf "${tmpj}" "${tmpp}"' EXIT
mkdir -p "${tmpj}/2026"
# Fixture: threads about destroyed guests (526/1035/101/231/999/9091) alongside a live-guest thread
# (9090, the ops VM — present in inventory) and a guest-free thread (PBS). The filter reads the REAL
# inventory for the live-VMID set, so this asserts the actual suppression rule end-to-end.
cat > "${tmpj}/2026/2026-01-01-session-fixture.md" <<'EOF'
---
date: 2026-01-01
kind: session
title: fixture
---
## Follow-ups / open threads
- CT 526 remains running and unmapped in DNS/reservations.
- Resolve ownership of 10.10.100.35 before any destruction of stopped CT 1035.
- Confirm that core VMIDs 101, 231, 999, and 9091 were intentionally removed.
- Establish whether the VMID 9090 restart was planned.
- PBS snapshots remain unverified this run.
EOF

JDIR="${tmpj}" PAGE="${tmpp}" ./scripts/render-digest.sh >/dev/null 2>&1 || bad "render-digest failed"
out="$(cat "${tmpp}")"

for ghost in "CT 526" "CT 1035" "101, 231, 999"; do
  if grep -qF "${ghost}" <<<"${out}"; then bad "digest still lists a destroyed-guest thread: ${ghost}"
  else ok "dropped destroyed-guest thread (${ghost})"; fi
done
if grep -qF "VMID 9090 restart" <<<"${out}"; then ok "kept the live-guest thread (VMID 9090)"
else bad "wrongly dropped the live-guest (9090) thread"; fi
if grep -qF "PBS snapshots remain unverified" <<<"${out}"; then ok "kept the guest-free thread (PBS)"
else bad "wrongly dropped the guest-free (PBS) thread"; fi

echo
echo "digest-test: ${pass} passed, ${fail} failed"
[ "${fail}" -eq 0 ]
