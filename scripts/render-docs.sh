#!/usr/bin/env bash
# render-docs.sh — compatibility entry for the packaged factual Markdown renderer.
# TIER: T1 local read + generated output. USAGE: render-docs.sh
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec "${REPO_DIR}/bin/skynet" render docs --repo "${REPO_DIR}" "$@"
