#!/usr/bin/env bash
# gitops-deploy.sh — forward to packaged generation deployment -> verified service outcome.
# Tier: supervised T2. Usage: gitops-deploy.sh <service> [skynet deploy service options].
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKYNET_BIN="${SKYNET_BIN:-${REPO_DIR}/bin/skynet}"
exec "${SKYNET_BIN}" deploy service --repo "${REPO_DIR}" "$@"
