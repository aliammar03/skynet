#!/usr/bin/env bash
# nightly-automerge.sh — fail-closed compatibility entry while nightly auto-merge is suspended.
# ADR 0004 records the former generated-only capability; AGENTS.md §3 keeps the auto-approve list
# empty, so older installed nightly callers must leave the PR open. SKY-025 Phase 11 removes this entry.
set -euo pipefail

echo "automerge: suspended (AGENTS.md §3) — PR left open for human merge"
