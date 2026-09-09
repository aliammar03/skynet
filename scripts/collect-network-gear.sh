#!/usr/bin/env bash
# collect-network-gear.sh — forward the established Omada caller to the Python collector → inventory/network-gear.json
# Tier: T1 read-only. Usage: collect-network-gear.sh; forwards OMADA_SECRET_FILE when set.
# This compatibility shim remains for demonstrated callers; SKY-025 P22 owns its removal.
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
credentials_file="${OMADA_SECRET_FILE:-/opt/skynet-ops/secrets/omada.env}"
# Keep the documented unavailable result observable from shell-only callers (including the
# deterministic identity gate) before the Nix-backed Python entrypoint is needed.
if [ ! -r "${credentials_file}" ]; then
  echo "network-gear: unavailable → ${REPO_DIR}/inventory/network-gear.json" >&2
  echo "credentials unavailable; refresh failed; any retained snapshot is previous evidence" >&2
  exit 3
fi
args=(collect omada --output "${REPO_DIR}/inventory/network-gear.json")
if [ -n "${OMADA_SECRET_FILE:-}" ]; then
  args+=(--credentials-file "${OMADA_SECRET_FILE}")
fi
exec "${REPO_DIR}/bin/skynet" "${args[@]}"
