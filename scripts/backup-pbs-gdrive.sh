#!/usr/bin/env bash
# backup-pbs-gdrive.sh — off-site copy of the PBS datastore to Google Drive (plan §6 L5)
# USAGE: backup-pbs-gdrive.sh
#   Runs AFTER PBS garbage-collection. Datastore is already client-side encrypted, so
#   rclone just moves ciphertext. Dedup chunks keep incrementals tiny.
#   Reads /opt/skynet-ops/secrets/pbs-gdrive.env:
#     RCLONE_CONFIG=/opt/skynet-ops/secrets/rclone.conf
#     PBS_DATASTORE_PATH=/mnt/datastore/main   # local path, run on the PBS host
set -euo pipefail
secret="/opt/skynet-ops/secrets/pbs-gdrive.env"

if ! sudo test -f "${secret}"; then
  echo "no pbs-gdrive config yet (${secret}) — idle until A4" >&2
  exit 0
fi
# shellcheck disable=SC1090
eval "$(sudo cat "${secret}")"
: "${PBS_DATASTORE_PATH:?}" "${RCLONE_CONFIG:?}"
export RCLONE_CONFIG

# bwlimit timetable: throttle to 10 MiB/s during waking hours (08:00), unlimited overnight
# (23:00 -> off) when the timer actually runs. The datastore is already deduplicated +
# compressed on disk (see plan §6), so this uploads the on-disk footprint, not logical size.
rclone sync "${PBS_DATASTORE_PATH}" gdrive:Skynet/Backups/pbs \
  --bwlimit "08:00,10M 23:00,off" \
  --transfers 4 --checkers 8 --fast-list
echo "PBS datastore synced to gdrive:Skynet/Backups/pbs"
