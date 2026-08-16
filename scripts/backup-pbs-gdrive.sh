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

REMOTE="gdrive:Skynet/Backups/pbs"

# bwlimit: the old "08:00,10M 23:00,off" timetable was fine for small nightly incrementals but
# strangled the FIRST full seed — from 08:00 it capped at 10 MiB/s exactly while the job was
# still uploading its second half, which (with the old 6h unit timeout) meant ~46% of chunks
# never shipped (found in A6). Default now: unthrottled, so a seed can actually finish. Override
# with PBS_GDRIVE_BWLIMIT in pbs-gdrive.env once seeded if you want daytime courtesy throttling
# (e.g. PBS_GDRIVE_BWLIMIT="08:00,25M 23:00,off").
BWLIMIT="${PBS_GDRIVE_BWLIMIT:-off}"

# --transfers/--checkers bumped: the store is ~39k small chunk files and Drive throughput is
# bound by per-file API rate, not bandwidth, so more parallelism is what actually helps.
rclone sync "${PBS_DATASTORE_PATH}" "${REMOTE}" \
  --bwlimit "${BWLIMIT}" \
  --transfers 16 --checkers 32 --fast-list \
  --drive-pacer-min-sleep 10ms --low-level-retries 10 --retries 5

# Completion guard (A6): the old script trusted a clean `rclone sync` exit, but a systemd
# TimeoutStartSec kill left a half-finished upload looking "fine" for weeks. Never again —
# verify every local chunk actually exists off-site (size-only: chunks are content-addressed
# by name, so name+size is a strong check and skips slow hashing). Exit non-zero on any miss so
# the unit shows failed and the nightly report surfaces it.
echo "verifying off-site copy is complete (rclone check --one-way)..."
if ! rclone check "${PBS_DATASTORE_PATH}" "${REMOTE}" --one-way --size-only --fast-list; then
  echo "L5 INCOMPLETE: off-site copy is missing files vs the datastore — restore would fail" >&2
  exit 1
fi
echo "PBS datastore synced AND verified complete on ${REMOTE}"
