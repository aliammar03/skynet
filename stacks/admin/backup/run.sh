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
  # An empty, stale or half-restored source would become the night's snapshot, and retention would
  # age the real ones out. Its dot files (btrbk's stamp, the marker) aren't app data: an app's
  # folder must hold something. And the marker doco-cd waits for must be there: skynet-restore
  # takes it away while it works, and a fresh host has none yet.
  if [ -z "$(find /opt/appdata -mindepth 2 -maxdepth 2 ! -path '/opt/appdata/.*' | head -n 1)" ]; then
    echo "backup: /opt/appdata holds no app data" >&2
    exit 1
  fi
  if [ ! -e /opt/appdata/.data-ready ]; then
    echo "backup: /opt/appdata has no .data-ready: a restore is under way or failed, or the host is new" >&2
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
