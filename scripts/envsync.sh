#!/usr/bin/env bash
# envsync.sh — import legacy Arcane project.env layers into encrypted git (docs/design/secrets.md)
# TIER: T2 (unprivileged svc-ops SSH read of project.env) + local sops encrypt.
# USAGE: envsync.sh            # nightly; STAGES compose/<svc>/.env.sops on change (caller commits).
#   Current GitOps projects are already reproducible from .env.git + .env.sops and normally have no
#   project.env. When a legacy/non-GitOps project has one, read it over SSH and stage its encryption.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_DIR}"

# Docker host that stores Arcane project dirs. Override via env for other hosts.
DOCKER_HOST_SSH="${DOCKER_HOST_SSH:-svc-ops@10.10.100.15}"
ARCANE_PROJECTS_DIR="${ARCANE_PROJECTS_DIR:-/opt/docker/arcane-projects}"
# sops decryption (change-detection) needs the age private key (root:root 0600).
export SOPS_AGE_KEY_FILE="${SOPS_AGE_KEY_FILE:-/opt/skynet-ops/secrets/age.key}"

command -v sops >/dev/null || { echo "sops not installed" >&2; exit 1; }
changed=0

# Iterate the services we track in-repo.
for svc_dir in compose/*/; do
  svc="$(basename "${svc_dir}")"
  [ "${svc}" = "README.md" ] && continue

  # Arcane's on-disk dir names don't match our lowercase compose dirs (e.g. "Aiostreams"
  # vs "aiostreams"), so resolve the remote project dir case-insensitively over SSH.
  remote_dir="$(ssh -o BatchMode=yes "${DOCKER_HOST_SSH}" \
    "for d in ${ARCANE_PROJECTS_DIR}/*/; do [ \"\$(basename \"\$d\" | tr '[:upper:]' '[:lower:]')\" = '${svc}' ] && printf '%s' \"\${d%/}\" && break; done" 2>/dev/null)"
  if [ -z "${remote_dir}" ]; then echo "skip ${svc}: no Arcane project dir on host"; continue; fi
  remote_env="${remote_dir}/project.env"

  if ! ssh -o BatchMode=yes "${DOCKER_HOST_SSH}" "test -f '${remote_env}'" 2>/dev/null; then
    echo "skip ${svc}: no project.env on host"
    continue
  fi

  tmp="$(mktemp)"; trap 'rm -f "${tmp}"' EXIT
  ssh -o BatchMode=yes "${DOCKER_HOST_SSH}" "cat '${remote_env}'" > "${tmp}"

  out="compose/${svc}/.env.sops"
  # --filename-override so sops matches the compose/*/.env.sops creation rule (the tmp path
  # would not). Encryption needs only the age public key (from .sops.yaml).
  new="$(sops --encrypt --input-type dotenv --output-type dotenv --filename-override "${out}" "${tmp}")"

  # sops re-encrypts nondeterministically; compare decrypted plaintext to avoid churn.
  # Decryption needs the age private key (root-only) and the dotenv type.
  if [ -f "${out}" ] && diff -q <(sops -d --input-type dotenv --output-type dotenv "${out}" 2>/dev/null) "${tmp}" >/dev/null 2>&1; then
    echo "unchanged ${svc}"
  else
    printf '%s\n' "${new}" > "${out}"
    git add "${out}"
    changed=1
    echo "updated ${svc}"
  fi
  rm -f "${tmp}"; trap - EXIT
done

if [ "${changed}" -eq 1 ]; then
  # Stage only — the caller owns the single commit (nightly folds this into its one
  # inventory+docs+env commit; a standalone operator commits the staged .env.sops themselves).
  echo "staged encrypted env changes (commit owned by caller / nightly)"
else
  echo "no env changes"
fi
