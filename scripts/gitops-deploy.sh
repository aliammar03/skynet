#!/usr/bin/env bash
# Compatibility entry point; the packaged command owns deployment behavior.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec "${REPO_ROOT}/bin/skynet" deploy service --repo "${REPO_ROOT}" "$@"
