#!/usr/bin/env bash
# collect-opnsense.sh — T1 live read of OPNsense via its API → the CANONICAL firewall inventory.
# Writes TWO files:
#   inventory/firewall/firewall.json  — CONFIG (aliases/rules/reservations), the USER view, in the
#     schema the mirror parser used to emit, but now LIVE-sourced. This REPLACES the os-git-backup
#     mirror parse (scripts/collect-firewall.sh) as the inventory source — no more push lag.
#   inventory/opnsense.json           — LIVE STATE the mirror can't give (firmware, ARP, interfaces).
# The git mirror (skynet-opnsense config.xml) is retained as the DR / rebuild-from-git source (§2a),
# not parsed for inventory. Read-only: the svc-skynet-recon key carries "System: Deny config write",
# so the firewall refuses every write; this collector only GETs (+ the searchRule/search POSTs, reads).
# Degrades to exit 0 (no output rewrite) with no creds / unreachable — like every collector. (ADR 0006)
#
# TLS: the self-signed cert's SAN is `DNS:OPNsense.internal` — we DERIVE the SNI from the pinned cert
# and --resolve it to the host, so a stale OPN_SNI can't break it. Never -k.
#
# USER-VIEW FILTER: the live API returns OPNsense's built-in aliases too; the mirror never did. We drop
# them to keep the user view identical: names matching `^__.*_network` (auto interface aliases) or the
# named built-ins {bogons, bogonsv6, sshlockout, virusprot}. Rules use /filter/get (the 28 configured
# user rules) intersected with /searchRule (flat display fields) — internal rules are excluded for free.
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
secret_file="${OPNSENSE_SECRET_FILE:-/opt/skynet-ops/secrets/opnsense.env}"

if [ -z "${OPN_KEY:-}" ]; then
  if [ -r "${secret_file}" ]; then
    # shellcheck disable=SC1090
    eval "$(cat "${secret_file}")"        # KEY/SECRET single-quoted in the file ($/+ safe)
  else
    echo "no creds yet (${secret_file}) — collector idle until the recon key is provisioned" >&2
    exit 0
  fi
fi
: "${OPN_HOST:?}" "${OPN_KEY:?}" "${OPN_SECRET:?}"
OPN_PORT="${OPN_PORT:-443}"
: "${OPN_CACERT:?set OPN_CACERT to the pinned cert — run: scripts/pin-cert.sh ${OPN_HOST} ${OPN_PORT} /opt/skynet-ops/certs/opnsense.crt}"
[ -r "${OPN_CACERT}" ] || { echo "OPN_CACERT ${OPN_CACERT} not readable" >&2; exit 1; }
command -v jq >/dev/null || { echo "collect-opnsense: jq is required" >&2; exit 1; }

sni="$(openssl x509 -in "${OPN_CACERT}" -noout -ext subjectAltName 2>/dev/null \
        | grep -oE 'DNS:[^,]+' | head -1 | cut -d: -f2 | tr -d ' ')"
sni="${sni:-${OPN_SNI:-${OPN_HOST}}}"
oc()   { command curl -sS --max-time 25 --cacert "${OPN_CACERT}" \
         --resolve "${sni}:${OPN_PORT}:${OPN_HOST}" -u "${OPN_KEY}:${OPN_SECRET}" "$@"; }
base="https://${sni}:${OPN_PORT}"
get()  { oc "${base}/api/$1"; }
srch() { oc -X POST -H 'Content-Type: application/json' "${base}/api/$1" -d "${2:-{\"current\":1,\"rowCount\":2000}}"; }

fw="$(get core/firmware/status 2>/dev/null)" || { echo "OPNsense API unreachable at ${OPN_HOST}:${OPN_PORT} — leaving inventory untouched" >&2; exit 0; }
printf '%s' "${fw}" | jq -e . >/dev/null 2>&1 || { echo "OPNsense API returned no/invalid JSON — leaving inventory untouched" >&2; exit 0; }

# ── CONFIG (→ firewall.json), user view ───────────────────────────────────────────────────────────
# Aliases: drop the built-ins; type = the selected enum key; content = members joined with newlines
# (matching the mirror string), so the audit/renderer joins are unchanged.
aliases="$(get firewall/alias/get | jq -c '
  [ .alias.aliases.alias // {} | to_entries[]
    | select(.value.name | test("^__.*_network$|^(bogons|bogonsv6|sshlockout|virusprot)$") | not)
    | .value as $a
    | { name:$a.name,
        type:($a.type   | if type=="object" then ([to_entries[]|select(.value.selected==1)|.key][0] // "") else . end),
        content:($a.content | if type=="object" then ([to_entries[]|select(.value.selected==1)|.key]|join("\n")) else (.//"") end),
        description:($a.description // ""),
        enabled:($a.enabled // "1") } ]' 2>/dev/null || echo '[]')"

# Rules: the 28 configured user rules (filter/get) → their uuids + real sequence; flat fields from
# searchRule. Internal/auto rules are excluded because they aren't in filter/get.
seqmap="$(get firewall/filter/get | jq -c '[.filter.rules.rule // {} | to_entries[] | {uuid:.key, sequence:(.value.sequence // null)}]' 2>/dev/null || echo '[]')"
rules="$(srch firewall/filter/searchRule | jq -c --argjson sm "${seqmap}" '
  ($sm | map({(.uuid): .sequence}) | add // {}) as $seq
  | [ .rows[]? | select(.uuid as $u | $seq | has($u))
      | { sequence:($seq[.uuid]), action, protocol, interface:(.interface // null),
          source_net, destination_net, destination_port, description, uuid,
          enabled:((.enabled=="1") or (.enabled==1)) } ]' 2>/dev/null || echo '[]')"

# Reservations: dnsmasq static hosts — the same shape the mirror parsed from dnsmasq/hosts.
reservations="$(srch dnsmasq/settings/searchHost | jq -c '[.rows[]? | {host, domain, ip, hwaddr, client_id, descr, aliases, comments}]' 2>/dev/null || echo '[]')"

out_fw="${REPO_DIR}/inventory/firewall/firewall.json"
mkdir -p "$(dirname "${out_fw}")"
jq -n --arg ts "$(date -Iseconds)" \
  --argjson aliases "${aliases:-[]}" --argjson rules "${rules:-[]}" --argjson reservations "${reservations:-[]}" \
  '{collected:$ts, source:"opnsense-api (live, T1 read-only; user view)",
    counts:{aliases:($aliases|length), rules:($rules|length), reservations:($reservations|length)},
    aliases:$aliases, rules:$rules, reservations:$reservations}' > "${out_fw}"

# ── LIVE STATE (→ opnsense.json) — what the mirror cannot give ─────────────────────────────────────
# ARP via searchArp (richer than getArp: carries per-entry expiry, so freshness is visible).
arp="$(srch diagnostics/interface/searchArp | jq -c '[.rows[]? | {ip,mac,hostname,intf,intf_description,manufacturer,permanent,expired,expires}]' 2>/dev/null || echo '[]')"

# ── PRESENCE probe — distinguish "idle (up, ARP aged out)" from "down" for ARP-silent hosts ────────
# ARP present ⇒ live, no probe. For ARP-silent declared hosts, ICMP-ping from the ops VM (fast: 1s
# timeout, parallel). This is DEFINITIVE once the "ops → NET_SKYNET ICMP" floating rule is in (the
# sees-all liveness grant); before it, ICMP is firewall-dropped so a silent host reads live:false in
# 1s (not the 12s the old TCP-port-guess burned). OPNsense's own ping API has no runnable verb in 26.7
# (get/set stub; start/run/results 404), so an OPNsense-side ping isn't an option.
arp_ips="$(printf '%s' "${arp}" | jq -r '.[].ip' 2>/dev/null | sort -u)"
host_ips="$(printf '%s' "${aliases}" | jq -r '.[] | select(.type=="host") | .content' 2>/dev/null | tr ' \n' '\n\n' | grep -E '^10\.10\.[0-9]+\.[0-9]+$' | sort -u)"
silent_ips="$(comm -23 <(printf '%s\n' "${host_ips}") <(printf '%s\n' "${arp_ips}"))"
# ping the silent set in parallel; collect the ones that answer.
pinged_up=""
[ -n "${silent_ips}" ] && pinged_up="$(printf '%s\n' "${silent_ips}" | grep -E '^10\.' \
  | xargs -r -P16 -I{} sh -c 'ping -c1 -W1 "{}" >/dev/null 2>&1 && echo "{}"' 2>/dev/null | sort -u)"
presence="$(jq -n --argjson host "$(printf '%s\n' "${host_ips}" | grep -E '^10\.' | jq -R . | jq -s .)" \
  --argjson arp "$(printf '%s\n' "${arp_ips}" | grep -E '^10\.' | jq -R . | jq -s .)" \
  --argjson up "$(printf '%s\n' "${pinged_up}" | grep -E '^10\.' | jq -R . | jq -s . 2>/dev/null || echo '[]')" '
  [ $host[] | . as $ip
    | if ($arp|index($ip)) then {ip:$ip, live:true, via:"arp"}
      elif ($up|index($ip)) then {ip:$ip, live:true, via:"icmp"}
      else {ip:$ip, live:false, via:"no-arp,no-icmp"} end ]' 2>/dev/null || echo '[]')"

ifaces="$(get interfaces/overview/interfacesInfo | jq -c '(.rows // .) | if type=="array" then [.[]|{device,description,status,enabled,identifier}] else [] end' 2>/dev/null || echo '[]')"
out_live="${REPO_DIR}/inventory/opnsense.json"
jq -n --arg ts "$(date -Iseconds)" --arg host "${OPN_HOST}" \
  --argjson fw "$(printf '%s' "${fw}" | jq -c '{status, product:(.product_version // .product_id // null), needs_upgrade:((.status//"")=="update")}')" \
  --argjson arp "${arp:-[]}" --argjson interfaces "${ifaces:-[]}" --argjson presence "${presence:-[]}" \
  '{collected:$ts, source:"opnsense-api (live read-only)", host:$host, firmware:$fw,
    counts:{arp:($arp|length), interfaces:($interfaces|length),
            live:([$presence[]|select(.live)]|length), silent:([$presence[]|select(.live|not)]|length)},
    arp:$arp, interfaces:$interfaces, presence:$presence}' > "${out_live}"

echo "wrote ${out_fw} (aliases=$(printf '%s' "${aliases}" | jq 'length'), rules=$(printf '%s' "${rules}" | jq 'length'), reservations=$(printf '%s' "${reservations}" | jq 'length'))"
echo "wrote ${out_live} (arp=$(printf '%s' "${arp}" | jq 'length'), interfaces=$(printf '%s' "${ifaces}" | jq 'length'))"
