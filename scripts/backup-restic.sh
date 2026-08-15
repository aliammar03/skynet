#!/usr/bin/env bash
# backup-restic.sh — nightly restic backup of a docker host → Google Drive (plan §6 L3)
# TIER: runs on/against the docker host; restic encrypts client-side (Google sees ciphertext).
# USAGE: backup-restic.sh <host-label>
#   Reads /opt/skynet-ops/secrets/restic-<host>.env:
#     export RESTIC_REPOSITORY='rclone:gdrive:Skynet/Backups/restic/<host>'
#     export RESTIC_PASSWORD_FILE=/opt/skynet-ops/secrets/restic-<host>.pass
#     export RCLONE_CONFIG=/opt/skynet-ops/secrets/rclone.conf
#
# WHAT GETS BACKED UP (the skynet volume standard):
#   1. /opt/docker/appdata — all simple-file data (services bind-mount here).
#   2. Database-engine named volumes labelled `skynet.backup=protect` — backed up directly
#      by their mountpoints (mongo/postgres/etc. keep data in named volumes so docker manages
#      per-engine uid). Volumes labelled `skynet.backup=ephemeral` (caches/indexes) are skipped.
set -euo pipefail
host="${1:?usage: backup-restic.sh <host-label>}"
secret="/opt/skynet-ops/secrets/restic-${host}.env"
APPDATA="${APPDATA:-/opt/docker/appdata}"
BACKUP_LABEL="${BACKUP_LABEL:-skynet.backup=protect}"

if ! sudo test -f "${secret}"; then
  echo "no restic config yet (${secret}) — idle until A4 init" >&2
  exit 0
fi
# shellcheck disable=SC1090
eval "$(sudo cat "${secret}")"
: "${RESTIC_REPOSITORY:?}"

# Resolve mountpoints of critical database named volumes (docker manages these dirs under
# /var/lib/docker/volumes/<vol>/_data; restic reads them as root).
vol_paths=()
while IFS= read -r vol; do
  [ -n "${vol}" ] || continue
  mp="$(docker volume inspect -f '{{.Mountpoint}}' "${vol}" 2>/dev/null || true)"
  [ -n "${mp}" ] && vol_paths+=("${mp}")
done < <(docker volume ls --filter "label=${BACKUP_LABEL}" --format '{{.Name}}')
echo "critical db volumes: ${#vol_paths[@]} (${vol_paths[*]:-none})"

restic backup "${APPDATA}" "${vol_paths[@]}" \
  --exclude-caches \
  --exclude '*/cache/*' --exclude '*/poster-cache/*' --exclude '*/cold-store/*' \
  --exclude '*/transcodes/*' --exclude '*/logs/*'

restic forget --keep-daily 7 --keep-weekly 4 --keep-monthly 6 --prune
restic check --read-data-subset=2%
echo "restic backup complete for ${host}"
