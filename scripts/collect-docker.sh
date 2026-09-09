#!/usr/bin/env bash
# collect-docker.sh — forward Docker inventory collection to the packaged Python command.
# TIER: T1 read. USAGE: collect-docker.sh [host-label] [docker-context].
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
label="${1:-docker-dmz}"
context="${2:-${label}}"
exec "${REPO_DIR}/bin/skynet" collect docker "${label}" --context "${context}" \
  --output "${REPO_DIR}/inventory/docker-${label}.json"
