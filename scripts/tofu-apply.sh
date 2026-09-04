#!/usr/bin/env bash
# tofu-apply.sh — health-gated OpenTofu apply with snapshot-before-apply and automatic rollback
# (SKY-018 P6). The highest-blast-radius actuator in the lab gets the dumb rollback ADR 0005 §3 wants:
#
#   1. Apply ONLY a SAVED plan (never re-plan at apply time — the reviewed diff is the one that runs).
#   2. REFUSE any plan containing a `delete`/replace action, or touching a T3 excluded guest, OUTRIGHT.
#      destroy stays a hard checkpoint at every autonomy level — this wrapper never performs one.
#   3. Snapshot every in-pool guest the plan touches BEFORE applying. Fail closed: a guest that can't
#      be snapshotted means no guaranteed rollback → refuse to apply. This deliberately blocks a
#      new-guest create: the planned VMID does not exist yet and therefore has no rollback snapshot.
#   4. Apply the saved plan, then VERIFY deterministically (post-apply plan is clean; plus an optional
#      external check). The verdict is an exit code, not the agent's opinion.
#   5. On apply-or-verify failure, roll every snapshot back (scripts/pve-snapshot.sh) and exit non-zero.
#      On success, prune the safety snapshots.
#
# TIER: T2 — svc-ops!operate applies on the managed envelope and takes safety snapshots.
# USAGE:
#   tofu-apply.sh <planfile>            # apply a plan saved with: tofu plan -out <planfile>
# ENV (optional; the failure-case test injects through these):
#   TOFU_BIN         tofu binary (default: tofu)               TOFU_DIR   tofu root (default: repo tofu/)
#   PVE_SNAPSHOT     snapshot helper (default: scripts/pve-snapshot.sh)
#   TOFU_APPLY_VERIFY  extra verify command; non-zero ⇒ rollback (default: post-apply plan must be clean)
#   TOFU_APPLY_SKIP_ENV=1  skip sourcing tofu-env.sh (creds already in env / test)
set -euo pipefail
PLAN="${1:?usage: tofu-apply.sh <planfile>  (a plan saved via: tofu plan -out <planfile>)}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOFU_DIR="${TOFU_DIR:-${REPO_ROOT}/tofu}"
TOFU_BIN="${TOFU_BIN:-tofu}"
PVE_SNAPSHOT="${PVE_SNAPSHOT:-${REPO_ROOT}/scripts/pve-snapshot.sh}"
INVARIANTS="${REPO_ROOT}/invariants.json"
GUEST_TYPES='proxmox_virtual_environment_vm proxmox_virtual_environment_container'

[ -f "${PLAN}" ] || { echo "tofu-apply: saved plan '${PLAN}' not found — create it with 'tofu plan -out ${PLAN}'" >&2; exit 1; }
command -v jq >/dev/null || { echo "tofu-apply: jq required" >&2; exit 1; }

cd "${TOFU_DIR}"
if [ "${TOFU_APPLY_SKIP_ENV:-0}" != 1 ]; then
  eval "$("${REPO_ROOT}/scripts/tofu-env.sh")"
fi

# --- inspect the SAVED plan (never re-plan) -------------------------------------------------------
PLAN_JSON="$("${TOFU_BIN}" show -json "${PLAN}")"
excluded="$(jq -r '.excluded_guests.guests[].vmid' "${INVARIANTS}" | tr '\n' ' ')"

# 1. destroy/delete guard — any delete (incl. replace = delete+create) is a hard checkpoint, refused.
deletes="$(printf '%s' "${PLAN_JSON}" | jq -r '
  [.resource_changes[]? | select(.change.actions | index("delete")) | .address] | join(", ")')"
if [ -n "${deletes}" ]; then
  echo "tofu-apply: REFUSED — plan contains delete/replace actions (a hard checkpoint, never auto-applied):" >&2
  echo "            ${deletes}" >&2
  echo "            destroy/delete is human-run at every autonomy level (ADR 0005 §3)." >&2
  exit 3
fi

# 2. collect guests the plan changes (create/update, not no-op) → (kind vmid node) triples.
# A create reaches the snapshot preflight below and fails closed because the VMID does not exist.
mapfile -t guest_rows < <(printf '%s' "${PLAN_JSON}" | jq -r --arg types "${GUEST_TYPES}" '
  ($types | split(" ")) as $gt
  | .resource_changes[]?
  | select(.type as $t | $gt | index($t))
  | select(.change.actions | (index("create") or index("update")))
  | (.change.after // .change.before) as $v
  | "\(if .type=="proxmox_virtual_environment_container" then "lxc" else "vm" end)\t\($v.vm_id)\t\($v.node_name)"')

# 3. excluded-guest guard — this wrapper never auto-touches a T3 guest (run those by hand).
for row in "${guest_rows[@]:-}"; do
  [ -n "${row}" ] || continue
  vmid="$(printf '%s' "${row}" | cut -f2)"
  case " ${excluded} " in *" ${vmid} "*)
    echo "tofu-apply: REFUSED — plan touches T3 excluded guest ${vmid}; run this apply manually." >&2; exit 3;; esac
done

SNAP="sky018-p6-preapply-$(date +%Y%m%d-%H%M%S)"
declare -a TAKEN=()   # "kind vmid node" for each snapshot successfully taken

rollback_all() {
  local r kind vmid node
  for r in "${TAKEN[@]:-}"; do
    [ -n "${r}" ] || continue
    read -r kind vmid node <<< "${r}"
    "${PVE_SNAPSHOT}" rollback "${node}" "${kind}" "${vmid}" "${SNAP}" || echo "tofu-apply: rollback of ${vmid} FAILED — manual recovery needed" >&2
  done
}
prune_all() {
  local r kind vmid node
  for r in "${TAKEN[@]:-}"; do
    [ -n "${r}" ] || continue
    read -r kind vmid node <<< "${r}"
    "${PVE_SNAPSHOT}" delete "${node}" "${kind}" "${vmid}" "${SNAP}" || true
  done
}

# 4. snapshot every touched guest FIRST (fail closed: no snapshot ⇒ no apply).
for row in "${guest_rows[@]:-}"; do
  [ -n "${row}" ] || continue
  read -r kind vmid node <<< "$(printf '%s' "${row}")"
  if "${PVE_SNAPSHOT}" create "${node}" "${kind}" "${vmid}" "${SNAP}"; then
    TAKEN+=("${kind} ${vmid} ${node}")
  else
    echo "tofu-apply: could not snapshot ${kind} ${vmid} @ ${node} — refusing to apply without a rollback point." >&2
    prune_all
    exit 4
  fi
done
[ "${#TAKEN[@]}" -gt 0 ] && echo "==> snapshotted ${#TAKEN[@]} guest(s) as ${SNAP}" || echo "==> no in-pool guests touched — nothing to snapshot"

# 5. apply the SAVED plan; on failure, roll back.
echo "==> applying saved plan ${PLAN}"
if ! "${TOFU_BIN}" apply -auto-approve "${PLAN}"; then
  echo "tofu-apply: apply FAILED — rolling back snapshots" >&2
  rollback_all
  exit 5
fi

# 6. verify deterministically: post-apply plan must be clean (exit 0); optional extra check.
echo "==> verifying (post-apply plan must be clean)"
verify_ok=1
"${TOFU_BIN}" plan -detailed-exitcode -no-color >/dev/null 2>&1 || verify_ok=0
if [ -n "${TOFU_APPLY_VERIFY:-}" ]; then
  eval "${TOFU_APPLY_VERIFY}" || verify_ok=0
fi
if [ "${verify_ok}" != 1 ]; then
  echo "tofu-apply: verification FAILED — rolling back snapshots" >&2
  rollback_all
  exit 6
fi

echo "==> apply verified clean — pruning safety snapshots"
prune_all
echo "tofu-apply: OK"
