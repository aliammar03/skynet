#!/usr/bin/env bash
# collect-dns.sh — T1 read-only snapshot of Technitium zones → inventory/dns-zones.json
# USAGE: collect-dns.sh
#   Reads /opt/skynet-ops/secrets/technitium.env:
#     TECH_HOST=10.10.70.50   TECH_TOKEN=<scoped-zones-token>
#   Scope is Zones view/modify only (T2). Server settings are T3 — not touched.
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
secret="/opt/skynet-ops/secrets/technitium.env"

if ! { test -e "${secret}" 2>/dev/null || sudo test -f "${secret}"; }; then
  echo "no creds yet (${secret}) — collector idle until A2" >&2
  exit 0
fi
# shellcheck disable=SC1090
eval "$(cat "${secret}" 2>/dev/null || sudo cat "${secret}")"
: "${TECH_HOST:?}" "${TECH_TOKEN:?}"
: "${TECH_CACERT:?set TECH_CACERT in ${secret} — run: scripts/pin-cert.sh ${TECH_HOST:-<host>} 53443 /opt/skynet-ops/certs/technitium.crt}"
[ -r "${TECH_CACERT}" ] || { echo "TECH_CACERT ${TECH_CACERT} not readable" >&2; exit 1; }
curlp() { curl -sSf --max-time 15 --cacert "${TECH_CACERT}" "$@"; }

base="https://${TECH_HOST}:53443/api"
zones="$(curlp "${base}/zones/list?token=${TECH_TOKEN}" | jq '.response.zones')"

# Pull records per zone (read-only).
records="$(echo "${zones}" | jq -r '.[].name' | while read -r z; do
  curlp "${base}/zones/records/get?token=${TECH_TOKEN}&domain=${z}&zone=${z}&listZone=true" \
    | jq --arg z "${z}" '{zone:$z, records:.response.records}'
done | jq -s '.')"

out="${REPO_DIR}/inventory/dns-zones.json"
jq -n --arg ts "$(date -Iseconds)" --argjson zones "${zones}" --argjson records "${records}" \
  '{collected:$ts, zones:$zones, records:$records}' > "${out}"
echo "wrote ${out}"
