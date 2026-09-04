#!/usr/bin/env bash
# collect-proxmox-acl.sh — T1 snapshot of the OPERATE token's OWN effective permissions on a node →
#   inventory/proxmox-<node>-acl.json. Read-only self-introspection: a token can always read its own
#   /access/permissions, so this never needs more than the operate token already holds, and mutates
#   nothing. Feeds the ACL-audit invariant (SKY-021): check-invariants.sh asserts this snapshot
#   carries none of the bright-line privileges and no network-node self-provisioning creep — so a
#   silent widening of the agent's own Proxmox leash (a /vms grant on network, a Permissions.Modify
#   anywhere) is caught by a NON-LLM gate, not by the agent remembering.
# USAGE: collect-proxmox-acl.sh <core|network>
#   Reads PVE_TOKEN_OPERATE from /opt/skynet-ops/secrets/proxmox-<node>.env (the same operate token
#   pve-snapshot.sh uses). Idles cleanly if there is no operate token on that node.
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
node="${1:?usage: collect-proxmox-acl.sh <core|network>}"
secret_file="/opt/skynet-ops/secrets/proxmox-${node}.env"

if ! { test -e "${secret_file}" 2>/dev/null || sudo -n test -f "${secret_file}" 2>/dev/null; }; then
  echo "no creds yet (${secret_file}) — acl collector idle" >&2; exit 0
fi
# shellcheck disable=SC1090
eval "$(cat "${secret_file}" 2>/dev/null || sudo -n cat "${secret_file}")"
: "${PVE_HOST:?}" "${PVE_CACERT:?}"
TOKEN="${PVE_TOKEN_OPERATE:-}"
if [ -z "${TOKEN}" ]; then
  echo "no operate token on ${node} (PVE_TOKEN_OPERATE) — nothing to audit; idle" >&2; exit 0
fi
[ -r "${PVE_CACERT}" ] || { echo "PVE_CACERT ${PVE_CACERT} not readable" >&2; exit 1; }

# The token id (svc-ops@pve!operate) — the subject of the audit, recorded so the checker/report can
# name what it verified. /access/permissions returns THIS caller's effective perms, path → {priv:1}.
tokenid="${TOKEN%%=*}"
perms="$(curl -sSf --max-time 15 --cacert "${PVE_CACERT}" -H "Authorization: PVEAPIToken=${TOKEN}" \
          "https://${PVE_HOST}:8006/api2/json/access/permissions" | jq '.data')"

out="${REPO_DIR}/inventory/proxmox-${node}-acl.json"
# Canonical node name (server-proxmox-core / -network) — matches invariants.json + excluded_guests,
# so the ACL-audit gate compares like-for-like (its <core|network> arg is only the file suffix).
jq -n --arg node "server-proxmox-${node}" --arg token "${tokenid}" --arg ts "$(date -Iseconds)" \
      --argjson permissions "${perms}" \
  '{node:$node, token:$token, collected:$ts, permissions:$permissions}' > "${out}"
echo "wrote ${out}"
