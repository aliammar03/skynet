#!/usr/bin/env bash
# gitops-rollback.sh — forward to packaged retained-generation rollback -> status or verified activation.
# Tier: supervised T2 with --apply. Usage: gitops-rollback.sh <service> [--to <revision>] [--apply].
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKYNET_BIN="${SKYNET_BIN:-${REPO_DIR}/bin/skynet}"
exec "${SKYNET_BIN}" rollback service --repo "${REPO_DIR}" "$@"
