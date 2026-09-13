#!/usr/bin/env bash
# render-runbook-catalog.sh — compatibility entry for the packaged runbook catalog renderer.
# TIER: T1 local read + generated catalog output. USAGE: render-runbook-catalog.sh
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_DIR}"
args=(render runbook-catalog --repo "${REPO_DIR}")
[ -z "${PAGE:-}" ] || args+=(--output "${PAGE}")
exec "${REPO_DIR}/bin/skynet" "${args[@]}" "$@"
