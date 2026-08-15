#!/usr/bin/env bash
# backup-restic.sh — nightly restic backup of a docker host's appdata → Google Drive (plan §6 L3)
# TIER: runs on/against the docker host; restic encrypts client-side (Google sees ciphertext).
# USAGE: backup-restic.sh <host-label>
#   Reads /opt/skynet-ops/secrets/restic-<host>.env:
#     export RESTIC_REPOSITORY='rclone:gdrive:skynet-backups/restic/<host>'
#     export RESTIC_PASSWORD_FILE=/opt/skynet-ops/secrets/restic-<host>.pass
#     export RCLONE_CONFIG=/opt/skynet-ops/secrets/rclone.conf
#   Database-backed services must dump into appdata via a pre-hook (see restore-service.md).
set -euo pipefail
host="${1:?usage: backup-restic.sh <host-label>}"
secret="/opt/skynet-ops/secrets/restic-${host}.env"
APPDATA="${APPDATA:-/opt/docker/appdata}"

if ! sudo test -f "${secret}"; then
  echo "no restic config yet (${secret}) — idle until A4 init" >&2
  exit 0
fi
# shellcheck disable=SC1090
eval "$(sudo cat "${secret}")"
: "${RESTIC_REPOSITORY:?}"

restic backup "${APPDATA}" \
  --exclude-caches \
  --exclude '*/cache/*' --exclude '*/transcodes/*' --exclude '*/logs/*'

restic forget --keep-daily 7 --keep-weekly 4 --keep-monthly 6 --prune
restic check --read-data-subset=2%
echo "restic backup complete for ${host}"
