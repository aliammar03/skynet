#!/usr/bin/env bash
# deploy-gate.sh — compatibility forwarder for the packaged, report-only verifier.
# TIER: T2 PR-gated verification; the route probe has a bounded ephemeral container/cache side effect.
#
# Current caller: scripts/gitops-deploy.sh <service> <full-deploy-commit>. The Python verifier
# owns Arcane/Docker/ingress observations and never invokes rollback or mutates Git/runtime state.
# Keep this shim until the P22 shell-retirement pass removes the old command name.
#
# USAGE:
#   deploy-gate.sh <service> <full-deploy-commit>
# OPTIONAL:
#   ARCANE_CREDENTIALS_FILE  literal Arcane credentials path
#   DOCKER_CONTEXT           read-only Docker context (default docker-dmz)
#   ARCANE_ENV_ID            explicit Arcane environment id, forwarded as data only
set -euo pipefail

SVC="${1:?usage: deploy-gate.sh <service> <full-deploy-commit>}"
REVISION="${2:?need the full 40-hex deploy commit to verify}"
[ "$#" -eq 2 ] || { echo "deploy-gate: expected exactly service and full revision" >&2; exit 2; }

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SELF_DIR}/.." && pwd)"
CREDENTIALS_FILE="${ARCANE_CREDENTIALS_FILE:-/opt/skynet-ops/secrets/arcane.env}"
DOCKER_CONTEXT="${DOCKER_CONTEXT:-docker-dmz}"
SKYNET_BIN="${SKYNET_BIN:-${REPO_ROOT}/bin/skynet}"

ARGS=(verify deployment "${SVC}" "${REVISION}"
  --repo "${REPO_ROOT}"
  --credentials-file "${CREDENTIALS_FILE}"
  --context "${DOCKER_CONTEXT}")
[ -n "${ARCANE_ENV_ID:-}" ] && ARGS+=(--environment-id "${ARCANE_ENV_ID}")

exec "${SKYNET_BIN}" "${ARGS[@]}"
