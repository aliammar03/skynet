#!/usr/bin/env bash
# collect-routes.sh — L2 route inventory (SKY-018 P5). Static-parse the committed Caddyfiles under
#   compose/ into inventory/routes.json: vhost -> front door -> backend ENTITY -> auth mode.
# TIER: T1 — reads compose/ (git), resolves backends via the compose ipv4_address map + entity.sh.
#   No live access, no writes. This is the VHOST class's only real source: app vhosts resolve through
#   the single *.aliammar.net wildcard, so DNS knows one name where the Caddyfile declares nine.
# The vhost->backend edge is NOT derivable by hostname (obsidian -> obsidian-livesync, speed ->
#   librespeed), but it IS derivable by the backend IP the Caddyfile targets: every app declares its
#   macvlan ipv4_address in its compose.yaml, so backend-IP -> svc is a lookup; a non-service backend
#   (Authentik) resolves via entity.sh (IP -> VMID -> guest).
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_DIR}"
# shellcheck source=scripts/entity.sh
source "${REPO_DIR}/scripts/entity.sh"
command -v jq >/dev/null || { echo "collect-routes: jq is required" >&2; exit 1; }

# ── backend-IP -> entity map: compose macvlan ipv4_address -> svc/<project> ───────────────────────
declare -A IP2SVC
for d in compose/*/; do
  proj="$(basename "${d}")"
  ip="$(grep -oE 'ipv4_address:[[:space:]]*10\.10\.[0-9.]+' "${d}compose.yaml" 2>/dev/null | grep -oE '10\.10\.[0-9.]+' | head -1 || true)"
  if [ -n "${ip}" ]; then IP2SVC["${ip}"]="${proj}"; fi
done
# guest-IP -> real entity id, from the collected guests (each guest's IP derived from its VMID via
# entity.sh — the SAME derivation the audit uses). This resolves a backend to the ACTUAL guest
# (name + real VMID: guest/authentik-identity-837), not an IP-derived guess (which picks the wrong
# VMID form for legacy guests, e.g. 8037 vs 837).
declare -A GUEST_IP
while IFS=$'\t' read -r vmid name; do
  [ -n "${vmid}" ] || continue
  gip="$(vmid_to_ip "${vmid}" 2>/dev/null || true)"
  if [ -n "${gip}" ]; then GUEST_IP["${gip}"]="$(guest_id "${vmid}" "${name}")"; fi
done < <(jq -r '.resources[]? | select(.type=="qemu" or .type=="lxc") | "\(.vmid)\t\(.name)"' inventory/proxmox-*.json 2>/dev/null | sort -u)

# resolve a backend host:port to an entity id: compose svc map, then the real guest map, else raw host.
resolve_backend() {
  local ip="${1%%:*}"
  if [ -n "${IP2SVC[${ip}]:-}" ]; then echo "svc/${IP2SVC[${ip}]}"; return; fi
  if [ -n "${GUEST_IP[${ip}]:-}" ]; then echo "${GUEST_IP[${ip}]}"; return; fi
  echo "host:${ip}"   # unresolved — a raw host, flagged for a human
}

# ── parse a Caddyfile → TSV: vhost \t backend_addr \t forward_auth(yes/no) ────────────────────────
parse_caddy() {
  awk '
    function is_addr(s){ return (s ~ /^[0-9A-Za-z][0-9A-Za-z._-]*:[0-9]+$/) }
    /^[A-Za-z0-9.*_-]+\.aliammar\.net[[:space:]]*\{/ && depth==0 {
      vhost=$1; sub(/[[:space:]]*\{.*/,"",vhost); depth=1; backend=""; fauth="no"; next
    }
    depth>0 {
      # the catch-all backend is a reverse_proxy whose FIRST arg is the address; skip path-scoped
      # ones (e.g. `reverse_proxy /outpost.goauthentik.io/* <authentik>`) — those are auth plumbing.
      if ($1=="reverse_proxy" && is_addr($2)) { backend=$2 }
      if ($1=="forward_auth")  fauth="yes"
      n=gsub(/\{/,"&"); m=gsub(/\}/,"&"); depth+=n-m
      if (depth<=0){ if(vhost!="") print vhost"\t"backend"\t"fauth; depth=0; vhost="" }
    }
  ' "$1"
}

routes="[]"
# The apps Caddy is the front door for compose/caddy-apps/Caddyfile (svc/caddy-apps, HOST_PROXY_APPS).
caddy="compose/caddy-apps/Caddyfile"
if [ -r "${caddy}" ]; then
  while IFS=$'\t' read -r vhost backend fauth; do
    [ -n "${vhost}" ] || continue
    entity="—"; auth="own-auth/plain"
    if [ -n "${backend}" ]; then
      entity="$(resolve_backend "${backend}")"
      # Authentik backend with no forward_auth on this vhost = the identity endpoint itself.
      case "${entity}" in guest/authentik-*) [ "${fauth}" = no ] && auth="identity (authentik)";; esac
    fi
    [ "${fauth}" = yes ] && auth="forward_auth (authentik)"
    routes="$(jq -c --arg v "${vhost}" --arg fd "svc/caddy-apps" --arg b "${backend:-}" \
                    --arg e "${entity}" --arg a "${auth}" \
              '. + [{vhost:$v, front_door:$fd, front_door_alias:"HOST_PROXY_APPS", backend:$b, backend_entity:$e, auth:$a}]' \
              <<<"${routes}")"
  done < <(parse_caddy "${caddy}")
fi

out="${REPO_DIR}/inventory/routes.json"
jq -n --arg ts "$(date -Iseconds)" --argjson routes "${routes}" \
  '{collected:$ts, source:"caddyfile static parse (compose/)", counts:{routes:($routes|length)}, routes:$routes}' > "${out}"
echo "wrote ${out} (routes=$(jq 'length' <<<"${routes}"))"
