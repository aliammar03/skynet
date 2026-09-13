#!/usr/bin/env bash
# audit-entities.sh — temporary compatibility entry for the packaged entity audit.
# TIER: T1 — reads authored repository data and committed inventory only.
# bin/ops and check-invariants retain this name until their later caller-cleanup phase.
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}" \
  exec python3 -m skynet.entities audit --repo "${REPO_DIR}" "$@"
