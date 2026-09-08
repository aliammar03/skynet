#!/usr/bin/env bash
# collect-proxmox-acl.sh — forward T1 operate-token ACL observations to the packaged command.
# TIER: T1 read. USAGE: collect-proxmox-acl.sh <core|network>.
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
node="${1:?usage: collect-proxmox-acl.sh <core|network>}"
case "${node}" in
  core|network) exec "${REPO_DIR}/bin/skynet" collect proxmox-acl "${node}" \
    --output "${REPO_DIR}/inventory/proxmox-${node}-acl.json" ;;
  *) echo 'usage: collect-proxmox-acl.sh <core|network>' >&2; exit 2 ;;
esac
