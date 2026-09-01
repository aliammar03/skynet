#!/usr/bin/env bash
# collect-network-gear.sh — T1 read-only snapshot of the Omada network estate → inventory/network-gear.json
# USAGE: collect-network-gear.sh
#   Reads read-only controller creds from /opt/skynet-ops/secrets/omada.env (override: $OMADA_SECRET_FILE):
#     OMADA_HOST=10.10.50.25   OMADA_PORT=8043   OMADA_SNI=Omada
#     OMADA_USER=svc-ops       OMADA_PASS='...'  OMADA_CACERT=/opt/skynet-ops/certs/omada.crt
#   The account is a controller **Viewer** (read-only) — see docs/design/access-and-trust.md. This
#   collector NEVER mutates: every call is a GET except the login POST. Adopting/rebooting/config is T3.
# Degrades to exit 0 (no output file rewrite) when creds are absent — like every other collector.
#
# TLS pinning: the controller serves a self-signed cert whose SAN is `DNS:Omada` (not its IP), so we
# verify with --cacert against the pinned chain AND --resolve the SAN name to the host IP, never `-k`.
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
secret_file="${OMADA_SECRET_FILE:-/opt/skynet-ops/secrets/omada.env}"

# Creds may arrive in the environment (tests) or via the sops-nix secret file (production).
if [ -z "${OMADA_USER:-}" ]; then
  if [ -r "${secret_file}" ]; then
    # shellcheck disable=SC1090
    eval "$(cat "${secret_file}")"          # values with $/specials are single-quoted in the file
  else
    echo "no creds yet (${secret_file}) — collector idle until the Omada read account is provisioned" >&2
    exit 0
  fi
fi
: "${OMADA_HOST:?}" "${OMADA_USER:?}" "${OMADA_PASS:?}"
OMADA_PORT="${OMADA_PORT:-8043}"
OMADA_SNI="${OMADA_SNI:-Omada}"
: "${OMADA_CACERT:?set OMADA_CACERT to the pinned cert — run: scripts/pin-cert.sh ${OMADA_HOST} ${OMADA_PORT} /opt/skynet-ops/certs/omada.crt}"
[ -r "${OMADA_CACERT}" ] || { echo "OMADA_CACERT ${OMADA_CACERT} not readable (pins live in /opt/skynet-ops/certs, 0644)" >&2; exit 1; }

command -v jq >/dev/null || { echo "collect-network-gear: jq is required" >&2; exit 1; }

BASE="https://${OMADA_SNI}:${OMADA_PORT}"
jar="$(mktemp)"; trap 'rm -f "${jar}"' EXIT   # holds the session cookie — tmp, never committed
oc() { command curl -sS --max-time 20 --cacert "${OMADA_CACERT}" \
       --resolve "${OMADA_SNI}:${OMADA_PORT}:${OMADA_HOST}" "$@"; }

# The controller id (omadacId) prefixes every path; /api/info serves it unauthenticated.
info="$(oc "${BASE}/api/info")" || { echo "controller unreachable at ${OMADA_HOST}:${OMADA_PORT} — leaving inventory untouched" >&2; exit 0; }
OID="$(printf '%s' "${info}" | jq -r '.result.omadacId')"
VER="$(printf '%s' "${info}" | jq -r '.result.controllerVer')"
[ -n "${OID}" ] && [ "${OID}" != "null" ] || { echo "no omadacId from ${OMADA_HOST} — controller not configured?" >&2; exit 0; }
API="${BASE}/${OID}/api/v2"

# Login (the one POST). The response carries the CSRF token; the session rides the cookie jar.
login_body="$(jq -nc --arg u "${OMADA_USER}" --arg p "${OMADA_PASS}" '{username:$u,password:$p}')"
login="$(oc -c "${jar}" -X POST -H 'Content-Type: application/json' "${API}/login" -d "${login_body}")"
[ "$(printf '%s' "${login}" | jq -r '.errorCode')" = "0" ] || {
  echo "omada login failed: $(printf '%s' "${login}" | jq -r '.msg // "unknown"')" >&2; exit 1; }
TOK="$(printf '%s' "${login}" | jq -r '.result.token')"
auth=(-H "Csrf-Token: ${TOK}" -b "${jar}")
get() { oc "${auth[@]}" "${API}/$1"; }   # authenticated GET helper

# Sites the read account can see.
sites="$(get "sites?currentPage=1&currentPageSize=1000" | jq -c '[.result.data[]? | {id, name}]')"

# Devices per site; switch ports per switch. Assemble one entity-keyed row per device.
devices='[]'
while IFS= read -r site; do
  sid="$(printf '%s' "${site}" | jq -r '.id')"
  sname="$(printf '%s' "${site}" | jq -r '.name')"
  raw="$(get "sites/${sid}/devices")"
  # For each switch, fetch its ports and fold them in; APs/others carry ports:null.
  while IFS= read -r mac; do
    [ -n "${mac}" ] || continue
    ports="$(get "sites/${sid}/switches/${mac}/ports" \
             | jq -c '[.result[]? | {port, name, profile:.profileName,
                        link:(.portStatus.linkStatus // 0), speed:.portStatus.speed,
                        poe:.poe, disabled:.disable}]' 2>/dev/null || echo 'null')"
    raw="$(printf '%s' "${raw}" | jq --arg m "${mac}" --argjson p "${ports:-null}" \
           '(.result[] | select(.mac==$m)) |= (. + {_ports:$p})')"
  done < <(printf '%s' "${raw}" | jq -r '.result[]? | select(.type=="switch") | .mac')

  page="$(printf '%s' "${raw}" | jq --arg site "${sname}" '[.result[]? | {
      entity_id: ("net/" + ((.name // .mac)
                  | ascii_downcase | gsub("[^a-z0-9]+";"-") | gsub("(^-+|-+$)";""))),
      class: "net",
      site: $site,
      type, name, model, mac, ip,
      firmware: (.firmwareVersion // .version),
      needs_upgrade: (.needUpgrade // false),
      status: (.statusCategory // 0),          # 0 disconnected · 1 connected · 2 pending
      connected: ((.statusCategory // 0) == 1),
      uptime_s: (.uptimeLong // .uptime // 0),
      clients: (.clientNum // 0),
      poe: (if (.poeSupport // false) then {support:true, remain_w:(.poeRemain // null),
                total_w:(.poeTotalPower // null)} else {support:false} end),
      ports: ._ports
    }]')"
  devices="$(jq -s '.[0] + .[1]' <(printf '%s' "${devices}") <(printf '%s' "${page}"))"
done < <(printf '%s' "${sites}" | jq -c '.[]')

out="${REPO_DIR}/inventory/network-gear.json"
jq -n \
  --arg ts "$(date -Iseconds)" \
  --arg host "${OMADA_HOST}" --arg ver "${VER}" --arg oid "${OID}" \
  --argjson sites "${sites}" \
  --argjson devices "${devices}" \
  '{collected:$ts, controller:{host:$host, version:$ver, omadacId:$oid}, sites:$sites, devices:$devices}' \
  > "${out}"
echo "wrote ${out}  (devices=$(printf '%s' "${devices}" | jq 'length'), sites=$(printf '%s' "${sites}" | jq 'length'))"
