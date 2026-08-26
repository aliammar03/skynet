#!/usr/bin/env bash
# collect-proxmox.sh — T1 read-only snapshot of a Proxmox node → inventory/proxmox-<node>.json
# USAGE: collect-proxmox.sh <core|network>
#   Reads API creds from /opt/skynet-ops/secrets/proxmox-<node>.env:
#     PVE_HOST=10.10.50.10   PVE_TOKEN='svc-ops@pve!readonly=<uuid>'
# Never mutates remote state.
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
node="${1:?usage: collect-proxmox.sh <core|network>}"
secret_file="/opt/skynet-ops/secrets/proxmox-${node}.env"

if ! { test -e "${secret_file}" 2>/dev/null || sudo -n test -f "${secret_file}" 2>/dev/null; }; then
  echo "no creds yet (${secret_file}) — collector idle until A2 provisions the readonly token" >&2
  exit 0
fi
# shellcheck disable=SC1090
eval "$(cat "${secret_file}" 2>/dev/null || sudo -n cat "${secret_file}")"
: "${PVE_HOST:?}" "${PVE_TOKEN:?}"
: "${PVE_CACERT:?set PVE_CACERT in ${secret_file} to a pinned cert — run: scripts/pin-cert.sh ${PVE_HOST:-<host>} 8006 /opt/skynet-ops/certs/proxmox-${node}.crt}"
[ -r "${PVE_CACERT}" ] || { echo "PVE_CACERT ${PVE_CACERT} not readable (pins live in /opt/skynet-ops/certs, 0644)" >&2; exit 1; }

api() { curl -sSf --max-time 15 --cacert "${PVE_CACERT}" -H "Authorization: PVEAPIToken=${PVE_TOKEN}" \
        "https://${PVE_HOST}:8006/api2/json/$1"; }

# Pool membership: /pools lists poolids, but only /pools/{id} carries the member list —
# and reading it needs Pool.Audit ON that pool path (svc-ops@pve, PVEAuditor at /pool/<id>).
# The invariants gate (SKY-011) needs membership to assert excluded guests never join a pool.
# Fetch each pool's detail and project members to STABLE identity fields (the volatile stats
# already live in `resources`). Degrade to members:null — never [] — when a pool can't be
# audited, so the gate can tell "unknown" (grant missing) apart from "empty" (genuinely no members).
pool_detail() {
  local pid="$1" data
  if data="$(api "pools/${pid}" 2>/dev/null)"; then
    printf '%s' "${data}" | jq --arg pid "${pid}" \
      '.data | {poolid:$pid, comment:(.comment // null),
                members:[ (.members // [])[] | {id, type, vmid, node} ]}'
  else
    jq -n --arg pid "${pid}" '{poolid:$pid, comment:null, members:null}'
  fi
}
pools="$(api pools | jq -r '.data[].poolid' | while IFS= read -r pid; do
           [ -n "${pid}" ] || continue
           pool_detail "${pid}"
         done | jq -s '.')"

out="${REPO_DIR}/inventory/proxmox-${node}.json"
jq -n \
  --argjson nodes "$(api nodes | jq '.data')" \
  --argjson resources "$(api cluster/resources | jq '.data')" \
  --argjson pools "${pools}" \
  --arg node "${node}" --arg ts "$(date -Iseconds)" \
  '{node:$node, collected:$ts, nodes:$nodes, resources:$resources, pools:$pools}' > "${out}"
echo "wrote ${out}"
