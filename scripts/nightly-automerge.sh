#!/usr/bin/env bash
# nightly-automerge.sh — fail-closed compatibility entry during the SKY-025 test embargo.
# ADR 0004 records the former generated-only capability. With GitHub CI absent, no PR has the
# evidence required for unattended merge, so older installed nightly callers must leave it open.
set -euo pipefail

echo "automerge: suspended during SKY-025 test embargo — PR left open for human merge"
