#!/usr/bin/env bash
# deploy-gate.sh — forward to packaged exact-generation health/DMZ route verifier -> report.
# Tier: T1 observation with bounded ephemeral DMZ probe. Usage: deploy-gate.sh <service> <revision>.
set -euo pipefail

if [ "$#" -ne 2 ]; then
  echo "usage: deploy-gate.sh <service> <full-revision>" >&2
  exit 2
fi
SERVICE="$1"
REVISION="$2"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOCKER_CONTEXT="${DOCKER_CONTEXT:-docker-dmz}"
SKYNET_BIN="${SKYNET_BIN:-${REPO_DIR}/bin/skynet}"
exec "${SKYNET_BIN}" verify deployment "${SERVICE}" "${REVISION}" \
  --repo "${REPO_DIR}" --context "${DOCKER_CONTEXT}"
