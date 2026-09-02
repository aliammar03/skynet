#!/usr/bin/env bash
# cf-dns-route.sh — upsert (or delete) a proxied public CNAME for a tunnel hostname (SKY-014).
# NB: the canonical create path is now TOFU — the tunnel CNAMEs are DERIVED from the cloudflared
# ingress in tofu/cloudflare-dns.tf (publish = add the ingress line → `tofu apply`). This script is
# the BREAK-GLASS / immediate path (and `--delete` for an urgent pull); re-apply tofu afterward so
# state matches, or tofu will want to reconcile the record back.
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

envfile="/opt/skynet-ops/secrets/cloudflare-dns.env"
{ test -r "${envfile}" 2>/dev/null || sudo -n test -r "${envfile}" 2>/dev/null; } || { echo "missing ${envfile} (0600) — mint the scoped token first" >&2; exit 1; }
# The whole secrets/ dir is root:root 0700, so source the env via sudo (process substitution keeps
# the token off any argv and off disk). Matches gitops-deploy.sh's `source <(sudo -n cat ...)`.
set -a; source <(cat "${envfile}" 2>/dev/null || sudo -n cat "${envfile}"); set +a
: "${CF_DNS_TOKEN:?}" "${CF_ZONE:?}" "${TUNNEL_ID:?}"

del=0
[ "${1:-}" = "--delete" ] && { del=1; shift; }
host="${1:?usage: cf-dns-route.sh [--delete] <hostname>}"
case "${host}" in *".${CF_ZONE}") : ;; *) echo "refusing: ${host} is not in zone ${CF_ZONE}" >&2; exit 1;; esac

api() { # <path> [curl args...]
  curl -sS --fail-with-body -H "Authorization: Bearer ${CF_DNS_TOKEN}" \
    -H "Content-Type: application/json" "https://api.cloudflare.com/client/v4/$1" "${@:2}"
}

zid="$(api "zones?name=${CF_ZONE}" | jq -r '.result[0].id // empty')"
[ -n "${zid}" ] || { echo "zone ${CF_ZONE} not visible to this token (check its scope)" >&2; exit 1; }

rid="$(api "zones/${zid}/dns_records?type=CNAME&name=${host}" | jq -r '.result[0].id // empty')"

if [ "${del}" = 1 ]; then
  [ -n "${rid}" ] || { echo "no CNAME ${host} — nothing to delete"; exit 0; }
  api "zones/${zid}/dns_records/${rid}" -X DELETE >/dev/null
  echo "deleted CNAME ${host}"; exit 0
fi

target="${TUNNEL_ID}.cfargotunnel.com"
body="$(jq -nc --arg n "${host}" --arg c "${target}" '{type:"CNAME",name:$n,content:$c,proxied:true,ttl:1}')"
if [ -n "${rid}" ]; then
  api "zones/${zid}/dns_records/${rid}" -X PUT --data "${body}" >/dev/null
  echo "updated CNAME ${host} → ${target} (proxied)"
else
  api "zones/${zid}/dns_records" -X POST --data "${body}" >/dev/null
  echo "created CNAME ${host} → ${target} (proxied)"
fi
