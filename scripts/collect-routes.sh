#!/usr/bin/env bash
# collect-routes.sh — compatibility forwarder for Python static Caddy route observations.
# TIER: T1 — reads this checkout only. P22 owns removal.
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec "${REPO_DIR}/bin/skynet" collect routes --repo "${REPO_DIR}" --output "${REPO_DIR}/inventory/routes.json"
