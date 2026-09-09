#!/usr/bin/env bash
# recon.sh — compatibility forwarder for bounded Python T1 reconnaissance. P22 owns removal.
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec "${REPO_DIR}/bin/skynet" recon "$@"
