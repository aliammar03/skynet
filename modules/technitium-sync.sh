# shellcheck shell=bash
# technitium-sync: applies dns/ to the local Technitium through its HTTP API (skynetv2.md → P2):
# the settings, then the aliammar.net zone, replaced whole by the file, then the SSO login if SSO
# is set. Idempotent. modules/dns.nix runs it at boot and on every deploy that changes dns/. By
# hand, e.g. against a test server:
#   API=http://127.0.0.1:15380/api PASSWORD_FILE=… SETTINGS=dns/settings.json \
#     ZONE_FILE=dns/aliammar.net.zone [SSO=dns/sso.json SSO_CLIENT_ID=… SSO_SECRET_FILE=…] \
#     bash modules/technitium-sync.sh
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

# Technitium takes a few seconds to answer after a start, and after it restarts its web service
# (an SSO change, below).
wait_up() {
  local tries=0
  until curl -fso /dev/null "${api%/api}/"; do
    ((++tries < 60)) || {
      echo "technitium-sync: no answer from $api in 60 s" >&2
      exit 1
    }
    sleep 1
  done
}

wait_up

# The password goes to curl on stdin, URL-encoded; Technitium reads only the file's first line too.
pass=$(head -n1 "$PASSWORD_FILE" | jq -Rr @uri)
token=$(printf 'user=admin&pass=%s' "$pass" | call user/login --data @- | jq -r .token)
printf 'Authorization: Bearer %s\n' "$token" >"$auth"

# Only the keys in settings.json change, and each must read back as written.
call settings/set -H 'Content-Type: application/json' --data-binary @"$SETTINGS" |
  jq -e --slurpfile want "$SETTINGS" '.response as $have
    | [$want[0] | to_entries[] | select(.value != $have[.key]) | .key]
    | if . == [] then true else ("settings not applied: \(join(", "))\n" | halt_error(1)) end' >/dev/null

type=$(call "zones/list?filterName=$zone" | jq -r --arg z "$zone" '.response.zones[] | select(.name == $z) | .type')
case $type in
  Primary) ;;
  "") call zones/create --data "zone=$zone&type=Primary" >/dev/null ;;
  *) call zones/convert --data "zone=$zone&type=Primary" >/dev/null ;; # e.g. the old Forwarder zone
esac
# The file is the whole zone, SOA and NS lines included: a record missing from it is deleted.
call "zones/import?zone=$zone&overwriteZone=true" -H 'Content-Type: text/plain' \
  --data-binary @"$ZONE_FILE" >/dev/null

# The login through admin Authelia (dns/sso.json): this server's client ID and secret beside the
# file's keys, the secret on stdin. Technitium compares each value and restarts its web service 2 s
# after a change, so the read-back waits that out; it shows the secret only as set or not.
if [[ -n ${SSO:-} ]]; then
  jq -j --arg id "$SSO_CLIENT_ID" --rawfile secret "$SSO_SECRET_FILE" '
    {ssoEnabled, ssoAuthority, ssoClientId: $id, ssoClientSecret: ($secret | split("\n")[0]),
     ssoScopes: (.ssoScopes | join("|")), ssoAllowSignup, ssoAllowSignupOnlyForMappedUsers,
     ssoGroupMap: ([.ssoGroupMap | to_entries[] | .key, .value] | join("|"))}
    | to_entries | map("\(.key)=\(.value | tostring | @uri)") | join("&")' "$SSO" |
    call admin/sso/set --data @- >/dev/null
  sleep 3
  wait_up
  call admin/sso/get | jq -e --slurpfile want "$SSO" --arg id "$SSO_CLIENT_ID" '.response as $have
    | ($want[0] + {ssoClientId: $id}) as $w
    | [$w | keys[] | select(. as $k
        | if $k == "ssoScopes" then ($have[$k] | sort) != ($w[$k] | sort)
          elif $k == "ssoGroupMap" then
            ($have[$k] | map({(.remoteGroup): .localGroup}) | add // {}) != $w[$k]
          else $have[$k] != $w[$k] end)]
      + (if $have.ssoClientSecret == "************" then [] else ["ssoClientSecret"] end)
    | if . == [] then true else ("sso not applied: \(join(", "))\n" | halt_error(1)) end' >/dev/null
fi

call user/logout >/dev/null
echo "technitium-sync: settings, $zone${SSO:+ and the SSO login} applied"
