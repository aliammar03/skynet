#!/usr/bin/env bash
# gitops-deploy.sh — deploy one service onto the canonical "skynet way" via Arcane GitOps.
#
# The standard (compose/README.md):
#   compose/<svc>/compose.yaml  — pinned images, env_file: .env   (Arcane GitOps owns this)
#   compose/<svc>/.env.git      — non-secret config, committed plaintext
#   compose/<svc>/.env.sops     — secrets only, sops+age
#
# Arcane's GitOps sync copies compose.yaml from git and manages the project lifecycle,
# but it does NOT merge .env.git/.env.sops into the effective .env (that layering model is
# for Arcane's non-GitOps projects). So THIS script materialises the effective `.env` on the
# host = .env.git + decrypt(.env.sops), which compose reads via `env_file: .env`. Arcane's
# auto-sync leaves a populated .env untouched (verified), so the two coexist cleanly.
#
# Idempotent: creates the GitOps sync if absent, refreshes .env, redeploys, health-checks.
#
# USAGE: scripts/gitops-deploy.sh <service> [--no-deploy]
#   <service>  a directory name under compose/ (e.g. aiostreams)
set -euo pipefail

SVC="${1:?usage: gitops-deploy.sh <service> [--no-deploy]}"
NO_DEPLOY="${2:-}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SVC_DIR="${REPO_ROOT}/compose/${SVC}"
COMPOSE_REL="compose/${SVC}/compose.yaml"

[ -f "${SVC_DIR}/compose.yaml" ] || { echo "no compose at ${SVC_DIR}/compose.yaml" >&2; exit 1; }

# --- secrets / config -------------------------------------------------------
ARC_ENV="/opt/skynet-ops/secrets/arcane.env"
AGE_KEY="/opt/skynet-ops/secrets/age.key"
set -a; source <(sudo cat "${ARC_ENV}"); set +a
: "${ARCANE_URL:?ARCANE_URL missing from ${ARC_ENV}}"
: "${ARCANE_TOKEN:?ARCANE_TOKEN missing from ${ARC_ENV}}"
ENVID="${ARCANE_ENV_ID:-0}"
BRANCH="${GITOPS_BRANCH:-main}"   # override during migration to verify off a feature branch
SSH_HOST="root@$(printf '%s' "${ARCANE_URL}" | sed -E 's#^https?://([^:/]+).*#\1#')"

arc() { # arc METHOD PATH [curl-args...]
  local m="$1" p="$2"; shift 2
  curl -fsS -X "${m}" -H "X-API-Key: ${ARCANE_TOKEN}" "${ARCANE_URL}/api${p}" "$@"
}

# --- resolve repository id (match Arcane's registered repo to git origin) ----
ORIGIN="$(git -C "${REPO_ROOT}" config --get remote.origin.url)"; ORIGIN="${ORIGIN%.git}"
REPO_ID="$(arc GET "/customize/git-repositories" \
  | jq -r --arg u "${ORIGIN}" '.data[] | select((.url|rtrimstr(".git"))==$u) | .id' | head -1)"
[ -n "${REPO_ID}" ] || { echo "repo ${ORIGIN} not registered in Arcane (add it in Settings > Git Repositories)" >&2; exit 1; }

# --- ensure a GitOps sync exists for this service ---------------------------
SID="$(arc GET "/environments/${ENVID}/gitops-syncs" \
  | jq -r --arg n "${SVC}" '.data[] | select(.name==$n or .projectName==$n) | .id' | head -1)"
if [ -z "${SID}" ]; then
  echo "==> creating GitOps sync for ${SVC} (branch ${BRANCH})"
  SID="$(arc POST "/environments/${ENVID}/gitops-syncs" -H 'Content-Type: application/json' \
    -d "$(jq -nc --arg n "${SVC}" --arg r "${REPO_ID}" --arg c "${COMPOSE_REL}" --arg b "${BRANCH}" \
        '{name:$n, projectName:$n, repositoryId:$r, branch:$b, composePath:$c,
          syncDirectory:true, autoSync:true, syncInterval:180}')" \
    | jq -r '.data.id')"
else
  CUR_BRANCH="$(arc GET "/environments/${ENVID}/gitops-syncs/${SID}" | jq -r '.data.branch')"
  if [ "${CUR_BRANCH}" != "${BRANCH}" ]; then
    echo "==> repointing ${SVC} sync ${CUR_BRANCH} -> ${BRANCH}"
    arc PUT "/environments/${ENVID}/gitops-syncs/${SID}" -H 'Content-Type: application/json' \
      -d "$(jq -nc --arg b "${BRANCH}" '{branch:$b}')" >/dev/null
  fi
  echo "==> GitOps sync exists for ${SVC} (${SID}); pulling latest (branch ${BRANCH})"
  arc POST "/environments/${ENVID}/gitops-syncs/${SID}/sync" >/dev/null
fi
sleep 2

# --- project id + host path -------------------------------------------------
PROJ="$(arc GET "/environments/${ENVID}/gitops-syncs/${SID}" | jq -r '.data.projectId')"
PPATH="$(arc GET "/environments/${ENVID}/projects/${PROJ}" | jq -r '.data.path')"
[ -n "${PPATH}" ] && [ "${PPATH}" != "null" ] || { echo "could not resolve project path" >&2; exit 1; }

# --- materialise effective .env = .env.git + decrypt(.env.sops) -------------
# Built entirely off-host; plaintext transits only the ssh channel, lands 0600 root.
TMP="$(mktemp)"; trap 'rm -f "${TMP}"' EXIT
: > "${TMP}"
[ -f "${SVC_DIR}/.env.git" ]  && { cat "${SVC_DIR}/.env.git" >> "${TMP}"; echo >> "${TMP}"; }
if [ -f "${SVC_DIR}/.env.sops" ]; then
  sudo SOPS_AGE_KEY_FILE="${AGE_KEY}" sops -d --input-type dotenv --output-type dotenv \
    "${SVC_DIR}/.env.sops" >> "${TMP}"
fi
KEYS="$(grep -cE '^[A-Za-z_][A-Za-z0-9_]*=' "${TMP}" || true)"
ssh "${SSH_HOST}" "umask 077; cat > '${PPATH}/.env'" < "${TMP}"
echo "==> wrote ${PPATH}/.env (${KEYS} keys)"

[ "${NO_DEPLOY}" = "--no-deploy" ] && { echo "sync ready, skipping deploy (--no-deploy)"; exit 0; }

# --- deploy + health --------------------------------------------------------
echo "==> redeploying ${SVC}"
arc POST "/environments/${ENVID}/projects/${PROJ}/redeploy" >/dev/null || true
for i in $(seq 1 20); do
  sleep 3
  ST="$(arc GET "/environments/${ENVID}/projects/${PROJ}" | jq -r '.data.status')"
  [ "${ST}" = "running" ] && break
done
echo "==> ${SVC}: project status = ${ST:-unknown}"
ssh "${SSH_HOST}" "docker ps --filter label=com.docker.compose.project --format '{{.Names}}\t{{.Status}}' | grep -i '${SVC}' || true"
