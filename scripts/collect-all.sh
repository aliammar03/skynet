#!/usr/bin/env bash
# collect-all.sh — run every T1 inventory collector once → refreshed inventory/ inputs.
# TIER: T1 read. USAGE: collect-all.sh (normally through bin/ops collect or scripts/nightly.sh).
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_DIR}"

failed=0
collect() {
  local name="$1"; shift
  if "$@"; then
    printf 'collect: %s OK\n' "${name}"
  else
    printf 'collect: %s FAILED; continuing with remaining T1 collectors\n' "${name}" >&2
    failed=1
  fi
}

printf '== refreshing inventory ==\n'
collect proxmox-core    ./scripts/collect-proxmox.sh core
collect proxmox-network ./scripts/collect-proxmox.sh network
collect proxmox-acl-core    ./scripts/collect-proxmox-acl.sh core
collect proxmox-acl-network ./scripts/collect-proxmox-acl.sh network
collect pbs           ./scripts/collect-pbs.sh
collect docker-dmz    ./scripts/collect-docker.sh docker-dmz
collect dns           ./scripts/collect-dns.sh
collect opnsense      ./scripts/collect-opnsense.sh
collect network-gear  ./scripts/collect-network-gear.sh
collect routes        ./scripts/collect-routes.sh
collect certs         ./scripts/collect-certs.sh

exit "${failed}"
