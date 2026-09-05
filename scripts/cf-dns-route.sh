#!/usr/bin/env bash
# cf-dns-route.sh — upsert (or delete) a proxied public CNAME for a tunnel hostname (SKY-014).
# NB: the canonical create path is now TOFU — the tunnel CNAMEs are DERIVED from the cloudflared
# ingress in tofu/cloudflare-dns.tf (publish = merge the ingress line → review a saved plan →
# `scripts/tofu-apply.sh <planfile>`). This script is the BREAK-GLASS / immediate path. Its `--delete`
# is also the explicit removal checkpoint because the saved-plan wrapper refuses delete plans; after
# source removal, run a read-only tofu plan so refresh can confirm state and Cloudflare agree.
# USAGE:
#   cf-dns-route.sh <hostname>            # publish: CNAME <host> → <tunnel>.cfargotunnel.com, proxied
#   cf-dns-route.sh --delete <hostname>   # rollback: pull the record (hostname stops resolving)
#
# T2 capability: writes ONLY DNS records in the aliammar.net zone via a scoped Zone:DNS:Edit token.
# The Cloudflare account / Access / tunnel config are T3 (out of reach here). Idempotent.
# Reads /opt/skynet-ops/secrets/cloudflare-dns.env (root-owned 0600) via sudo — same pattern as
# scripts/gitops-deploy.sh, so this runs bare (no sudo wrapper on the script). It sets three vars:
#   CF_DNS_TOKEN   scoped Zone:DNS:Edit token for aliammar.net (the only secret)
#   CF_ZONE        the zone, i.e. aliammar.net
#   TUNNEL_ID      the tunnel UUID (public), e.g. 7f4c50f9-cee6-40bb-ad5a-ef6c7f30ca56
set -euo pipefail
SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"   # for the dns-revert executor (SKY-018 P6)

envfile="/opt/skynet-ops/secrets/cloudflare-dns.env"
{ test -r "${envfile}" 2>/dev/null || sudo -n test -r "${envfile}" 2>/dev/null; } || { echo "missing ${envfile} (0600) — mint the scoped token first" >&2; exit 1; }
# The whole secrets/ dir is root:root 0700, so source the env via sudo (process substitution keeps
# the token off any argv and off disk). Matches gitops-deploy.sh's `source <(sudo -n cat ...)`.
set -a; source <(cat "${envfile}" 2>/dev/null || sudo -n cat "${envfile}"); set +a
: "${CF_DNS_TOKEN:?}" "${CF_ZONE:?}" "${TUNNEL_ID:?}"

del=0; restore=0; restore_payload=""
if [ "${1:-}" = "--delete" ]; then
  del=1; shift
elif [ "${1:-}" = "--restore-json" ]; then
  restore=1; shift
fi
host="${1:?usage: cf-dns-route.sh [--delete] <hostname>}"; shift || true
if [ "${restore}" = 1 ]; then
  restore_payload="${1:?usage: cf-dns-route.sh --restore-json <hostname> <record-json|null>}"
fi
case "${host}" in *".${CF_ZONE}") : ;; *) echo "refusing: ${host} is not in zone ${CF_ZONE}" >&2; exit 1;; esac

api() { # <path> [curl args...]
  curl -sS --fail-with-body -H "Authorization: Bearer ${CF_DNS_TOKEN}" \
    -H "Content-Type: application/json" "https://api.cloudflare.com/client/v4/$1" "${@:2}"
}

# Record this write's inverse for the rollback executor — UNLESS we are ourselves a replay of an
# inverse (DNS_REVERT_REPLAYING=1): a revert must not record a counter-inverse, or the log never
# settles. This happens BEFORE the mutating API call. If the durable record cannot be written, the
# caller must stop before changing Cloudflare.
record_inverse() {
  [ "${DNS_REVERT_REPLAYING:-0}" = 1 ] && return 0
  local prior="$1"; shift
  DNS_REVERT_PRIOR="${prior}" "${SELF_DIR}/dns-revert.sh" record cloudflare "${host}" -- "$@"
}

zid="$(api "zones?name=${CF_ZONE}" | jq -r '.result[0].id // empty')"
[ -n "${zid}" ] || { echo "zone ${CF_ZONE} not visible to this token (check its scope)" >&2; exit 1; }

record_json="$(api "zones/${zid}/dns_records?type=CNAME&name=${host}" \
  | jq -c '.result[0] // empty')"
rid="$(printf '%s' "${record_json}" | jq -r '.id // empty')"

# Replay an exact inverse captured before a write. Cloudflare response metadata (id, timestamps,
# zone_id, etc.) is not writable, so restore only the API's record fields while preserving all
# user-controlled content, proxy, TTL, tags, comments, settings, priority, and data values.
if [ "${restore}" = 1 ]; then
  prior_json="${restore_payload}"
  if [ "${prior_json}" = null ] || [ -z "${prior_json}" ]; then
    [ -n "${rid}" ] || { echo "restore: ${host} already absent"; exit 0; }
    api "zones/${zid}/dns_records/${rid}" -X DELETE >/dev/null
    echo "restored ${host} to absent"
    exit 0
  fi
  prior_id="$(printf '%s' "${prior_json}" | jq -r '.id // empty')"
  [ -n "${prior_id}" ] || { echo "restore: captured record has no id" >&2; exit 1; }
  body="$(printf '%s' "${prior_json}" | jq -c '{type,name,content,ttl,proxied,priority,data,settings,tags,comment} | with_entries(select(.value != null))')"
  if [ -n "${rid}" ]; then
    api "zones/${zid}/dns_records/${rid}" -X PUT --data "${body}" >/dev/null
  else
    api "zones/${zid}/dns_records" -X POST --data "${body}" >/dev/null
  fi
  echo "restored CNAME ${host} from captured record"
  exit 0
fi

if [ "${del}" = 1 ]; then
  [ -n "${rid}" ] || { echo "no CNAME ${host} — nothing to delete"; exit 0; }
  prior="$(api "zones/${zid}/dns_records/${rid}" | jq -c '.result')"
  # inverse of a delete = restore the complete captured record, not merely this tunnel target.
  record_inverse "${prior}" "${SELF_DIR}/cf-dns-route.sh" --restore-json "${host}" "${prior}"
  api "zones/${zid}/dns_records/${rid}" -X DELETE >/dev/null
  echo "deleted CNAME ${host}"
  exit 0
fi

target="${TUNNEL_ID}.cfargotunnel.com"
body="$(jq -nc --arg n "${host}" --arg c "${target}" '{type:"CNAME",name:$n,content:$c,proxied:true,ttl:1}')"
if [ -n "${rid}" ]; then
  prior="$(api "zones/${zid}/dns_records/${rid}" | jq -c '.result')"
  # The inverse is durable before the update, and captures all mutable record fields.
  record_inverse "${prior}" "${SELF_DIR}/cf-dns-route.sh" --restore-json "${host}" "${prior}"
  api "zones/${zid}/dns_records/${rid}" -X PUT --data "${body}" >/dev/null
  echo "updated CNAME ${host} → ${target} (proxied)"
else
  # The inverse of a create is absence. Record it before POST so a logging failure cannot leave
  # an untracked public record behind.
  record_inverse "null" "${SELF_DIR}/cf-dns-route.sh" --restore-json "${host}" null
  api "zones/${zid}/dns_records" -X POST --data "${body}" >/dev/null
  echo "created CNAME ${host} → ${target} (proxied)"
fi
