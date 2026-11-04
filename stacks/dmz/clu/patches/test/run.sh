#!/usr/bin/env bash
# From ops: CLU's matcher on test/posts.json (matcher.py) and its filing match on named files
# (filing.py), with this checkout's apply.py, in a throwaway container of CLU's pinned image on
# docker-dmz, with no network. For a CLU update or a change to apply.py; README → Patches has the
# numbers it should print.
set -euo pipefail
patches=$(cd "$(dirname "$0")/.." && pwd)
image=$(grep -m1 -oE 'docker\.io/allaboutduncan/comic-utils-web:[^ ]+' "$patches/../compose.yaml")
tar -C "$patches" -czf - apply.py test | ssh -o BatchMode=yes skynet@10.10.100.10 "sudo sh -c '
  d=\$(mktemp -d) && tar -xzf - -C \$d && chmod -R a+rX \$d
  docker run --rm --network none -v \$d:/patches:ro --entrypoint sh $image \
    -c \"python3 -I /patches/apply.py && cd /tmp && { python3 /patches/test/matcher.py 2>/dev/null; m=\\\$?; python3 /patches/test/filing.py 2>/dev/null; exit \\\$((m | \\\$?)); }\"
  s=\$?; rm -rf \$d; exit \$s'"
