# skynet-restore: puts a stack's /opt/appdata folder back, from a local btrfs snapshot (docker-dmz)
# or from Drive (restic), with doco-cd held so nothing restarts the stack meanwhile
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
exec 9>/run/skynet-restore.lock
flock -n 9 || die "another restore is running"

appdata=/opt/appdata
# doco-cd starts only with this marker (modules/docker-host.nix): the host's data is in place. A
# restore in place takes it away first, so nothing starts doco-cd under it: not a NixOS switch,
# not a reboot.
ready=$appdata/.data-ready
# While the marker is away, that restore's record: its target, its undo snapshot, then the
# containers it stopped.
held=/var/lib/skynet/restore-held
tmp=$(mktemp -d)
stopped=$tmp/stopped
closed=false  # this run took the marker away
touched=false # this run began replacing a stack's folder

# The data whole again: the marker back, then what the held restore stopped, then doco-cd.
reopen() {
  touch "$ready"
  sed -n '3,$p' "$held" >"$stopped"
  rm "$held"
  if [ -s "$stopped" ]; then xargs docker start <"$stopped" >/dev/null; fi
  systemctl start docker-doco-cd
}

# A failure before any file changed puts the host back as it was. One after leaves the stacks
# stopped and doco-cd held, their data half one snapshot and half the other, until the same
# restore, its undo or --all succeeds. A failed --all on a fresh host writes no marker either.
cleanup() {
  rc=$?
  if [ "$rc" != 0 ] && [ -e "$held" ]; then
    if [ "$closed" = true ] && [ "$touched" = false ]; then
      reopen || true
    else
      t=$(sed -n 1p "$held")
      echo "skynet-restore: $t is only partly back: its containers stay stopped, doco-cd held, until" >&2
      echo "skynet-restore: the same restore${undo:+, its undo (skynet-restore local $t ${undo#@appdata.})} or --all succeeds." >&2
    fi
  fi
  rm -rf "$tmp"
}
trap cleanup EXIT

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

# --all | <stack>…: doco-cd stopped, then the stacks' running containers (every Compose project's
# for --all), caches included. The record lists them first, so the restore that ends the hold
# starts them again.
pause() {
  systemctl stop docker-doco-cd
  if [ "$1" = --all ]; then
    docker ps --format '{{.Names}}' --filter label=com.docker.compose.project
  else
    for s in "$@"; do docker ps --format '{{.Names}}' --filter "label=com.docker.compose.project=$s"; done
  fi | sort -u >"$stopped"
  if [ -e "$held" ]; then cat "$stopped" >>"$held"; fi
  if [ -s "$stopped" ]; then xargs docker stop <"$stopped" >/dev/null; fi
}

source=${1:-}
[ "$#" -gt 0 ] && shift
case "$source" in
list)
  if [ -e "$held" ]; then
    t=$(sed -n 1p "$held") u=$(sed -n 2p "$held")
    echo "== held: a restore of $t failed partway${u:+ (undo: skynet-restore local $t ${u#@appdata.})}"
  elif [ ! -e "$ready" ]; then
    echo "== held: no $ready (a fresh host's data isn't all back)"
  fi
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

if [ -e "$held" ]; then
  # A restore that failed partway holds this host: only it again, its undo or --all may run.
  t=$(sed -n 1p "$held")
  [ "$target" = "$t" ] || [ "$target" = --all ] ||
    die "a restore of $t failed partway and holds this host: restore it again, or undo it, first"
  undo=$(sed -n 2p "$held")
elif [ -e "$ready" ]; then
  # Undo point (docker-dmz): a snapshot of what is about to be replaced. Then the marker goes, its
  # record written first. A fresh host has neither yet.
  if [ -n "$SNAPSHOTS" ]; then
    systemctl start btrbk-appdata
    undo=$(readlink "$SNAPSHOTS/latest")
  fi
  closed=true
  mkdir -p "${held%/*}"
  printf '%s\n%s\n' "$target" "${undo:-}" >"$held"
  rm "$ready"
fi

if [ "$target" = --all ]; then pause --all; else pause "${list[@]}"; fi

for s in "${list[@]}"; do
  keep "$s"
  touched=true
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

if [ -e "$held" ]; then
  reopen
elif [ "$target" = --all ] && [ ! -e "$ready" ]; then
  # A fresh host, every stack back: its first snapshot, so the backup job finds `latest`; then the
  # marker, last, and doco-cd deploys the stacks onto their data.
  if [ -n "$SNAPSHOTS" ]; then systemctl start btrbk-appdata; fi
  touch "$ready"
  systemctl start docker-doco-cd
fi
