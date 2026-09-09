#!/usr/bin/env bash
# collect-certs.sh — compatibility forwarder for Python TLS observations.
# TIER: T1 — an unauthenticated probe of the fixed ops-VLAN endpoint list. P22 owns removal.
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec "${REPO_DIR}/bin/skynet" collect certs --output "${REPO_DIR}/inventory/certs.json"
