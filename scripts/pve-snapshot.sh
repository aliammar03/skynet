#!/usr/bin/env bash
# pve-snapshot.sh — create / rollback / delete a Proxmox guest snapshot (SKY-018 P6).
# The dumb executor half of the tofu rollback: scripts/tofu-apply.sh snapshots every in-pool guest a
# saved plan touches BEFORE applying, and rolls those snapshots back if the apply fails verification.
# This script is the actuator; the rollback DECISION lives in tofu-apply.sh (a deterministic verify),
# never in the agent.
#
# TIER: T2 — VM.Snapshot / VM.Snapshot.Rollback on the ops-managed pool via the svc-ops OPERATE token
# (non-destructive; access-and-trust.md). Rollback restores a just-taken point-in-time — it does NOT
# delete a guest, so it never crosses the destroy/T3 checkpoint.
#
# Auth: /opt/skynet-ops/secrets/proxmox-<core|network>.env for PVE_HOST + PVE_CACERT, and the OPERATE
# token from PVE_OPERATE_TOKEN (env, or set in that env file). The read-only PVE_TOKEN cannot snapshot;
# if no operate token is available the script exits non-zero so the caller FAILS CLOSED (no snapshot =
# no apply = no unguarded change).
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
epath="qemu"; [ "${kind}" = lxc ] && epath="lxc"

# node_name → secret suffix (server-proxmox-core → core, server-proxmox-network → network)
suffix="${node##*-}"
secret_file="/opt/skynet-ops/secrets/proxmox-${suffix}.env"
{ test -r "${secret_file}" 2>/dev/null || sudo -n test -f "${secret_file}" 2>/dev/null; } || { echo "pve-snapshot: no ${secret_file}" >&2; exit 1; }
# shellcheck disable=SC1090
eval "$(cat "${secret_file}" 2>/dev/null || sudo -n cat "${secret_file}")"
: "${PVE_HOST:?}" "${PVE_CACERT:?}"
TOKEN="${PVE_OPERATE_TOKEN:-}"
[ -n "${TOKEN}" ] || { echo "pve-snapshot: PVE_OPERATE_TOKEN not set (read-only token cannot snapshot) — set the operate token in ${secret_file} or the env" >&2; exit 1; }
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
    upid="$(api POST "${base}/snapshot" --data-urlencode "snapname=${snap}" \
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
