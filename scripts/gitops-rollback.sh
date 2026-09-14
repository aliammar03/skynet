#!/usr/bin/env bash
# Compatibility entry point; the packaged command owns rollback behavior.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec "${REPO_ROOT}/bin/skynet" rollback service --repo "${REPO_ROOT}" "$@"
