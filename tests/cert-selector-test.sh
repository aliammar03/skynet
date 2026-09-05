#!/usr/bin/env bash
# cert-selector-test.sh — ensure root grants select one certificate per SSH host alias.
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tmp="$(mktemp -d)"; trap 'rm -rf "${tmp}"' EXIT
pass=0; fail=0
ok() { printf '  ✓ %s\n' "$1"; pass=$((pass+1)); }
bad() { printf '  ✗ %s\n' "$1" >&2; fail=$((fail+1)); }

mkdir -p "${tmp}/.ssh/certs"
ssh-keygen -q -t ed25519 -N '' -f "${tmp}/ca" >/dev/null
ssh-keygen -q -t ed25519 -N '' -f "${tmp}/agent" >/dev/null
ssh-keygen -q -s "${tmp}/ca" -I docker-grant -n ops-root-docker-dmz -V +1h "${tmp}/agent.pub" >/dev/null
mv "${tmp}/agent-cert.pub" "${tmp}/.ssh/certs/docker-dmz-cert.pub"
ssh-keygen -q -s "${tmp}/ca" -I db-grant -n ops-root-db -V +1h "${tmp}/agent.pub" >/dev/null
mv "${tmp}/agent-cert.pub" "${tmp}/.ssh/certs/db-cert.pub"

HOME="${tmp}" bash "${REPO_DIR}/scripts/skynet-ops-ssh-certs.sh" >/dev/null
cfg="${tmp}/.ssh/config"
rg -q '^Host docker-dmz$' "${cfg}" && ok "docker grant has an exact Host stanza" || bad "docker Host stanza missing"
rg -q '^Host db$' "${cfg}" && ok "database grant has an exact Host stanza" || bad "database Host stanza missing"
! rg -q '^Match user root$' "${cfg}" && ok "no broad root Match offers every certificate" || bad "broad root Match remains"

docker_block="$(awk '/^Host docker-dmz$/{on=1} /^Host / && $0 != "Host docker-dmz"{on=0} on{print}' "${cfg}")"
printf '%s\n' "${docker_block}" | rg -q 'docker-dmz-cert\.pub' \
  && ! printf '%s\n' "${docker_block}" | rg -q 'db-cert\.pub' \
  && ok "docker alias offers only its own certificate" || bad "docker alias leaks another certificate"

echo
echo "cert-selector-test: ${pass} passed, ${fail} failed"
[ "${fail}" -eq 0 ]
