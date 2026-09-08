#!/usr/bin/env bash
# collect-all.sh — run every T1 inventory collector once → refreshed inventory/ inputs.
# TIER: T1 read. USAGE: collect-all.sh (normally through bin/ops collect or scripts/nightly.sh).
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec "${REPO_DIR}/bin/skynet" collect all --repo "${REPO_DIR}" "$@"
