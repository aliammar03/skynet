#!/usr/bin/env bash
# collect-dns.sh — forward Technitium DNS zone collection to the packaged Python command.
# TIER: T1 read. USAGE: collect-dns.sh [skynet collect dns options]; reads DNS credentials through it.
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec "${REPO_DIR}/bin/skynet" collect dns --output "${REPO_DIR}/inventory/dns-zones.json" "$@"
