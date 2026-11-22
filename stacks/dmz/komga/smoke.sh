#!/usr/bin/env bash
# Komga's smoke check (skynet-verify, from ops): the newest book's first page, through caddy-apps
# as the agent's account (ADR-0016). It proves what /actuator/health doesn't: the database lists
# books, and the library on Unraid's share serves a page.
set -euo pipefail
netrc=/run/secrets/rendered/komga.netrc
api=https://komga.aliammar.net/api/v1
id=$(curl -fsS --max-time 30 --netrc-file "$netrc" "$api/books?size=1&sort=lastModified,desc" | jq -r '.content[0].id // empty')
[ -n "$id" ] || {
  echo "Komga lists no book"
  exit 1
}
got=$(curl -fsS --max-time 60 --netrc-file "$netrc" -o /dev/null -w '%{content_type} %{size_download}' "$api/books/$id/pages/1")
case "$got" in
image/*) echo "Komga served page 1 of book $id (${got% *}, ${got#* } bytes)" ;;
*)
  echo "page 1 of book $id came as ${got% *}"
  exit 1
  ;;
esac
