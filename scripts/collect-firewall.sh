#!/usr/bin/env bash
# collect-firewall.sh — forward offline OPNsense config.xml parsing (DR rebuild) to the packaged command.
# TIER: T1 offline parse. USAGE: collect-firewall.sh [path-to-config.xml].
# This is the DR/offline parser: rebuild inventory/firewall/firewall.json from the git-mirrored
# config.xml when the live API is unreachable. `scripts/collect-opnsense.sh` is the live T1 collector.
# The parser never pulls — refresh the skynet-opnsense mirror yourself first (as the mirror owner,
# not root). An offline parse writes no freshness marker and never satisfies the live-freshness contract.
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
config="${1:-/opt/skynet-ops/mirror/skynet-opnsense/config.xml}"
exec "${REPO_DIR}/bin/skynet" collect firewall --config "${config}" \
  --output "${REPO_DIR}/inventory/firewall/firewall.json"
