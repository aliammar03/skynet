# shellcheck shell=bash
# technitium-sync: applies dns/ to the local Technitium through its HTTP API (skynetv2.md → P2):
# the settings, then the aliammar.net zone, replaced whole by the file. Idempotent. modules/dns.nix
# runs it at boot and on every deploy that changes dns/. By hand, e.g. against a test server:
#   API=http://127.0.0.1:15380/api PASSWORD_FILE=… SETTINGS=dns/settings.json \
#     ZONE_FILE=dns/aliammar.net.zone bash modules/technitium-sync.sh
set -euo pipefail
api=${API:-http://127.0.0.1:5380/api}
zone=aliammar.net
auth=$(mktemp) # the session token as a header file, so it's never on a command line
trap 'rm -f "$auth"' EXIT

# call ENDPOINT [curl args…]: prints the response; fails with Technitium's message unless its
# status is ok (the API answers errors with HTTP 200).
call() {
  local endpoint=$1
  shift
  curl -fsS -H @"$auth" "$@" "$api/$endpoint" |
    jq -e 'if .status == "ok" then . else ("\(.status): \(.errorMessage // "")\n" | halt_error(1)) end'
}

tries=0
until curl -fso /dev/null "${api%/api}/"; do # it takes a few seconds to answer after a start
  ((++tries < 60)) || {
    echo "technitium-sync: no answer from $api in 60 s" >&2
    exit 1
  }
  sleep 1
done

# The password goes to curl on stdin, URL-encoded; Technitium reads only the file's first line too.
pass=$(head -n1 "$PASSWORD_FILE" | jq -Rr @uri)
token=$(printf 'user=admin&pass=%s' "$pass" | call user/login --data @- | jq -r .token)
printf 'Authorization: Bearer %s\n' "$token" >"$auth"

# Only the keys in settings.json change, and each must read back as written.
call settings/set -H 'Content-Type: application/json' --data-binary @"$SETTINGS" |
  jq -e --slurpfile want "$SETTINGS" '.response as $have
    | [$want[0] | to_entries[] | select(.value != $have[.key]) | .key]
    | if . == [] then true else ("settings not applied: \(join(", "))\n" | halt_error(1)) end' >/dev/null

zones=$(call "zones/list?filterName=$zone")
if ! jq -e --arg z "$zone" 'any(.response.zones[]; .name == $z)' <<<"$zones" >/dev/null; then
  call zones/create --data "zone=$zone&type=Forwarder&forwarder=this-server" >/dev/null
fi
# The file is the whole zone, SOA and FWD lines included: a record missing from it is deleted.
call "zones/import?zone=$zone&overwriteZone=true" -H 'Content-Type: text/plain' \
  --data-binary @"$ZONE_FILE" >/dev/null

call user/logout >/dev/null
echo "technitium-sync: settings and $zone applied"
