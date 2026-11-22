#!/usr/bin/env bash
# Uchiyomi's smoke check (skynet-verify, from ops): a login as the agent's account (ADR-0016), then
# a book's first page the way its reader loads it, with the session's cookie. It proves what
# /healthz doesn't: logins, the library's listing, and a page off Unraid's share. The token and the
# cookie stay in a private folder, removed after.
set -euo pipefail
base=https://uchiyomi.aliammar.net
d=$(mktemp -d)
trap 'rm -rf "$d"' EXIT
umask 077
curl -fsS --max-time 30 -c "$d/jar" -H 'Content-Type: application/json' \
  -d @/run/secrets/rendered/uchiyomi-login.json "$base/auth/login" | jq -r '.accessToken // empty' >"$d/token"
[ -s "$d/token" ] || {
  echo "Uchiyomi refused the login"
  exit 1
}
printf 'Authorization: Bearer %s\n' "$(cat "$d/token")" >"$d/auth"
sid=$(curl -fsS --max-time 30 -H @"$d/auth" -H 'Content-Type: application/json' -d '{"query":""}' \
  "$base/api/series/search?adult=1" | jq -r '.content[0].id // empty')
bid=
[ -z "$sid" ] || bid=$(curl -fsS --max-time 30 -H @"$d/auth" "$base/api/series/$sid/books?size=1&page=0" | jq -r '.content[0].id // empty')
[ -n "$bid" ] || {
  echo "Uchiyomi lists no book"
  exit 1
}
got=$(curl -fsS --max-time 60 -b "$d/jar" -o /dev/null -w '%{content_type} %{size_download}' "$base/img/books/$bid/page/1")
case "$got" in
image/*) echo "Uchiyomi served page 1 of book $bid (${got% *}, ${got#* } bytes)" ;;
*)
  echo "page 1 of book $bid came as ${got% *}"
  exit 1
  ;;
esac
