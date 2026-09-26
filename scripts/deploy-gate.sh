#!/usr/bin/env bash
# deploy-gate.sh — compatibility forwarder for the packaged, report-only verifier.
# TIER: T2 PR-gated verification; the route probe has a bounded ephemeral container/cache side effect.
#
# Current caller: scripts/gitops-deploy.sh <service> <expected-revision>. The Python verifier
# owns Arcane/Docker/ingress observations and never invokes rollback or mutates Git/runtime state.
# Keep this shim until the SKY-025 phase that ports deploy (13) removes the old command name.
#
# USAGE:
#   deploy-gate.sh <service> <expected-revision>
# OPTIONAL:
#   ARCANE_CREDENTIALS_FILE  literal Arcane credentials path
#   DOCKER_CONTEXT           read-only Docker context (default docker-dmz)
#   ARCANE_ENV_ID            explicit Arcane environment id, forwarded as data only
set -euo pipefail

if [ "$#" -ne 2 ]; then
  echo "usage: deploy-gate.sh <service> <expected-revision>" >&2
  exit 2
fi
SVC="$1"
REVISION="$2"

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
