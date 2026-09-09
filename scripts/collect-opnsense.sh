#!/usr/bin/env bash
# collect-opnsense.sh — forward live OPNsense firewall+state collection to the packaged Python command.
# TIER: T1 read (live API, read-only). USAGE: collect-opnsense.sh [skynet collect opnsense options].
# Writes inventory/firewall/firewall.json (user-view config) and inventory/opnsense.json (live state).
# The git mirror (collect-firewall.sh) remains the offline DR/rebuild parser.
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec "${REPO_DIR}/bin/skynet" collect opnsense \
  --firewall-output "${REPO_DIR}/inventory/firewall/firewall.json" \
  --state-output "${REPO_DIR}/inventory/opnsense.json" "$@"
