# skynet-restore: puts a stack's /opt/appdata folder back, from a local btrfs snapshot (docker-dmz)
# or from Drive (restic), with doco-cd paused so nothing restarts the stack meanwhile
# (skynetv2.md → P4 → Restores). modules/docker-host.nix sets REPO, EXCLUDES (the backup stack's
# excludes.txt), SNAPSHOTS (the snapshot folder; empty without btrbk), and ENV_FILE and RCLONE_FILE
# (the backup stack's own secrets, which sops-nix renders whole).

usage() {
  cat >&2 <<'EOF'
usage: skynet-restore list [<stack>]
       skynet-restore local <stack>|--all <snapshot> [--to <dir>]
       skynet-restore drive <stack>|--all [<snapshot>] [--to <dir>]   (default: latest)
EOF
  exit 2
}
die() {
  echo "skynet-restore: $*" >&2
  exit 1
}

[ "$(id -u)" = 0 ] || die "run it as root (sudo)"
appdata=/opt/appdata
# doco-cd starts only with this marker (modules/docker-host.nix): the host's data is in place.
ready=$appdata/.data-ready
tmp=$(mktemp -d)
stopped=$tmp/stopped
doco_paused=false
release=false

# Whatever happens, the stopped containers and doco-cd come back. A failed --all leaves a fresh host
# without the marker, so doco-cd stays held: its data isn't all there.
cleanup() {
  if [ -s "$stopped" ]; then xargs docker start <"$stopped" >/dev/null || true; fi
  if [ "$doco_paused" = true ] || [ "$release" = true ]; then
    systemctl start docker-doco-cd || true
  fi
  rm -rf "$tmp"
}
trap cleanup EXIT

exec 9>/run/skynet-restore.lock
flock -n 9 || die "another restore is running"

# The backup job's repository and password. rclone gets a writable copy of its config: it saves
# refreshed tokens back.
restic_env() {
  RESTIC_PASSWORD=$(sed -n 's/^RESTIC_PASSWORD=//p' "$ENV_FILE")
  [ -n "$RESTIC_PASSWORD" ] || die "no RESTIC_PASSWORD in $ENV_FILE"
  cp "$RCLONE_FILE" "$tmp/rclone.conf"
  export RESTIC_PASSWORD RESTIC_REPOSITORY="$REPO" RESTIC_CACHE_DIR=/var/cache/skynet-restore \
    RCLONE_CONFIG="$tmp/rclone.conf"
}

name_ok() { [[ $1 =~ ^[a-z0-9][a-z0-9-]*$ ]] || die "'$1' isn't a stack name"; }

# <stack>: its cache folders, relative to its own folder. A restore neither restores nor deletes
# them.
keep() { sed -n "s|^$appdata/$1/|/|p" "$EXCLUDES" >"$tmp/keep-$1"; }

# --all | <stack>…: doco-cd paused, then the stacks' running containers stopped (every Compose
# project's for --all), caches included.
pause() {
  if systemctl is-active --quiet docker-doco-cd; then
    systemctl stop docker-doco-cd
    doco_paused=true
  fi
  if [ "$1" = --all ]; then
    docker ps -q --filter label=com.docker.compose.project
  else
    for s in "$@"; do docker ps -q --filter "label=com.docker.compose.project=$s"; done
  fi | sort -u >"$stopped"
  if [ -s "$stopped" ]; then xargs docker stop <"$stopped" >/dev/null; fi
}

source=${1:-}
[ "$#" -gt 0 ] && shift
case "$source" in
list)
  if [ -n "$SNAPSHOTS" ]; then
    echo "== local snapshots (latest: $(readlink "$SNAPSHOTS/latest" || echo none))"
    find "$SNAPSHOTS" -mindepth 1 -maxdepth 1 -name '@appdata.*' -printf '%f\n' | sort
  fi
  restic_env
  echo "== Drive ($REPO)"
  restic snapshots --compact
  if [ -n "${1:-}" ]; then
    name_ok "$1"
    echo "== entries changed in $1, per Drive snapshot"
    prev=
    for id in $(restic snapshots --compact | grep -oE '^[0-9a-f]{8}'); do
      if [ -n "$prev" ]; then echo "$id: $(restic diff "$prev" "$id" | grep -c " $appdata/$1/" || true)"; fi
      prev=$id
    done
  fi
  exit 0
  ;;
local | drive) ;;
*) usage ;;
esac

target=${1:-}
[ -n "$target" ] || usage
shift
[ "$target" = --all ] || name_ok "$target"
snap=
if [ -n "${1:-}" ] && [ "$1" != --to ]; then
  snap=$1
  shift
fi
dir=
if [ "${1:-}" = --to ]; then
  [ -n "${2:-}" ] || usage
  dir=$(realpath -m "$2")
  shift 2
fi
[ "$#" = 0 ] || usage

if [ "$source" = local ]; then
  [ -n "$SNAPSHOTS" ] || die "no local snapshots on this host"
  # Named, never "newest": after a restore, the newest is the one taken just before it.
  [ -n "$snap" ] || die "name the snapshot (skynet-restore list)"
  case "$snap" in @appdata.*) ;; *) snap=@appdata.$snap ;; esac
  src=$SNAPSHOTS/$snap
  [ -d "$src" ] || die "no local snapshot $snap"
  stacks() { find "$src" -mindepth 1 -maxdepth 1 -type d ! -name '.*' -printf '%f\n' | sort; }
  has() { [ -d "$src/$1" ]; }
else
  restic_env
  snap=${snap:-latest}
  stacks() { restic ls --long "$snap" "$appdata" | sed -n "s|^d.* $appdata/\([^/]*\)$|\1|p" | sort; }
  # restic ls prints a header line first; only the stack's own path counts.
  has() { restic ls "$snap" "$appdata/$1" | grep -q "^$appdata/$1\(/\|\$\)"; }
fi

if [ "$target" = --all ]; then
  mapfile -t list < <(stacks)
  [ "${#list[@]}" -gt 0 ] || die "$snap holds no stacks"
else
  has "$target" || die "$snap has no $target"
  list=("$target")
fi

copy() { # <stack> <into>: the stack's folder as in the snapshot
  if [ "$source" = local ]; then
    rsync -aHAX --numeric-ids "$src/$1/" "$2/"
  else
    restic restore "$snap:$appdata/$1" --target "$2"
  fi
}

if [ -n "$dir" ]; then
  for s in "${list[@]}"; do
    out=$dir
    [ "$target" != --all ] || out=$dir/$s
    mkdir -p "$out"
    copy "$s" "$out"
    echo "$s ($source $snap) → $out"
  done
  exit 0
fi

# Undo point (docker-dmz): a snapshot of what is about to be replaced. A fresh host has nothing yet.
if [ -n "$SNAPSHOTS" ] && [ -e "$ready" ]; then
  systemctl start btrbk-appdata
  undo=$(readlink "$SNAPSHOTS/latest")
fi

if [ "$target" = --all ]; then pause --all; else pause "${list[@]}"; fi

for s in "${list[@]}"; do
  keep "$s"
  mkdir -p "$appdata/$s"
  if [ "$source" = local ]; then
    # --checksum: compares contents, not just sizes and times.
    rsync -aHAX --numeric-ids --delete --checksum --exclude-from="$tmp/keep-$s" "$src/$s/" "$appdata/$s/"
  else
    restic restore "$snap:$appdata/$s" --target "$appdata/$s" --delete --exclude-file "$tmp/keep-$s"
  fi
  echo "$s: back as in $source $snap"
done

if [ -n "${undo:-}" ]; then
  echo "undo: skynet-restore local ${target} ${undo#@appdata.}"
fi

# A fresh host, every stack back: its first snapshot, so the backup job finds `latest`; then the
# marker, last, and doco-cd, started by cleanup, deploys the stacks onto their data.
if [ "$target" = --all ] && [ ! -e "$ready" ]; then
  if [ -n "$SNAPSHOTS" ]; then systemctl start btrbk-appdata; fi
  touch "$ready"
  release=true
fi
