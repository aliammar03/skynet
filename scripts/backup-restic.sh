#!/usr/bin/env bash
# backup-restic.sh — nightly restic backup of a host → Google Drive (plan §6 L3).
# TIER: runs on/against the host; restic encrypts client-side (Google sees ciphertext).
# Provisioned by scripts/provision-restic.sh (A4.5). USAGE: backup-restic.sh <host-label> [tag ...]
# The systemd timer passes no tags (snapshot tagged `scheduled`); on-demand runs pass one or
# more tags (snapshot tagged `manual` + those tags) so a pre-change backup is easy to find:
#   restic snapshots --tag manual        # e.g. before a risky change: backup-restic.sh <label> pre-<reason>
#
#   Reads /opt/skynet-ops/secrets/restic-<label>.env:
#     export RESTIC_REPOSITORY='rclone:gdrive:Skynet/Backups/restic/<label>'
#     export RESTIC_PASSWORD_FILE=/opt/skynet-ops/secrets/restic-<label>.pass
#     export RCLONE_CONFIG=/opt/skynet-ops/secrets/rclone.conf
#     BACKUP_PATHS="/srv/foo /data/bar"   # optional: extra absolute folders (space-separated)
#     BACKUP_DOCKER=auto|yes|no           # docker appdata + protect volumes (default: auto)
#     RESTIC_EXCLUDES="*/foo/* */bar/*"   # optional: extra exclude patterns (space-separated)
#
# WHAT GETS BACKED UP:
#   1. Any absolute paths listed in BACKUP_PATHS (folders of your choosing).
#   2. If this is a docker host (BACKUP_DOCKER): $APPDATA (all bind-mounted app data) PLUS
#      named volumes labelled $BACKUP_LABEL (db engines keep data in named volumes so docker
#      manages per-engine uid). Volumes labelled skynet.backup=ephemeral are simply not selected.
set -euo pipefail
host="${1:?usage: backup-restic.sh <host-label> [tag ...]}"; shift
# Distinguish scheduled vs on-demand snapshots by tag.
tags=(--tag scheduled)
if [ "$#" -gt 0 ]; then tags=(--tag manual); for t in "$@"; do tags+=(--tag "${t}"); done; fi
secret="/opt/skynet-ops/secrets/restic-${host}.env"
APPDATA="${APPDATA:-/opt/docker/appdata}"
BACKUP_LABEL="${BACKUP_LABEL:-skynet.backup=protect}"

if ! sudo test -f "${secret}"; then
  echo "no restic config yet (${secret}) — idle until provisioned (scripts/provision-restic.sh)" >&2
  exit 0
fi
# shellcheck disable=SC1090
eval "$(sudo cat "${secret}")"
: "${RESTIC_REPOSITORY:?}"
BACKUP_DOCKER="${BACKUP_DOCKER:-auto}"

targets=()
# General excludes applied to every host.
excludes=(--exclude-caches --exclude '*/cache/*' --exclude '*/logs/*')

# (1) arbitrary folders of your choosing ------------------------------------
if [ -n "${BACKUP_PATHS:-}" ]; then
  for p in ${BACKUP_PATHS}; do
    if [ -e "${p}" ]; then targets+=("${p}"); else echo "WARN: BACKUP_PATHS entry missing, skipping: ${p}" >&2; fi
  done
fi

# (2) docker host: appdata + protect-labelled named volumes -----------------
docker_on=no
case "${BACKUP_DOCKER}" in
  yes)  docker_on=yes ;;
  no)   docker_on=no ;;
  auto) command -v docker >/dev/null 2>&1 && [ -d "${APPDATA}" ] && docker_on=yes ;;
  *)    echo "BACKUP_DOCKER must be auto|yes|no (got '${BACKUP_DOCKER}')" >&2; exit 1 ;;
esac
if [ "${docker_on}" = yes ]; then
  [ -d "${APPDATA}" ] && targets+=("${APPDATA}")
  # media/cache dirs that live under appdata but are rebuildable.
  excludes+=(--exclude '*/poster-cache/*' --exclude '*/cold-store/*' --exclude '*/transcodes/*')
  vol_paths=()
  while IFS= read -r vol; do
    [ -n "${vol}" ] || continue
    mp="$(docker volume inspect -f '{{.Mountpoint}}' "${vol}" 2>/dev/null || true)"
    [ -n "${mp}" ] && vol_paths+=("${mp}")
  done < <(docker volume ls --filter "label=${BACKUP_LABEL}" --format '{{.Name}}')
  echo "docker: appdata + ${#vol_paths[@]} protect volume(s) (${vol_paths[*]:-none})"
  targets+=("${vol_paths[@]}")
fi

# (3) extra excludes --------------------------------------------------------
if [ -n "${RESTIC_EXCLUDES:-}" ]; then
  for e in ${RESTIC_EXCLUDES}; do excludes+=(--exclude "${e}"); done
fi

[ "${#targets[@]}" -gt 0 ] || { echo "no backup targets resolved for ${host} — set BACKUP_PATHS and/or BACKUP_DOCKER" >&2; exit 1; }
echo "restic targets (${#targets[@]}): ${targets[*]}"

echo "snapshot tags: ${tags[*]}"
restic backup "${targets[@]}" "${excludes[@]}" "${tags[@]}"
restic forget --keep-daily 7 --keep-weekly 4 --keep-monthly 6 --prune
restic check --read-data-subset=2%
echo "restic backup complete for ${host}"
