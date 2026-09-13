#!/usr/bin/env bash
# render-digest.sh — compatibility entry for the packaged recent-activity renderer.
# TIER: T1 local read + generated output. USAGE: render-digest.sh
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_DIR}"
args=(render digest --repo "${REPO_DIR}")
[ -z "${PAGE:-}" ] || args+=(--output "${PAGE}")
[ -z "${JDIR:-}" ] || args+=(--journal "${JDIR}")
exec "${REPO_DIR}/bin/skynet" "${args[@]}" "$@"
