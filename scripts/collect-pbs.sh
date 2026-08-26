#!/usr/bin/env bash
# collect-pbs.sh — T1 read-only snapshot of Proxmox Backup Server → inventory/pbs.json
# USAGE: collect-pbs.sh
#   Reads /opt/skynet-ops/secrets/pbs.env:
#     PBS_HOST=10.10.20.40   PBS_TOKEN='svc-ops@pbs!readonly=<uuid>'
# NOTE (finding, 2026-08-15): PBS:8007 was unreachable during A1 env checks — verify
#   reachability before relying on this collector (A4).
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
secret="/opt/skynet-ops/secrets/pbs.env"

if ! { test -e "${secret}" 2>/dev/null || sudo -n test -f "${secret}" 2>/dev/null; }; then
  echo "no creds yet (${secret}) — collector idle until A2/A4" >&2
  exit 0
fi
# shellcheck disable=SC1090
eval "$(cat "${secret}" 2>/dev/null || sudo -n cat "${secret}")"
: "${PBS_HOST:?}" "${PBS_TOKEN:?}"
: "${PBS_CACERT:?set PBS_CACERT in ${secret} — run: scripts/pin-cert.sh ${PBS_HOST:-<host>} 8007 /opt/skynet-ops/certs/pbs.crt}"
[ -r "${PBS_CACERT}" ] || { echo "PBS_CACERT ${PBS_CACERT} not readable" >&2; exit 1; }

if ! timeout 5 bash -c "</dev/tcp/${PBS_HOST}/8007" 2>/dev/null; then
  echo "PBS ${PBS_HOST}:8007 unreachable — see A1 finding; not writing inventory" >&2
  exit 1
fi

api() { curl -sSf --max-time 15 --cacert "${PBS_CACERT}" -H "Authorization: PBSAPIToken=${PBS_TOKEN}" \
        "https://${PBS_HOST}:8007/api2/json/$1"; }

out="${REPO_DIR}/inventory/pbs.json"
jq -n \
  --argjson datastores "$(api admin/datastore | jq '.data')" \
  --arg ts "$(date -Iseconds)" \
  '{collected:$ts, datastores:$datastores}' > "${out}"
echo "wrote ${out}"
