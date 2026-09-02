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
# TIER: T2 (standing) — runs entirely as unprivileged svc-ops over SSH. Arcane owns its
# project dirs as its own uid (PUID/PGID), mode 0700, so svc-ops can't write .env there
# *directly*; but svc-ops is in the docker group (the T2 mechanism for docker hosts,
# AGENTS.md §1), so the .env write goes through a throwaway container that bind-mounts the
# project dir, and the docker ps health checks run as svc-ops too. No T2+ root grant needed.
#
# USAGE: scripts/gitops-deploy.sh <service> [--no-deploy] [--gate] [--revert-commit <sha>]
#   <service>          a directory name under compose/ (e.g. aiostreams)
#   --no-deploy        materialise .env + ensure the sync, but don't redeploy
#   --gate             health-gate the deploy (SKY-018 P6): after deploy, deterministically probe
#                      the service; if it isn't healthy in the window, auto-revert the deploy commit
#                      and let Arcane reconcile back. The rollback DECISION is scripts/deploy-gate.sh
#                      (a container-state check), not the agent — see ADR 0005 §3.
#   --revert-commit    the commit --gate reverts on failure (default: the newest commit touching
#                      compose/<service>/, i.e. this deploy's change)
set -euo pipefail

SVC="${1:?usage: gitops-deploy.sh <service> [--no-deploy] [--gate] [--revert-commit <sha>]}"; shift || true
NO_DEPLOY=""; GATE=0; REVERT_COMMIT=""
while [ "$#" -gt 0 ]; do case "$1" in
  --no-deploy)     NO_DEPLOY="--no-deploy" ;;
  --gate)          GATE=1 ;;
  --revert-commit) shift; REVERT_COMMIT="${1:?--revert-commit needs a sha}" ;;
  *) echo "gitops-deploy: unknown arg '$1'" >&2; exit 2 ;;
esac; shift; done
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SVC_DIR="${REPO_ROOT}/compose/${SVC}"
COMPOSE_REL="compose/${SVC}/compose.yaml"

[ -f "${SVC_DIR}/compose.yaml" ] || { echo "no compose at ${SVC_DIR}/compose.yaml" >&2; exit 1; }

# --- secrets / config -------------------------------------------------------
ARC_ENV="/opt/skynet-ops/secrets/arcane.env"
AGE_KEY="/opt/skynet-ops/secrets/age.key"
set -a; source <(cat "${ARC_ENV}" 2>/dev/null || sudo -n cat "${ARC_ENV}"); set +a
: "${ARCANE_URL:?ARCANE_URL missing from ${ARC_ENV}}"
: "${ARCANE_TOKEN:?ARCANE_TOKEN missing from ${ARC_ENV}}"
ENVID="${ARCANE_ENV_ID:-0}"
BRANCH="${GITOPS_BRANCH:-main}"   # override during migration to verify off a feature branch
# Deploy identity = standing T2 svc-ops (NOT root). The docker host is the Arcane host in ARCANE_URL.
DOCKER_HOST_NAME="$(printf '%s' "${ARCANE_URL}" | sed -E 's#^https?://([^:/]+).*#\1#')"
SSH_HOST="svc-ops@${DOCKER_HOST_NAME}"
# Tiny throwaway image used only to drop the effective .env into Arcane's (0700, PUID-owned)
# project dir via the docker group. Pinned by digest — Renovate bumps it like any other image.
ENVWRITER_IMG="busybox@sha256:dc2d74b28e4cf8984fa52af1f39bc7c3d9c73760b41a74d629f5d11b1ab28616"

arc() { # arc METHOD PATH [curl-args...]
  local m="$1" p="$2"; shift 2
  curl -fsS -X "${m}" -H "X-API-Key: ${ARCANE_TOKEN}" "${ARCANE_URL}/api${p}" "$@"
}
# Arcane's sync endpoint can 500 transiently right after a branch repoint/push (it races its own
# fetch of the new ref). Retry a few times so a flake doesn't abort the deploy before the gate runs.
arc_retry() { local m="$1" p="$2"; shift 2; local i; for i in 1 2 3 4 5; do arc "${m}" "${p}" "$@" && return 0; sleep 2; done; return 1; }

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
  arc_retry POST "/environments/${ENVID}/gitops-syncs/${SID}/sync" >/dev/null
fi
sleep 2

# --- project id + host path -------------------------------------------------
PROJ="$(arc GET "/environments/${ENVID}/gitops-syncs/${SID}" | jq -r '.data.projectId')"
PPATH="$(arc GET "/environments/${ENVID}/projects/${PROJ}" | jq -r '.data.path')"
[ -n "${PPATH}" ] && [ "${PPATH}" != "null" ] || { echo "could not resolve project path" >&2; exit 1; }

# --- materialise effective .env = .env.git + decrypt(.env.sops) -------------
# Decrypted entirely off-host (age key never leaves vm-skynet-ops); the plaintext transits
# only the ssh channel and the throwaway container's stdin — never an argv or extra on-disk file.
TMP="$(mktemp)"; trap 'rm -f "${TMP}"' EXIT
: > "${TMP}"
[ -f "${SVC_DIR}/.env.git" ]  && { cat "${SVC_DIR}/.env.git" >> "${TMP}"; echo >> "${TMP}"; }
if [ -f "${SVC_DIR}/.env.sops" ]; then
  # Age key is group-readable by the ops user, so decrypt unprivileged; fall back to sudo -n
  # (a NOPASSWD host) only if that fails. Same "try direct, then sudo -n" idiom as ARC_ENV above —
  # a bare `sudo` here breaks non-interactive T2 deploys (no tty for a password prompt).
  SOPS_AGE_KEY_FILE="${AGE_KEY}" sops -d --input-type dotenv --output-type dotenv \
    "${SVC_DIR}/.env.sops" >> "${TMP}" 2>/dev/null \
  || sudo -n SOPS_AGE_KEY_FILE="${AGE_KEY}" sops -d --input-type dotenv --output-type dotenv \
    "${SVC_DIR}/.env.sops" >> "${TMP}"
fi
KEYS="$(grep -cE '^[A-Za-z_][A-Za-z0-9_]*=' "${TMP}" || true)"
# Arcane owns the project dir as its PUID (0700) — svc-ops can't write .env directly, so the
# docker group does it via a container bind-mount. Match the file's owner to the dir's owner so
# Arcane can read it, and force 0600 with chmod (a truncating `cat >` keeps a pre-existing
# file's mode, so umask alone would leave a stale 0644 on a secret file).
# (svc-ops can stat the dir through the 0755 parent.)
OWNER="$(ssh "${SSH_HOST}" "stat -c '%u:%g' '${PPATH}'")"
ssh "${SSH_HOST}" "docker run --rm -i -v '${PPATH}':/mnt ${ENVWRITER_IMG} \
  sh -c 'cat > /mnt/.env; chown ${OWNER} /mnt/.env; chmod 600 /mnt/.env'" < "${TMP}"
echo "==> wrote ${PPATH}/.env (${KEYS} keys, owner ${OWNER}, mode 600) via svc-ops docker group"

[ "${NO_DEPLOY}" = "--no-deploy" ] && { echo "sync ready, skipping deploy (--no-deploy)"; exit 0; }

# --- deploy + health --------------------------------------------------------
echo "==> redeploying ${SVC}"
arc POST "/environments/${ENVID}/projects/${PROJ}/redeploy" >/dev/null || true

# Config-file services read a bind-mounted config only at STARTUP, and a file-only change doesn't
# alter the compose spec — so Arcane's redeploy leaves the running container untouched and the new
# config is never loaded. Force a restart for those. (cloudflared has no --watch; Caddy hot-reloads
# via --watch, so it's deliberately NOT here.) Otherwise every tunnel-config change is a silent
# two-step where the second step is easy to forget. See runbooks/publish-service.md Path C.
case "${SVC}" in
  cloudflared)
    echo "==> ${SVC}: restarting container(s) to reload bind-mounted config"
    ssh "${SSH_HOST}" "docker restart \$(docker ps -q --filter label=com.docker.compose.project=${SVC})" >/dev/null || true ;;
esac

for i in $(seq 1 20); do
  sleep 3
  ST="$(arc GET "/environments/${ENVID}/projects/${PROJ}" | jq -r '.data.status')"
  [ "${ST}" = "running" ] && break
done
echo "==> ${SVC}: project status = ${ST:-unknown}"
ssh "${SSH_HOST}" "docker ps --filter label=com.docker.compose.project --format '{{.Names}}\t{{.Status}}' | grep -i '${SVC}' || true"

# --- role tag (skynet standard: exactly one x-arcane role tag per service; Arcane applies
#     it from the synced compose). Report it, and warn if the service is untagged. ---
TAGS="$(arc GET "/environments/${ENVID}/projects/${PROJ}" | jq -r '(.data.tags // [])|map(.name)|join(", ")')"
if [ -n "${TAGS}" ]; then
  echo "==> ${SVC}: role tag(s) = ${TAGS}"
else
  echo "==> ${SVC}: WARNING — no role tag; add x-arcane.tags to compose/${SVC}/compose.yaml" >&2
fi

# --- healthcheck coverage (skynet standard: every service declares one; image-built-in counts) ---
MISSING="$(ssh "${SSH_HOST}" "for c in \$(docker ps --filter label=com.docker.compose.project=${SVC} --format '{{.Names}}'); do \
  [ \"\$(docker inspect \"\$c\" --format '{{if .State.Health}}ok{{else}}none{{end}}')\" = none ] && echo \"\$c\"; done")"
if [ -n "${MISSING}" ]; then
  echo "==> ${SVC}: WARNING — service(s) without a healthcheck (add one to compose):" >&2
  echo "${MISSING}" | sed 's/^/      /' >&2
fi

# --- health gate (SKY-018 P6, opt-in via --gate) ----------------------------
# Deploy → probe → auto-revert on failure. The gate reuses the creds/ids resolved above (exported so
# deploy-gate.sh's default probe doesn't re-resolve them) and reverts the deploy commit if unhealthy.
if [ "${GATE}" = 1 ]; then
  [ -n "${REVERT_COMMIT}" ] || REVERT_COMMIT="$(git -C "${REPO_ROOT}" log -1 --format=%H -- "compose/${SVC}/")"
  [ -n "${REVERT_COMMIT}" ] || { echo "==> ${SVC}: --gate: no commit touches compose/${SVC}/ — nothing to revert to" >&2; exit 1; }
  export ARCANE_URL ARCANE_TOKEN SSH_HOST PROJ
  export ARCANE_ENV_ID="${ENVID}"
  exec "${REPO_ROOT}/scripts/deploy-gate.sh" "${SVC}" "${REVERT_COMMIT}"
fi
