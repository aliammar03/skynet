#!/usr/bin/env bash
# collect-docker.sh — T1 read-only snapshot of a docker host → inventory/docker-<host>.json
# USAGE: collect-docker.sh <host-label> [docker-context]
#   Uses an unprivileged `docker context` (svc-ops in the docker group). Read-only.
#   Default host-label 'docker-dmz', default context = same label.
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
label="${1:-docker-dmz}"
ctx="${2:-${label}}"

command -v docker >/dev/null || { echo "docker CLI missing" >&2; exit 1; }
if ! docker context inspect "${ctx}" >/dev/null 2>&1; then
  echo "docker context '${ctx}' not configured yet — collector idle until A3" >&2
  exit 0
fi

dc() { docker --context "${ctx}" "$@"; }
out="${REPO_DIR}/inventory/docker-${label}.json"

containers="$(dc ps --all --format '{{json .}}' | jq -s '.')"
images="$(dc image ls --format '{{json .}}' | jq -s '.')"

jq -n \
  --arg host "${label}" --arg ts "$(date -Iseconds)" \
  --argjson containers "${containers}" \
  --argjson images "${images}" \
  '{host:$host, collected:$ts, containers:$containers, images:$images}' > "${out}"
echo "wrote ${out}"
