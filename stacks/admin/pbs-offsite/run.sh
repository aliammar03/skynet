#!/bin/sh
# Entrypoint of the two jobs (compose.yaml): `sync` mirrors PBS's datastore to Drive and pings
# healthchecks.io; `check` confirms Drive holds every datastore file, unchanged.
set -eu
# rclone saves refreshed tokens into its config, so it gets a writable copy of the mounted one.
cp /etc/rclone/rclone.conf /tmp/rclone.conf
export RCLONE_CONFIG=/tmp/rclone.conf
src=/mnt/pbs-datastore
dst=gdrive:skynet/pbs
ping() { # <path: "", /start or /fail> [body]
  [ -z "${HC_PING_URL:-}" ] ||
    curl -fsS -m 10 --retry 3 -o /dev/null --data-raw "${2:-}" "$HC_PING_URL$1" || true
}
# For node-exporter on the host (its /var/lib/node-exporter): when the last sync ended, and rclone's
# exit code. Written whole, then renamed, so a scrape never reads half a file.
metrics() { # <rclone exit code>
  f=/var/lib/node-exporter/pbs-offsite.prom
  cat >"$f.tmp" <<EOF
# HELP skynet_pbs_offsite_end_timestamp_seconds When the last sync of PBS's datastore to Drive ended.
# TYPE skynet_pbs_offsite_end_timestamp_seconds gauge
skynet_pbs_offsite_end_timestamp_seconds $(date +%s)
# HELP skynet_pbs_offsite_exit_code The last sync's rclone exit code: 0 done, 8 the night's cap reached.
# TYPE skynet_pbs_offsite_exit_code gauge
skynet_pbs_offsite_exit_code $1
EOF
  mv "$f.tmp" "$f"
}

# An unmounted or empty source would make `sync` empty Drive's copy: never run without the chunks.
if [ ! -d "$src/.chunks/0000" ]; then
  echo "pbs-offsite: no datastore at $src" >&2
  [ "${1:-}" != sync ] || ping /fail "no datastore at $src"
  exit 1
fi
# PBS's lock and GC status, and the temporary files it renames into place: a restore needs none.
set -- "${1:-}" --exclude /.lock --exclude /.gc-status --exclude '*.tmp' --exclude '*.tmp_*' --fast-list

case "$1" in
sync)
  ping /start
  shift
  rc=0
  # Drive takes about 2 new files a second and 750 GiB a day. Exit 8: --max-transfer reached; the
  # rest goes the next night.
  rclone sync "$src" "$dst" "$@" --transfers 4 --tpslimit 8 --drive-chunk-size 64M \
    --max-transfer 700G --cutoff-mode soft \
    --stats 15m --stats-one-line --stats-log-level NOTICE || rc=$?
  metrics "$rc" || true
  case $rc in
  0 | 8) ping "" "rclone sync: exit $rc" ;;
  *)
    ping /fail "rclone sync: exit $rc (the job's log has the rest)"
    exit "$rc"
    ;;
  esac
  ;;
check)
  shift
  rclone check --one-way "$src" "$dst" "$@"
  ;;
*)
  echo "usage: run.sh sync|check" >&2
  exit 2
  ;;
esac
