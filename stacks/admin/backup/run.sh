#!/bin/sh
# Entrypoint of the three jobs (compose.yaml), and of skynet-restore's direct runs:
#   backup | check | restore          the jobs; restore does what restore.request says
#   snapshots | diff <stack> | restore-to <stack> <snapshot> <dir>
set -eu
# rclone saves refreshed tokens into its config, so it gets a writable copy of the mounted one.
cp /etc/rclone/rclone.conf /tmp/rclone.conf
export RCLONE_CONFIG=/tmp/rclone.conf
rp() { resticprofile --no-ansi --config /etc/resticprofile/profiles.yaml --name appdata "$@"; }

# Puts /opt/appdata/<stack> back exactly as in snapshot $2. Only that folder is the target, and
# its cache subfolders (excludes.txt) are left alone: neither restored nor deleted.
restore_stack() {
  sed -n "s|^/opt/appdata/$1/|/|p" /etc/resticprofile/excludes.txt >/tmp/keep
  rp restore "$2:/opt/appdata/$1" --target "/opt/appdata/$1" --delete --exclude-file /tmp/keep
}

case "${1:-}" in
backup)
  # The first backup creates the repository (restic init refuses one that exists). resticprofile's
  # own `initialize` would run before every command, restores included.
  rp cat config >/dev/null 2>&1 || rp init || true
  rp backup
  ;;
snapshots) rp snapshots ;;
check) rp prune && rp check ;;
restore)
  # Written by skynet-restore just before it starts this job: "<stack>|all <snapshot>".
  req=/opt/appdata/backup/restore.request
  if [ -z "$(find "$req" -mmin -10 2>/dev/null)" ]; then
    echo "restore: no fresh $req; skynet-restore writes it" >&2
    exit 1
  fi
  read -r stack snap <"$req"
  rm -f "$req"
  if [ "$stack" = all ]; then
    stack=$(rp ls "$snap" /opt/appdata | sed -n 's|^/opt/appdata/\([^/]*\)$|\1|p')
  fi
  for s in $stack; do restore_stack "$s" "$snap"; done
  ;;
diff) # how many entries under /opt/appdata/<stack> each snapshot changed
  prev=
  for id in $(rp snapshots --compact | grep -oE '^[0-9a-f]{8}'); do
    [ -n "$prev" ] && echo "$id: $(rp diff "$prev" "$id" | grep -c " /opt/appdata/$2/" || true)"
    prev=$id
  done
  ;;
restore-to) rp restore "$3:/opt/appdata/$2" --target "$4" ;;
*)
  echo "usage: run.sh backup|check|restore|snapshots|diff <stack>|restore-to <stack> <snap> <dir>" >&2
  exit 2
  ;;
esac
