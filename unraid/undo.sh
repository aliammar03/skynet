#!/bin/bash
# skynet-undo: a dated copy of each share the lab can write or delete (PBS's datastore; Storage),
# kept on the same array disk in a share of its own, `undo-<share>`, which the lab can at most read
# (skynetv2.md → P6 → The undo out of reach). A User Script on Unraid, nightly; unraid/README.md
# has the install.
#
# A copy shares its files' data with the original, so it costs space only for what the original
# later deletes or replaces:
#   link     a hard link per file. Holds whatever is deleted or replaced by a new file. PBS never
#            rewrites a chunk or an index, so its datastore is whole in every copy.
#   reflink  a copy-on-write copy per file, which also holds a file rewritten in place. It needs
#            XFS made with reflinks; a disk without them gets hard links, and the log line says so.
set -u
KEEP=${KEEP:-14} # dated copies kept of each share
SHARES=${SHARES:-"pbs:link Storage:reflink"}
ROOTS=${ROOTS:-/mnt/disk[0-9]*} # array disks only: a copy on the pool would pin there what the mover moves

log() {
  logger -t skynet-undo -- "$*" 2>/dev/null
  echo "skynet-undo: $*"
}

day=$(date +%F)
rc=0
found=0
for fs in $ROOTS; do
  [ -d "$fs" ] || continue
  ok=1
  for entry in $SHARES; do
    share=${entry%%:*}
    mode=${entry##*:}
    src=$fs/$share
    # No such share on this disk, or an empty one (an unmounted disk): nothing to copy.
    [ -d "$src" ] && [ -n "$(ls -A "$src" 2>/dev/null)" ] || continue
    found=1
    dest=$fs/undo-$share
    [ -e "$dest/$day" ] && continue # today's is there already
    mkdir -p "$dest" || { ok=0; continue; }
    if [ "$mode" = reflink ]; then
      probe=$dest/.probe
      : >"$probe"
      cp --reflink=always "$probe" "$probe.2" 2>/dev/null || mode="link"
      rm -f "$probe" "$probe.2"
    fi
    flag=-al
    [ "$mode" = reflink ] && flag="-a --reflink=always"
    # Under a .partial name until it's whole, so a failed run never counts as a copy. A file that
    # goes away mid-copy (PBS renames its temporary files into place) isn't a failure.
    rm -rf "$dest/.partial"
    # shellcheck disable=SC2086
    errs=$(cp $flag "$src" "$dest/.partial" 2>&1 | grep -v 'No such file or directory' | head -n 5)
    if [ -z "$errs" ] && mv "$dest/.partial" "$dest/$day"; then
      log "$src: copied ($mode) to undo-$share/$day"
    else
      log "$src: FAILED: ${errs:-rename}"
      rm -rf "$dest/.partial"
      ok=0
      continue
    fi
    # Old copies go only after a good copy: a failing job, or one that finds nothing to copy, never
    # deletes its way to none.
    find "$dest" -mindepth 1 -maxdepth 1 -type d -name '20[0-9][0-9]-[0-9][0-9]-[0-9][0-9]' |
      sort | head -n -"$KEEP" | while IFS= read -r old; do
      rm -rf "$old" && log "$old: removed (older than the newest $KEEP)"
    done
  done
  [ "$ok" = 1 ] || rc=1
done
[ "$found" = 1 ] || {
  log "FAILED: no share to copy (is the array started?)"
  exit 1
}
[ "$rc" = 0 ] && log "done"
exit "$rc"
