#!/bin/sh
# Entrypoint of the two jobs (compose.yaml): backup | check. Restores are skynet-restore's, on the
# host (modules/docker-host.nix).
set -eu
# rclone saves refreshed tokens into its config, so it gets a writable copy of the mounted one.
cp /etc/rclone/rclone.conf /tmp/rclone.conf
export RCLONE_CONFIG=/tmp/rclone.conf
rp() { resticprofile --no-ansi --config /etc/resticprofile/profiles.yaml --name appdata "$@"; }

case "${1:-}" in
backup)
  # An empty or stale source would become the night's snapshot, and retention would age the real
  # ones out.
  if [ -z "$(ls -A /opt/appdata)" ]; then
    echo "backup: /opt/appdata is empty" >&2
    exit 1
  fi
  if [ "${APPDATA_SNAPSHOT:-}" = true ]; then
    # btrbk-appdata writes the stamp just before each snapshot (modules/docker-host.nix).
    age=$(($(date +%s) - $(cat /opt/appdata/.snapshot-stamp 2>/dev/null || echo 0)))
    if [ "$age" -gt 3600 ]; then
      echo "backup: the snapshot is ${age}s old: btrbk-appdata didn't run" >&2
      exit 1
    fi
  fi
  # The first backup creates the repository (restic init refuses one that exists).
  rp cat config >/dev/null 2>&1 || rp init || true
  rp backup
  ;;
check) rp prune && rp check ;;
*)
  echo "usage: run.sh backup|check" >&2
  exit 2
  ;;
esac
