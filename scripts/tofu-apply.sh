#!/usr/bin/env bash
# tofu-apply.sh — saved-plan OpenTofu apply with automatic snapshot rollback for existing guests
# (SKY-018 P6). The guest actuator gets the dumb rollback ADR 0005 §3 wants; non-guest resources
# still receive the plan/delete/verification guards but have no automatic inverse:
#
#   1. Apply ONLY a SAVED plan (never re-plan at apply time — the reviewed diff is the one that runs).
#   2. REFUSE any plan containing a `delete`/replace action, or touching a T3 excluded guest, OUTRIGHT.
#      destroy stays a hard checkpoint at every autonomy level — this wrapper never performs one.
#   3. Snapshot every existing guest UPDATE before applying. Fail closed if an update cannot be
#      snapshotted. A guest CREATE has no pre-change object, so it runs only as a supervised T2
#      saved-plan action and is never represented as automatically rollback-safe/A4.
#   4. Apply the saved plan, then VERIFY deterministically (post-apply plan is clean; plus an optional
#      external check). The verdict is an exit code, not the agent's opinion.
#   5. On apply failure, restore every existing-guest snapshot and the pre-apply OpenTofu state. A
#      post-apply verification failure preserves the snapshots and stops for operator recovery: an
#      unavailable verifier is not permission to discard guest writes. Created guests and non-guest
#      changes always require operator recovery. On success, prune safety snapshots.
#
# TIER: T2 — svc-ops!operate applies on the managed envelope and takes safety snapshots.
# USAGE:
#   tofu-apply.sh <planfile>            # apply a plan saved with: tofu plan -out <planfile>
# ENV (optional; the failure-case test injects through these):
#   TOFU_BIN         tofu binary (default: tofu)               TOFU_DIR   tofu root (default: repo tofu/)
#   PVE_SNAPSHOT     snapshot helper (default: scripts/pve-snapshot.sh)
#   TOFU_APPLY_VERIFY  extra verify command; non-zero retains snapshots for operator recovery
#   TOFU_APPLY_SCOPE  required one-actuator scope: proxmox-core|proxmox-network|technitium-dns|cloudflare-dns
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
PLAN="$(cd "$(dirname "${PLAN}")" && pwd)/$(basename "${PLAN}")"
command -v jq >/dev/null || { echo "tofu-apply: jq required" >&2; exit 1; }

cd "${TOFU_DIR}"
if [ "${TOFU_APPLY_SKIP_ENV:-0}" != 1 ]; then
  # A saved plan needs only the encrypted-state passphrase to be inspected. Load the one matching
  # actuator credential after its scope is proven below, rather than every standing T2 secret.
  eval "$("${REPO_ROOT}/scripts/tofu-env.sh" state)"
fi

# --- inspect the SAVED plan (never re-plan) -------------------------------------------------------
PLAN_JSON="$("${TOFU_BIN}" show -json "${PLAN}")"
excluded="$(jq -r '.excluded_guests.guests[].vmid' "${INVARIANTS}" | tr '\n' ' ')"

# A saved plan can carry unrelated drift from this legacy shared tofu root. Require the operator to
# name one actuator and reject a mixed or mismatched plan before it reaches apply.
scope="${TOFU_APPLY_SCOPE:-}"
case "${scope}" in proxmox-core|proxmox-network|technitium-dns|cloudflare-dns) : ;;
  *) echo "tofu-apply: TOFU_APPLY_SCOPE is required (proxmox-core|proxmox-network|technitium-dns|cloudflare-dns)" >&2; exit 2;; esac
mapfile -t plan_scopes < <(printf '%s' "${PLAN_JSON}" | jq -r '
  [.resource_changes[]?
   | select(.change.actions | any(. != "no-op"))
   | if .type == "proxmox_virtual_environment_vm" or .type == "proxmox_virtual_environment_container" then
       ((.change.after // .change.before).node_name
        | if . == "server-proxmox-core" then "proxmox-core"
          elif . == "server-proxmox-network" then "proxmox-network"
          else "unknown-proxmox" end)
     elif .type == "technitium_record" then "technitium-dns"
     elif .type == "cloudflare_dns_record" then "cloudflare-dns"
     else "unknown" end]
  | unique[]')
if [ "${#plan_scopes[@]}" -ne 1 ] || [ "${plan_scopes[0]:-}" != "${scope}" ]; then
  echo "tofu-apply: REFUSED — saved plan scope [${plan_scopes[*]:-no changes}] does not exactly match TOFU_APPLY_SCOPE=${scope}" >&2
  exit 2
fi
if [ "${TOFU_APPLY_SKIP_ENV:-0}" != 1 ]; then
  eval "$("${REPO_ROOT}/scripts/tofu-env.sh" "${scope}")"
fi

# 1. destroy/delete guard — any delete (incl. replace = delete+create) is a hard checkpoint, refused.
deletes="$(printf '%s' "${PLAN_JSON}" | jq -r '
  [.resource_changes[]? | select(.change.actions | index("delete")) | .address] | join(", ")')"
if [ -n "${deletes}" ]; then
  echo "tofu-apply: REFUSED — plan contains delete/replace actions (a hard checkpoint, never auto-applied):" >&2
  echo "            ${deletes}" >&2
  echo "            destroy/delete is human-run at every autonomy level (ADR 0005 §3)." >&2
  exit 3
fi

# 2. collect guests the plan changes (create/update, not no-op) → (action kind vmid node) rows.
mapfile -t guest_rows < <(printf '%s' "${PLAN_JSON}" | jq -r --arg types "${GUEST_TYPES}" '
  ($types | split(" ")) as $gt
  | .resource_changes[]?
  | select(.type as $t | $gt | index($t))
  | select(.change.actions | (index("create") or index("update")))
  | (.change.after // .change.before) as $v
  | "\(if (.change.actions | index("create")) then "create" else "update" end)\t\(if .type=="proxmox_virtual_environment_container" then "lxc" else "vm" end)\t\($v.vm_id)\t\($v.node_name)"')

# 3. excluded-guest guard — this wrapper never auto-touches a T3 guest (run those by hand).
for row in "${guest_rows[@]:-}"; do
  [ -n "${row}" ] || continue
  vmid="$(printf '%s' "${row}" | cut -f3)"
  case " ${excluded} " in *" ${vmid} "*)
    echo "tofu-apply: REFUSED — plan touches T3 excluded guest ${vmid}; stop for its privileged path." >&2; exit 3;; esac
done

SNAP="sky018-p6-preapply-$(date +%Y%m%d-%H%M%S)"
declare -a TAKEN=()   # "kind vmid node" for each snapshot successfully taken
STATE_BACKUP="$(mktemp)"
STATE_BACKUP_TAKEN=0
trap 'rm -f "${STATE_BACKUP}"' EXIT

rollback_all() {
  local r kind vmid node failed=0
  for r in "${TAKEN[@]:-}"; do
    [ -n "${r}" ] || continue
    read -r kind vmid node <<< "${r}"
    if ! "${PVE_SNAPSHOT}" rollback "${node}" "${kind}" "${vmid}" "${SNAP}"; then
      echo "tofu-apply: rollback of ${vmid} FAILED — manual recovery needed" >&2
      failed=1
    fi
  done
  return "${failed}"
}
prune_all() {
  local r kind vmid node
  for r in "${TAKEN[@]:-}"; do
    [ -n "${r}" ] || continue
    read -r kind vmid node <<< "${r}"
    "${PVE_SNAPSHOT}" delete "${node}" "${kind}" "${vmid}" "${SNAP}" || true
  done
}
restore_state() {
  [ "${STATE_BACKUP_TAKEN}" = 1 ] || return 0
  # Apply increments the local-state serial; restoring the pre-apply snapshot therefore requires an
  # explicit state-only force push after the matching Proxmox rollback.
  "${TOFU_BIN}" state push -force "${STATE_BACKUP}" \
    || { echo "tofu-apply: OpenTofu state restore FAILED — manual recovery needed" >&2; return 1; }
}
recover_apply_failure() {
  # Never restore old state when a guest rollback failed: that would hide the real remote state.
  rollback_all || return 1
  restore_state
}

# 4. snapshot every existing-guest UPDATE first. Creates are explicit supervised actions: no
# pre-change guest exists to snapshot, so failure can require operator cleanup.
create_count=0
for row in "${guest_rows[@]:-}"; do
  [ -n "${row}" ] || continue
  read -r action kind vmid node <<< "$(printf '%s' "${row}")"
  if [ "${action}" = create ]; then
    create_count=$((create_count + 1))
    continue
  fi
  if [ "${STATE_BACKUP_TAKEN}" = 0 ]; then
    if "${TOFU_BIN}" state pull > "${STATE_BACKUP}"; then
      STATE_BACKUP_TAKEN=1
    else
      echo "tofu-apply: could not capture OpenTofu state before an existing-guest update — refusing to apply." >&2
      exit 4
    fi
  fi
  if "${PVE_SNAPSHOT}" create "${node}" "${kind}" "${vmid}" "${SNAP}"; then
    TAKEN+=("${kind} ${vmid} ${node}")
  else
    echo "tofu-apply: could not snapshot ${kind} ${vmid} @ ${node} — refusing to apply without a rollback point." >&2
    prune_all
    exit 4
  fi
done
[ "${#TAKEN[@]}" -gt 0 ] && echo "==> snapshotted ${#TAKEN[@]} existing guest(s) as ${SNAP}"
[ "${create_count}" -gt 0 ] && echo "==> supervised guest create(s): ${create_count} — no automatic rollback; explicit approval required"
[ "${#TAKEN[@]}" -eq 0 ] && [ "${create_count}" -eq 0 ] && echo "==> no guests touched — non-guest changes have no automatic rollback"

# 5. apply the SAVED plan; on failure, roll back.
echo "==> applying saved plan ${PLAN}"
if ! "${TOFU_BIN}" apply -auto-approve "${PLAN}"; then
  echo "tofu-apply: apply FAILED — restoring existing-guest snapshots and OpenTofu state; created guests and non-guest changes need operator recovery" >&2
  if ! recover_apply_failure; then
    echo "tofu-apply: recovery FAILED — hard checkpoint; manual recovery required" >&2
    exit 7
  fi
  exit 5
fi

# 6. verify deterministically: post-apply plan must be clean (exit 0). Do not auto-rollback after a
# successful apply: a dirty plan or unavailable verifier needs operator judgement, and snapshots stay.
echo "==> verifying (post-apply plan must be clean)"
verify_rc=0
"${TOFU_BIN}" plan -detailed-exitcode -no-color >/dev/null 2>&1 || verify_rc=$?
if [ "${verify_rc}" -ne 0 ]; then
  if [ "${verify_rc}" -eq 2 ]; then
    echo "tofu-apply: verification found remaining drift — snapshots retained; operator recovery required" >&2
    exit 6
  fi
  echo "tofu-apply: verification unavailable (tofu plan exit ${verify_rc}) — snapshots retained; operator recovery required" >&2
  exit 7
fi
if [ -n "${TOFU_APPLY_VERIFY:-}" ] && ! eval "${TOFU_APPLY_VERIFY}"; then
  echo "tofu-apply: external verification FAILED — snapshots retained; operator recovery required" >&2
  exit 6
fi

echo "==> apply verified clean — pruning safety snapshots"
prune_all
echo "tofu-apply: OK"
