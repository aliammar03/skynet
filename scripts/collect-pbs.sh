#!/usr/bin/env bash
# collect-pbs.sh — forward documented PBS inventory collection to the packaged Python command.
# TIER: T1 read. USAGE: collect-pbs.sh [skynet collect pbs options]; reads PBS credentials through it.
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec "${REPO_DIR}/bin/skynet" collect pbs --output "${REPO_DIR}/inventory/pbs.json" "$@"
