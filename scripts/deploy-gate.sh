#!/usr/bin/env bash
# deploy-gate.sh — the deterministic health gate that DECIDES a Compose rollback (SKY-018 P6).
#
# ADR 0005 §3: the rollback must fire without the agent noticing. This script is that decider — a
# dumb, deterministic probe of the just-deployed service. If the service is not healthy within the
# window it invokes scripts/gitops-rollback.sh (the executor) and returns non-zero. The LLM is never
# in this loop: the verdict is a container-state comparison, not a judgement.
#
# Health = every container in the project is Running, not Restarting, and (if it declares a
# healthcheck) reports `healthy` — the skynet service standard says every service declares one, so
# this is the service's own declared endpoint (compose healthcheck), probed deterministically.
#
# TIER: T2 — reads Arcane + docker over svc-ops (standing). Writes only on failure, via the executor.
# USAGE:
#   deploy-gate.sh <service> <deploy-commit>
# ENV (for testing / reuse from gitops-deploy.sh, all optional):
#   DEPLOY_GATE_PROBE   override the health probe with a command (exit 0 = healthy) — the seam the
#                       failure-case test injects an unhealthy result through.
#   DEPLOY_GATE_TIMEOUT total seconds to wait for health (default 60)
#   DEPLOY_GATE_INTERVAL poll interval seconds (default 3)
#   ARCANE_URL/ARCANE_TOKEN/ARCANE_ENV_ID, SSH_HOST, PROJ  reused if already resolved by the caller
#   GITOPS_ROLLBACK  path to the executor (default scripts/gitops-rollback.sh next to this file)
set -euo pipefail
SVC="${1:?usage: deploy-gate.sh <service> <deploy-commit>}"
COMMIT="${2:?need the deploy commit to revert on failure}"
SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GITOPS_ROLLBACK="${GITOPS_ROLLBACK:-${SELF_DIR}/gitops-rollback.sh}"
TIMEOUT="${DEPLOY_GATE_TIMEOUT:-60}"
INTERVAL="${DEPLOY_GATE_INTERVAL:-3}"

# --- the default probe: Arcane project running + all project containers healthy/running -----------
# Emits nothing on success (exit 0); a one-line reason on failure (exit 1). Deterministic.
default_probe() {
  local arc_env="/opt/skynet-ops/secrets/arcane.env"
  if [ -z "${ARCANE_URL:-}" ] || [ -z "${ARCANE_TOKEN:-}" ]; then
    { [ -r "${arc_env}" ] || sudo -n test -r "${arc_env}" 2>/dev/null; } || { echo "no arcane creds"; return 1; }
    set -a; source <(cat "${arc_env}" 2>/dev/null || sudo -n cat "${arc_env}"); set +a
  fi
  local envid="${ARCANE_ENV_ID:-0}"
  local host="${SSH_HOST:-svc-ops@$(printf '%s' "${ARCANE_URL}" | sed -E 's#^https?://([^:/]+).*#\1#')}"
  arc() { local m="$1" p="$2"; shift 2; curl -fsS -X "${m}" -H "X-API-Key: ${ARCANE_TOKEN}" "${ARCANE_URL}/api${p}" "$@"; }
  local proj="${PROJ:-}"
  if [ -z "${proj}" ]; then
    local sid
    sid="$(arc GET "/environments/${envid}/gitops-syncs" | jq -r --arg n "${SVC}" '.data[] | select(.name==$n or .projectName==$n) | .id' | head -1)"
    proj="$(arc GET "/environments/${envid}/gitops-syncs/${sid}" | jq -r '.data.projectId')"
  fi
  local st; st="$(arc GET "/environments/${envid}/projects/${proj}" | jq -r '.data.status')"
  [ "${st}" = "running" ] || { echo "project status=${st:-unknown}"; return 1; }
  # Per-container: Running && !Restarting && health in {none, healthy}. A single bad container fails.
  local bad
  bad="$(ssh "${host}" "for c in \$(docker ps -a --filter label=com.docker.compose.project=${SVC} --format '{{.Names}}'); do \
    r=\$(docker inspect \"\$c\" --format '{{.State.Running}}/{{.State.Restarting}}/{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}'); \
    case \"\$r\" in true/false/healthy|true/false/none) : ;; *) echo \"\$c=\$r\";; esac; done")"
  [ -z "${bad}" ] || { echo "unhealthy container(s): ${bad}"; return 1; }
  return 0
}

probe() { if [ -n "${DEPLOY_GATE_PROBE:-}" ]; then eval "${DEPLOY_GATE_PROBE}"; else default_probe; fi; }

echo "==> deploy-gate: probing ${SVC} health (timeout ${TIMEOUT}s)"
deadline=$(( $(date +%s) + TIMEOUT ))
reason=""
while :; do
  if reason="$(probe)"; then
    echo "==> deploy-gate: ${SVC} healthy — deploy kept"
    exit 0
  fi
  [ "$(date +%s)" -ge "${deadline}" ] && break
  sleep "${INTERVAL}"
done

echo "==> deploy-gate: ${SVC} UNHEALTHY after ${TIMEOUT}s (${reason:-no reason}) — reporting rollback required" >&2
"${GITOPS_ROLLBACK}" "${SVC}" "${COMMIT}"
echo "==> deploy-gate: ${SVC} rollback reported; no git mutation performed" >&2
exit 1
