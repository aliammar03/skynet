#!/usr/bin/env bash
# The admin Authelia's smoke check (skynet-verify, from ops): a password login through caddy-admin
# as the smoke checks' account, which an access rule then denies everything (configuration.yml).
# It proves what /api/health doesn't: the users file loads and a password checks out. The body is
# a file curl reads, so the password is on no command line.
set -euo pipefail
got=$(curl -sS --max-time 30 -o /dev/null -w '%{http_code}' -H 'Content-Type: application/json' \
  -d @/run/secrets/rendered/authelia-smoke.json https://auth.aliammar.net/api/firstfactor)
if [ "$got" = 200 ]; then
  echo "Authelia (admin) took the smoke account's login"
else
  echo "Authelia (admin) answered $got to the smoke account's login"
  exit 1
fi
