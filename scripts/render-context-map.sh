#!/usr/bin/env bash
# render-context-map.sh — compatibility entry for the packaged context-map renderer.
# TIER: T1 local read + generated output. USAGE: render-context-map.sh
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec "${REPO_DIR}/bin/skynet" render context --repo "${REPO_DIR}" "$@"
