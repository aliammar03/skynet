#!/usr/bin/env bash
# envsync.sh — back up each project's secret env layer into git, encrypted (plan §5)
# TIER: T2 (unprivileged svc-ops SSH read of project.env) + local sops encrypt.
# USAGE: envsync.sh            # nightly; commits compose/<svc>/.env.sops only on change.
#   Reads project.env (Arcane's override layer — the only env not reproducible from the repo)
#   over SSH from the docker host, sops-encrypts it, commits if changed.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_DIR}"

# Docker host that stores Arcane project dirs. Override via env for other hosts.
DOCKER_HOST_SSH="${DOCKER_HOST_SSH:-svc-ops@10.10.100.15}"
ARCANE_PROJECTS_DIR="${ARCANE_PROJECTS_DIR:-/opt/arcane/projects}"

command -v sops >/dev/null || { echo "sops not installed" >&2; exit 1; }
changed=0

# Iterate the services we track in-repo.
for svc_dir in compose/*/; do
  svc="$(basename "${svc_dir}")"
  [ "${svc}" = "README.md" ] && continue
  remote_env="${ARCANE_PROJECTS_DIR}/${svc}/project.env"

  if ! ssh -o BatchMode=yes "${DOCKER_HOST_SSH}" "test -f '${remote_env}'" 2>/dev/null; then
    echo "skip ${svc}: no project.env on host"
    continue
  fi

  tmp="$(mktemp)"; trap 'rm -f "${tmp}"' EXIT
  ssh -o BatchMode=yes "${DOCKER_HOST_SSH}" "cat '${remote_env}'" > "${tmp}"

  out="compose/${svc}/.env.sops"
  new="$(sops --encrypt --input-type dotenv --output-type dotenv "${tmp}" 2>/dev/null)"

  # sops re-encrypts nondeterministically; compare decrypted plaintext to avoid churn.
  if [ -f "${out}" ] && diff -q <(sops -d "${out}" 2>/dev/null) "${tmp}" >/dev/null 2>&1; then
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
  git commit -m "envsync: refresh encrypted project env" >/dev/null
  echo "committed env changes (push handled by caller / nightly)"
else
  echo "no env changes"
fi
