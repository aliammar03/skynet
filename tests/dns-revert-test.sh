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

# A replay that succeeds remotely but cannot durably mark its inverse reverted must fail loudly;
# otherwise a later run may replay the same inverse against newer DNS state.
mark_tmp="$(mktemp -d)"; mark_log="${mark_tmp}/revert.jsonl"; mark_marker="${mark_tmp}/marker"
mkdir "${mark_tmp}/bin"
cat > "${mark_tmp}/bin/sudo" <<'EOF'
#!/usr/bin/env bash
exit 1
EOF
chmod +x "${mark_tmp}/bin/sudo"
DNS_REVERT_LOG="${mark_log}" DNS_REVERT_PRIOR="before" "${R}" record cloudflare mark.aliammar.net -- touch "${mark_marker}" >/dev/null
chmod 400 "${mark_log}"
if DNS_REVERT_LOG="${mark_log}" PATH="${mark_tmp}/bin:${PATH}" "${R}" undo --last >/dev/null 2>&1; then
  bad "undo reported success when reverted-state persistence failed"
else
  [ -e "${mark_marker}" ] && jq -e 'select(.reverted | not)' "${mark_log}" >/dev/null \
    && ok "replay marking failure is a hard checkpoint" || bad "replay-mark failure lost its pending inverse"
fi
chmod 600 "${mark_log}"; rm -rf "${mark_tmp}"

# --- Cloudflare writer: capture a complete inverse BEFORE mutation -------------------------------
# Fake the API and secret reader so update/create/delete + replay run entirely offline. The state
# file is the Cloudflare record; the call log proves a failed inverse write performs no mutation.
CF_TMP="$(mktemp -d)"
CF_STATE="${CF_TMP}/record.json"; CF_CALLS="${CF_TMP}/calls.log"
cat > "${CF_TMP}/curl" <<'EOF'
#!/usr/bin/env bash
set -eu
url=""; method=GET; data=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    https://*) url="$1" ;;
    -X) shift; method="$1" ;;
    --data) shift; data="$1" ;;
  esac
  shift
done
printf '%s %s\n' "$method" "$url" >> "${CF_CALLS}"
case "$method $url" in
  "GET https://api.cloudflare.com/client/v4/zones?name="*) printf '{"result":[{"id":"zone"}]}' ;;
  "GET https://api.cloudflare.com/client/v4/zones/zone/dns_records?"*)
    if [ -s "${CF_STATE}" ] && [ "$(cat "${CF_STATE}")" != null ]; then
      printf '{"result":[%s]}' "$(cat "${CF_STATE}")"
    else printf '{"result":[]}'; fi ;;
  "GET https://api.cloudflare.com/client/v4/zones/zone/dns_records/"*)
    printf '{"result":%s}' "$(cat "${CF_STATE}")" ;;
  "PUT https://api.cloudflare.com/client/v4/zones/zone/dns_records/"*)
    printf '%s' "${data}" > "${CF_STATE}"; printf '{"success":true}' ;;
  "POST https://api.cloudflare.com/client/v4/zones/zone/dns_records")
    printf '%s' "$(printf '%s' "${data}" | jq -c '. + {id:"created",zone_id:"zone"}')" > "${CF_STATE}"; printf '{"success":true}' ;;
  "DELETE https://api.cloudflare.com/client/v4/zones/zone/dns_records/"*)
    printf null > "${CF_STATE}"; printf '{"success":true}' ;;
  *) echo "unexpected fake Cloudflare request: ${method} ${url}" >&2; exit 1 ;;
esac
EOF
cat > "${CF_TMP}/sudo" <<'EOF'
#!/usr/bin/env bash
set -eu
if [ "${2:-}" = test ]; then exit 0; fi
if [ "${2:-}" = cat ]; then printf 'CF_DNS_TOKEN=test-token\nCF_ZONE=aliammar.net\nTUNNEL_ID=test-tunnel\n'; exit 0; fi
exit 1
EOF
chmod +x "${CF_TMP}/curl" "${CF_TMP}/sudo"
export CF_DNS_TOKEN=test-token CF_ZONE=aliammar.net TUNNEL_ID=test-tunnel
export DNS_REVERT_LOG="${CF_TMP}/cloudflare-log.jsonl"
export CF_CALLS CF_STATE

prior='{"id":"old-id","zone_id":"zone","name":"full.aliammar.net","type":"CNAME","content":"old-target.example","ttl":300,"proxied":false,"comment":"must survive","tags":["keep"],"data":{"value":"x"}}'
printf '%s' "${prior}" > "${CF_STATE}"
PATH="${CF_TMP}:${PATH}" scripts/cf-dns-route.sh full.aliammar.net >/dev/null
grep -q '^PUT ' "${CF_CALLS}" && ok "update mutates Cloudflare after inverse recording" || bad "update did not reach fake Cloudflare"
inverse="$(jq -r '.undo[3]' "${DNS_REVERT_LOG}")"
[ "${inverse}" = "${prior}" ] && ok "update log captures the complete prior record" || bad "update inverse lost record fields"
PATH="${CF_TMP}:${PATH}" scripts/dns-revert.sh undo --last >/dev/null
jq -e --argjson p "${prior}" '.name==$p.name and .type==$p.type and .content==$p.content and .ttl==$p.ttl and .proxied==$p.proxied and .comment==$p.comment and .tags==$p.tags and .data==$p.data' "${CF_STATE}" >/dev/null \
  && ok "update inverse restores prior Cloudflare fields" || bad "update inverse did not restore the prior record"

# A new record's inverse is an exact absence restore, not a republish with guessed attributes.
printf null > "${CF_STATE}"; : > "${DNS_REVERT_LOG}"; : > "${CF_CALLS}"
PATH="${CF_TMP}:${PATH}" scripts/cf-dns-route.sh new.aliammar.net >/dev/null
jq -e '.undo[1] == "--restore-json" and .undo[3] == "null"' "${DNS_REVERT_LOG}" >/dev/null \
  && ok "create logs an absence inverse before POST" || bad "create inverse is not absence restore"
PATH="${CF_TMP}:${PATH}" scripts/dns-revert.sh undo --last >/dev/null
[ "$(cat "${CF_STATE}")" = null ] && ok "create inverse removes the created record" || bad "create inverse did not remove record"

# If the inverse log cannot be persisted, the writer must fail closed before POST/PUT/DELETE.
printf '%s' "${prior}" > "${CF_STATE}"; : > "${CF_CALLS}"
touch "${CF_TMP}/not-a-directory"
if DNS_REVERT_LOG="${CF_TMP}/not-a-directory/log.jsonl" PATH="${CF_TMP}:${PATH}" \
  scripts/cf-dns-route.sh failclosed.aliammar.net >/dev/null 2>&1; then
  bad "writer continued after inverse persistence failure"
else
  ! grep -qE '^(POST|PUT|DELETE) ' "${CF_CALLS}" \
    && ok "inverse persistence failure blocks the Cloudflare mutation" \
    || bad "Cloudflare mutation happened after inverse persistence failure"
fi
rm -rf "${CF_TMP}"

echo
echo "dns-revert-test: ${pass} passed, ${fail} failed"
[ "${fail}" -eq 0 ]
