#!/usr/bin/env bash
# The apps' Authelia's smoke check (skynet-verify, from ops): a password login through caddy-apps
# as the smoke checks' account, which an access rule then denies everything (configuration.yml).
# It proves what /api/health doesn't: the users file loads, a password checks out, and the session
# reaches Redis. The body is a file curl reads, so the password is on no command line.
set -euo pipefail
got=$(curl -sS --max-time 30 -o /dev/null -w '%{http_code}' -H 'Content-Type: application/json' \
  -d @/run/secrets/rendered/authelia-smoke.json https://login.aliammar.net/api/firstfactor)
if [ "$got" = 200 ]; then
  echo "Authelia (apps) took the smoke account's login"
else
  echo "Authelia (apps) answered $got to the smoke account's login"
  exit 1
fi
