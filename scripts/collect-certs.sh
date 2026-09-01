#!/usr/bin/env bash
# collect-certs.sh — TLS certificate inventory (SKY-018 P5) → inventory/certs.json.
# TIER: T1 — probes reachable TLS endpoints read-only (openssl s_client), records issuer / SANs /
#   notAfter / days-left. No writes. Degrades per-endpoint (unreachable → recorded as such) and to an
#   empty inventory if openssl is missing.
# Scope: the infra endpoints the ops VM can reach on VLAN 90 (OPNsense, Omada, Proxmox, PBS,
#   Technitium). The apps-Caddy vhost certs (ACME via Cloudflare DNS-01) live at HOST_PROXY_APPS
#   (10.10.100.35), which VLAN 90 can't reach — those are noted pending (would need docker-dmz access).
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
command -v openssl >/dev/null || { echo "collect-certs: openssl not available — skipping" >&2; exit 0; }
command -v jq >/dev/null || { echo "collect-certs: jq is required" >&2; exit 1; }

# endpoints: "label host port sni" — sni matters for SNI-based vhosts / mismatched certs.
ENDPOINTS=(
  "opnsense           10.10.90.1   443    OPNsense.internal"
  "omada              10.10.50.25  8043   Omada"
  "proxmox-core       10.10.50.11  8006   -"
  "proxmox-network    10.10.50.10  8006   -"
  "pbs                10.10.20.40  8007   -"
  "technitium-core    10.10.70.51  53443  -"
  "technitium-network 10.10.70.50  53443  -"
)

now_epoch="$(date +%s)"
certs="[]"
for row in "${ENDPOINTS[@]}"; do
  # shellcheck disable=SC2086
  set -- ${row}; label="$1"; host="$2"; port="$3"; sni="$4"
  args=(-connect "${host}:${port}")
  [ "${sni}" != "-" ] && args+=(-servername "${sni}")
  leaf="$(timeout 8 openssl s_client "${args[@]}" </dev/null 2>/dev/null | openssl x509 2>/dev/null || true)"
  if [ -z "${leaf}" ]; then
    certs="$(jq -c --arg l "${label}" --arg h "${host}:${port}" '. + [{label:$l, endpoint:$h, reachable:false}]' <<<"${certs}")"
    continue
  fi
  issuer="$(printf '%s' "${leaf}" | openssl x509 -noout -issuer 2>/dev/null | sed 's/^issuer=//')"
  subject="$(printf '%s' "${leaf}" | openssl x509 -noout -subject 2>/dev/null | sed 's/^subject=//')"
  notafter="$(printf '%s' "${leaf}" | openssl x509 -noout -enddate 2>/dev/null | sed 's/^notAfter=//')"
  sans="$(printf '%s' "${leaf}" | openssl x509 -noout -ext subjectAltName 2>/dev/null | grep -oE '(DNS|IP Address):[^,]+' | sed 's/^DNS://; s/^IP Address://' | paste -sd, - || true)"
  exp_epoch="$(date -d "${notafter}" +%s 2>/dev/null || echo 0)"
  days_left=$(( exp_epoch > 0 ? (exp_epoch - now_epoch) / 86400 : -1 ))
  certs="$(jq -c --arg l "${label}" --arg h "${host}:${port}" --arg i "${issuer}" --arg s "${subject}" \
             --arg na "${notafter}" --arg sans "${sans}" --argjson dl "${days_left}" \
           '. + [{label:$l, endpoint:$h, reachable:true, issuer:$i, subject:$s, sans:($sans|split(",")), not_after:$na, days_left:$dl}]' <<<"${certs}")"
done

out="${REPO_DIR}/inventory/certs.json"
jq -n --arg ts "$(date -Iseconds)" --argjson certs "${certs}" \
  '{collected:$ts, source:"tls probe (openssl s_client)",
    counts:{probed:($certs|length), reachable:([$certs[]|select(.reachable)]|length)},
    certs:$certs}' > "${out}"
echo "wrote ${out} (probed=$(jq 'length' <<<"${certs}"), reachable=$(jq '[.[]|select(.reachable)]|length' <<<"${certs}"))"
