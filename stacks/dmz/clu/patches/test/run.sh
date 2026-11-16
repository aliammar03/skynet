#!/usr/bin/env bash
# CLU's matcher on test/posts.json (matcher.py) and its filing match on named files (filing.py),
# with this checkout's apply.py, in a throwaway container of CLU's pinned image, with no network.
# From ops it runs on docker-dmz. `--local` runs it with this machine's own Docker: CI does, when
# the stack changes (.github/workflows/clu-patches.yml), so a CLU update is tested before it
# merges. For a CLU update or a change to apply.py; README → Patches has the numbers it should
# print.
set -euo pipefail
patches=$(cd "$(dirname "$0")/.." && pwd)
image=$(grep -m1 -oE 'docker\.io/allaboutduncan/comic-utils-web:[^ ]+' "$patches/../compose.yaml")
if [ "${1:-}" = --local ]; then
  # The same commands as below, without the hop to docker-dmz.
  exec docker run --rm --network none -v "$patches:/patches:ro" --entrypoint sh "$image" \
    -c 'python3 -I /patches/apply.py && cd /tmp && { python3 /patches/test/matcher.py 2>/dev/null; m=$?; python3 /patches/test/filing.py 2>/dev/null; exit $((m | $?)); }'
fi
tar -C "$patches" -czf - apply.py test | ssh -o BatchMode=yes skynet@10.10.100.10 "sudo sh -c '
  d=\$(mktemp -d) && tar -xzf - -C \$d && chmod -R a+rX \$d
  docker run --rm --network none -v \$d:/patches:ro --entrypoint sh $image \
    -c \"python3 -I /patches/apply.py && cd /tmp && { python3 /patches/test/matcher.py 2>/dev/null; m=\\\$?; python3 /patches/test/filing.py 2>/dev/null; exit \\\$((m | \\\$?)); }\"
  s=\$?; rm -rf \$d; exit \$s'"
