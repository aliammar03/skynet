#!/usr/bin/env bash
# build-db.sh — compatibility launcher for the Python disposable inventory cache.
# TIER: T1 — reads repository inventory/lab facts and writes only .cache/inventory.db.
# USAGE: build-db.sh            # (re)build .cache/inventory.db
#        build-db.sh --help     # Python module options
# The schema/build logic lives in src/skynet/cache.py; this entry remains for direct historical
# rebuilds and existing runbooks while callers migrate to the packaged command.
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}" \
  exec python3 -m skynet.cache --repo "${REPO_DIR}" "$@"
