#!/usr/bin/env bash
# collect-opnsense.sh — T1 live read of OPNsense via its API → inventory/opnsense.json (SKY-020 P1).
# USAGE: collect-opnsense.sh
#   Reads the READ-ONLY recon credential from /opt/skynet-ops/secrets/opnsense.env (override:
#   $OPNSENSE_SECRET_FILE):  OPN_HOST=10.10.90.1  OPN_PORT=443  OPN_USER=svc-skynet-recon
#   OPN_KEY=...  OPN_SECRET=...  OPN_CACERT=/opt/skynet-ops/certs/opnsense.crt  [OPN_SNI=...]
#   The account carries "System: Deny config write" (user-config-readonly): the API refuses every
#   write, so this collector is read-only by the firewall's own enforcement (ADR 0006). It only GETs.
# Live truth the git mirror can't give without lag: current aliases/rules, ARP neighbours, interface
# state, firmware currency. The mirror (collect-firewall.sh) stays the rebuild-from-git config source.
# Degrades to exit 0 (no output rewrite) with no creds / unreachable — like every collector.
#
# TLS: the self-signed cert's SAN is `DNS:OPNsense.internal` (not the IP / not a vanity name), so we
# verify with --cacert and --resolve that SAN name to the host — derived from the pinned cert itself,
# so a stale OPN_SNI in the secret can't break it. Never -k.
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
secret_file="${OPNSENSE_SECRET_FILE:-/opt/skynet-ops/secrets/opnsense.env}"

if [ -z "${OPN_KEY:-}" ]; then
  if [ -r "${secret_file}" ]; then
    # shellcheck disable=SC1090
    eval "$(cat "${secret_file}")"        # KEY/SECRET are single-quoted in the file ($/+ safe)
  else
    echo "no creds yet (${secret_file}) — collector idle until the recon key is provisioned" >&2
    exit 0
  fi
fi
: "${OPN_HOST:?}" "${OPN_KEY:?}" "${OPN_SECRET:?}"
OPN_PORT="${OPN_PORT:-443}"
: "${OPN_CACERT:?set OPN_CACERT to the pinned cert — run: scripts/pin-cert.sh ${OPN_HOST} ${OPN_PORT} /opt/skynet-ops/certs/opnsense.crt}"
[ -r "${OPN_CACERT}" ] || { echo "OPN_CACERT ${OPN_CACERT} not readable (pins live in /opt/skynet-ops/certs, 0644)" >&2; exit 1; }
command -v jq >/dev/null || { echo "collect-opnsense: jq is required" >&2; exit 1; }

# Derive the TLS SNI from the pinned cert's first SAN (self-correcting); fall back to OPN_SNI / host.
sni="$(openssl x509 -in "${OPN_CACERT}" -noout -ext subjectAltName 2>/dev/null \
        | grep -oE 'DNS:[^,]+' | head -1 | cut -d: -f2 | tr -d ' ')"
sni="${sni:-${OPN_SNI:-${OPN_HOST}}}"

oc() { command curl -sS --max-time 20 --cacert "${OPN_CACERT}" \
       --resolve "${sni}:${OPN_PORT}:${OPN_HOST}" -u "${OPN_KEY}:${OPN_SECRET}" "$@"; }
base="https://${sni}:${OPN_PORT}"
get()  { oc "${base}/api/$1"; }                                   # read
post() { oc -X POST -H 'Content-Type: application/json' "${base}/api/$1" -d "$2"; }

# Reachability / auth check up front — degrade cleanly if the firewall isn't reachable or the key is bad.
fw="$(get core/firmware/status 2>/dev/null)" || { echo "OPNsense API unreachable at ${OPN_HOST}:${OPN_PORT} — leaving inventory untouched" >&2; exit 0; }
[ -n "${fw}" ] && printf '%s' "${fw}" | jq -e . >/dev/null 2>&1 || { echo "OPNsense API returned no/invalid JSON (key wrong, or write-only path?) — leaving inventory untouched" >&2; exit 0; }

# Aliases (name/type/content/description). The API groups them under .alias.aliases.alias keyed by uuid.
aliases="$(get firewall/alias/get | jq -c '[.alias.aliases.alias // {} | to_entries[]
    | .value as $a | {uuid:.key, name:$a.name, type:($a.type|if type=="object" then (.|to_entries[]|select(.value.selected==1)|.key) else . end),
                      description:$a.description,
                      content:($a.content // {} | if type=="object" then [to_entries[]|.key] else (.|tostring|split("\n")) end)}]' 2>/dev/null || echo '[]')"

# Rules (live, includes automatic). Keep the load-bearing fields; flag automatic vs user rules.
rules="$(post firewall/filter/searchRule '{"current":1,"rowCount":2000}' \
    | jq -c '[.rows[]? | {uuid, enabled:(.enabled=="1" or .enabled==1), automatic:(.is_automatic=="1" or .is_automatic==1),
                          action, interface:(.interface // .["%interface"] // null),
                          source_net, destination_net, destination_port, protocol, description}]' 2>/dev/null || echo '[]')"

# ARP / neighbour table — live, the mirror can't give this.
arp="$(get diagnostics/interface/getArp | jq -c 'if type=="array" then [.[] | {ip, mac, hostname, intf, intf_description, manufacturer, permanent}] else [] end' 2>/dev/null || echo '[]')"

# Interfaces overview (selected fields; shape varies by version — keep it defensive).
ifaces="$(get interfaces/overview/interfacesInfo | jq -c '(.rows // .) | if type=="array" then [.[] | {device, description, status, enabled, identifier}] else [] end' 2>/dev/null || echo '[]')"

out="${REPO_DIR}/inventory/opnsense.json"
jq -n \
  --arg ts "$(date -Iseconds)" \
  --arg host "${OPN_HOST}" \
  --argjson fw "$(printf '%s' "${fw}" | jq -c '{status, product:(.product_version // .product_id // null), needs_upgrade:((.status//"")=="update")}')" \
  --argjson aliases "${aliases:-[]}" \
  --argjson rules "${rules:-[]}" \
  --argjson arp "${arp:-[]}" \
  --argjson interfaces "${ifaces:-[]}" \
  '{collected:$ts, source:"opnsense-api (read-only)", host:$host, firmware:$fw,
    counts:{aliases:($aliases|length), rules:($rules|length), arp:($arp|length), interfaces:($interfaces|length)},
    aliases:$aliases, rules:$rules, arp:$arp, interfaces:$interfaces}' > "${out}"
echo "wrote ${out}  (aliases=$(printf '%s' "${aliases}" | jq 'length'), rules=$(printf '%s' "${rules}" | jq 'length'), arp=$(printf '%s' "${arp}" | jq 'length'))"
