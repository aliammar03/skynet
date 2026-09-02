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

# regression: an undo command whose FIRST token is option-like (e.g. `--delete`, cf-dns-route's real
# delete inverse) must record + replay intact — jq --args would mis-parse it (caught by a live run).
marker2="$(mktemp -u)"
optcmd="$(mktemp)"; cat > "${optcmd}" <<EOF
#!/usr/bin/env bash
[ "\$1" = --delete ] && touch "${marker2}"
EOF
chmod +x "${optcmd}"
DNS_REVERT_PRIOR="CNAME → x" "${R}" record cloudflare opt.aliammar.net -- "${optcmd}" --delete opt.aliammar.net >/dev/null
"${R}" undo --target opt.aliammar.net >/dev/null 2>&1
[ -e "${marker2}" ] && ok "undo replays an option-like token (--delete) intact" || bad "option-like undo token lost/mis-parsed"
rm -f "${marker2}" "${optcmd}"

# replay guard: during a replay the writer must see DNS_REVERT_REPLAYING=1, so it suppresses its
# counter-inverse and the log settles (a live run caught an endless record chain without this).
flagfile="$(mktemp)"; probe="$(mktemp)"; cat > "${probe}" <<EOF
#!/usr/bin/env bash
printf '%s' "\${DNS_REVERT_REPLAYING:-unset}" > "${flagfile}"
EOF
chmod +x "${probe}"
"${R}" record cloudflare guard.aliammar.net -- "${probe}" >/dev/null
"${R}" undo --target guard.aliammar.net >/dev/null 2>&1
[ "$(cat "${flagfile}")" = 1 ] && ok "replay exports DNS_REVERT_REPLAYING=1 (no counter-inverse chain)" || bad "replay did not set the guard (got: $(cat "${flagfile}"))"
rm -f "${flagfile}" "${probe}"

echo
echo "dns-revert-test: ${pass} passed, ${fail} failed"
[ "${fail}" -eq 0 ]
