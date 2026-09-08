#!/usr/bin/env bash
# collect-proxmox.sh — forward a T1 Proxmox observation request → inventory/proxmox-<node>.json.
# TIER: T1 read. USAGE: collect-proxmox.sh <core|network>; credentials stay with the packaged command.
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
node="${1:?usage: collect-proxmox.sh <core|network>}"

case "${node}" in
  core|network)
    exec "${REPO_DIR}/bin/skynet" collect proxmox "${node}" \
      --output "${REPO_DIR}/inventory/proxmox-${node}.json"
    ;;
  *) echo 'usage: collect-proxmox.sh <core|network>' >&2; exit 2 ;;
esac
