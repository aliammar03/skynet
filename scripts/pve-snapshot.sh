#!/usr/bin/env bash
# pve-snapshot.sh — create / rollback / delete a Proxmox guest snapshot (SKY-018 P6).
# The dumb executor half of the tofu rollback: scripts/tofu-apply.sh snapshots an eligible existing
# managed guest before an update and restores it only when the saved-plan apply itself fails.
# This script is the actuator; the rollback DECISION lives in tofu-apply.sh (a deterministic verify),
# never in the agent.
#
# TIER: T2 — VM.Snapshot / VM.Snapshot.Rollback on an eligible managed guest via the svc-ops OPERATE
# token. This helper refuses every constitutionally excluded guest even when the core token could
# technically reach its envelope. Rollback restores a just-taken point-in-time — it does NOT delete a
# guest, so it never crosses the destroy/T3 checkpoint.
#
# Auth: /opt/skynet-ops/secrets/proxmox-<core|network>.env for PVE_HOST + PVE_CACERT, and the OPERATE
# token PVE_TOKEN_OPERATE (`svc-ops@pve!operate=…`, already sops-managed alongside the readonly
# PVE_TOKEN). The read-only PVE_TOKEN cannot snapshot; if no operate token is available the script
# exits non-zero so the caller FAILS CLOSED (no snapshot = no apply = no unguarded change).
# (PVE_OPERATE_TOKEN in the environment overrides, for a one-off / test.)
#
# USAGE:
#   pve-snapshot.sh create   <node_name> <vm|lxc> <vmid> <snapname>
#   pve-snapshot.sh rollback <node_name> <vm|lxc> <vmid> <snapname>
#   pve-snapshot.sh delete   <node_name> <vm|lxc> <vmid> <snapname>
#     <node_name>  the Proxmox node name, e.g. server-proxmox-core
set -euo pipefail
op="${1:?usage: pve-snapshot.sh create|rollback|delete <node_name> <vm|lxc> <vmid> <snapname>}"
node="${2:?node_name}"; kind="${3:?vm|lxc}"; vmid="${4:?vmid}"; snap="${5:?snapname}"
case "${kind}" in vm|lxc) : ;; *) echo "pve-snapshot: kind must be vm|lxc, got ${kind}" >&2; exit 2;; esac
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
invariants="${repo_root}/invariants.json"
command -v jq >/dev/null || { echo "pve-snapshot: jq is required" >&2; exit 1; }
if jq -e --argjson v "${vmid}" '.excluded_guests.guests[] | select(.vmid == $v)' "${invariants}" >/dev/null; then
  echo "pve-snapshot: REFUSED — ${vmid} is constitutionally excluded from this automated helper" >&2
  exit 3
fi
epath="qemu"; [ "${kind}" = lxc ] && epath="lxc"

# node_name → secret suffix (server-proxmox-core → core, server-proxmox-network → network)
suffix="${node##*-}"
secret_dir="${PVE_SECRET_DIR:-/opt/skynet-ops/secrets}"
secret_file="${secret_dir}/proxmox-${suffix}.env"
{ test -r "${secret_file}" 2>/dev/null || sudo -n test -f "${secret_file}" 2>/dev/null; } || { echo "pve-snapshot: no ${secret_file}" >&2; exit 1; }
# shellcheck disable=SC1090
eval "$(cat "${secret_file}" 2>/dev/null || sudo -n cat "${secret_file}")"
: "${PVE_HOST:?}" "${PVE_CACERT:?}"
# The operate token: env override first (one-off/test), then the sops-managed PVE_TOKEN_OPERATE.
TOKEN="${PVE_OPERATE_TOKEN:-${PVE_TOKEN_OPERATE:-}}"
[ -n "${TOKEN}" ] || { echo "pve-snapshot: no operate token (PVE_TOKEN_OPERATE in ${secret_file}, or PVE_OPERATE_TOKEN in env) — the read-only token cannot snapshot" >&2; exit 1; }
[ -r "${PVE_CACERT}" ] || { echo "pve-snapshot: PVE_CACERT ${PVE_CACERT} unreadable" >&2; exit 1; }

api() { local m="$1" p="$2"; shift 2; curl -sSf --max-time 30 --cacert "${PVE_CACERT}" \
        -H "Authorization: PVEAPIToken=${TOKEN}" -X "${m}" "https://${PVE_HOST}:8006/api2/json/$p" "$@"; }

base="nodes/${node}/${epath}/${vmid}"

# Proxmox snapshot ops return a UPID task; wait for it to stop and check the exit status.
wait_task() {
  local upid="$1" i status exit
  [ -n "${upid}" ] && [ "${upid}" != null ] || return 0
  for i in $(seq 1 60); do
    status="$(api GET "nodes/${node}/tasks/${upid}/status" | jq -r '.data.status')"
    [ "${status}" = stopped ] && { exit="$(api GET "nodes/${node}/tasks/${upid}/status" | jq -r '.data.exitstatus')"
      [ "${exit}" = OK ] && return 0 || { echo "pve-snapshot: task ${upid} exited ${exit}" >&2; return 1; }; }
    sleep 2
  done
  echo "pve-snapshot: task ${upid} did not finish in time" >&2; return 1
}

case "${op}" in
  create)
    echo "==> snapshot ${kind} ${vmid} @ ${node}: ${snap}"
    # VM snapshots include RAM by default so a rollback resumes a running guest in place instead of a
    # stop/start. It is heavier (writes RAM to disk), but matches the documented rollback semantics.
    vmstate_arg=()
    [ "${PVE_SNAPSHOT_VMSTATE:-1}" = 1 ] && [ "${kind}" = vm ] && vmstate_arg=(--data-urlencode "vmstate=1")
    upid="$(api POST "${base}/snapshot" --data-urlencode "snapname=${snap}" \
            "${vmstate_arg[@]}" \
            --data-urlencode "description=SKY-018 P6 pre-tofu-apply safety snapshot" | jq -r '.data')"
    wait_task "${upid}"
    ;;
  rollback)
    echo "==> ROLLBACK ${kind} ${vmid} @ ${node} to ${snap}"
    upid="$(api POST "${base}/snapshot/${snap}/rollback" | jq -r '.data')"
    wait_task "${upid}"
    ;;
  delete)
    echo "==> prune snapshot ${snap} on ${kind} ${vmid} @ ${node}"
    upid="$(api DELETE "${base}/snapshot/${snap}" | jq -r '.data')"
    wait_task "${upid}"
    ;;
  *) echo "pve-snapshot: unknown op ${op}" >&2; exit 2;;
esac
