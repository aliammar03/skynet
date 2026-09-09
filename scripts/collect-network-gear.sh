#!/usr/bin/env bash
# collect-network-gear.sh — forward the established Omada caller to the Python collector → inventory/network-gear.json
# Tier: T1 read-only. Usage: collect-network-gear.sh; forwards OMADA_SECRET_FILE when set.
# This compatibility shim remains for demonstrated callers; SKY-025 P22 owns its removal.
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
args=(collect omada --output "${REPO_DIR}/inventory/network-gear.json")
if [ -n "${OMADA_SECRET_FILE:-}" ]; then
  args+=(--credentials-file "${OMADA_SECRET_FILE}")
fi
exec "${REPO_DIR}/bin/skynet" "${args[@]}"
