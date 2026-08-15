#!/usr/bin/env bash
# collect-proxmox.sh — T1 read-only snapshot of a Proxmox node → inventory/proxmox-<node>.json
# USAGE: collect-proxmox.sh <core|network>
#   Reads API creds from /opt/skynet-ops/secrets/proxmox-<node>.env:
#     PVE_HOST=10.10.50.10   PVE_TOKEN='svc-ops@pve!readonly=<uuid>'
# Never mutates remote state.
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
node="${1:?usage: collect-proxmox.sh <core|network>}"
secret="/opt/skynet-ops/secrets/proxmox-${node}.env"

if ! sudo test -f "${secret}"; then
  echo "no creds yet (${secret}) — collector idle until A2 provisions the readonly token" >&2
  exit 0
fi
# shellcheck disable=SC1090
eval "$(sudo cat "${secret}")"
: "${PVE_HOST:?}" "${PVE_TOKEN:?}"

api() { curl -sSf --max-time 15 -H "Authorization: PVEAPIToken=${PVE_TOKEN}" \
        "https://${PVE_HOST}:8006/api2/json/$1"; }

out="${REPO_DIR}/inventory/proxmox-${node}.json"
jq -n \
  --argjson nodes "$(api nodes | jq '.data')" \
  --argjson resources "$(api cluster/resources | jq '.data')" \
  --argjson pools "$(api pools | jq '.data')" \
  --arg node "${node}" --arg ts "$(date -Iseconds)" \
  '{node:$node, collected:$ts, nodes:$nodes, resources:$resources, pools:$pools}' > "${out}"
echo "wrote ${out}"
