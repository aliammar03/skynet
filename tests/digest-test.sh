#!/usr/bin/env bash
# digest-test.sh — the cold-boot digest reads explicit current thread state, never guesses from old
# journal prose. T1 — fixtures only; no network or repository mutation. Run: bash tests/digest-test.sh
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

cat > "${tmpj}/2026/2026-01-01-session-resolved.md" <<'EOF'
---
date: 2026-01-01
time: 09:00:00
kind: session # inline template comment must not leak into the digest
title: resolved fixture
thread_status: resolved
---
## Follow-ups / open threads
- PR #185 still needs review.
- PR #186 needs CI and human review.
- Phase 2 may start only after Phase 1 merges.
EOF

cat > "${tmpj}/2026/2026-01-01-session-open-early.md" <<'EOF'
---
date: 2026-01-01
time: 10:00:00
kind: session
title: explicit open early
thread_status: open
---
## Follow-ups / open threads
- Explicit early follow-up remains open.
EOF

cat > "${tmpj}/2026/2026-01-01-session-open-late.md" <<'EOF'
---
date: 2026-01-01
time: 18:00:00
kind: session
title: explicit open late
thread_status: open
---
## Follow-ups / open threads
- Explicit late follow-up remains open.
EOF

JDIR="${tmpj}" PAGE="${tmpp}" ./scripts/render-digest.sh >/dev/null 2>&1 || bad "render-digest failed"
out="$(cat "${tmpp}")"

for ghost in "CT 526" "CT 1035" "101, 231, 999" "VMID 9090 restart" "PBS snapshots remain unverified"; do
  if grep -qF "${ghost}" <<<"${out}"; then bad "digest still lists a destroyed-guest thread: ${ghost}"
  else ok "untagged historical thread is not promoted (${ghost})"; fi
done
grep -qF "Explicit early follow-up remains open" <<<"${out}" \
  && grep -qF "Explicit late follow-up remains open" <<<"${out}" \
  && ok "explicit open threads remain visible" || bad "explicit open threads missing"
if grep -Eq 'PR #185|PR #186|Phase 2 may start only after Phase 1' <<<"${out}"; then
  bad "resolved dependency was promoted"
else
  ok "resolved dependencies stay hidden"
fi
grep -qF "unclassified follow-ups; status unknown" <<<"${out}" \
  && ok "untagged historical state is reported unknown" || bad "unknown thread state was not surfaced"
if [ "$(grep -n 'explicit open late' <<<"${out}" | head -1 | cut -d: -f1)" -lt "$(grep -n 'explicit open early' <<<"${out}" | head -1 | cut -d: -f1)" ]; then
  ok "same-day episodes sort by explicit time"
else
  bad "same-day episode ordering did not use time"
fi
grep -qF 'session # inline' <<<"${out}" \
  && bad "inline frontmatter comment leaked" || ok "frontmatter parser strips inline comments"

echo
echo "digest-test: ${pass} passed, ${fail} failed"
[ "${fail}" -eq 0 ]
