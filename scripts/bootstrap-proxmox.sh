#!/usr/bin/env bash
# bootstrap-proxmox.sh — one-time Proxmox operate-access setup (plan §7)
# TIER: T3 (node root) — HUMAN RUNS THIS, once per node, in the node's shell.
#   The agent writes it; Ali runs it because node root is T3, permanently.
# USAGE: bootstrap-proxmox.sh            # run as root on server-proxmox-core AND -network
# OUTPUT: prints the readonly + operate API tokens ONCE. Hand them to the agent
#         (they go into /opt/skynet-ops/secrets/ on the VM, never into git).
set -euo pipefail

command -v pveum >/dev/null || { echo "pveum not found — run this on a Proxmox node" >&2; exit 1; }
[ "$(id -u)" -eq 0 ] || { echo "must run as root" >&2; exit 1; }

echo "==> user svc-ops@pve (idempotent)"
pveum user list | grep -q 'svc-ops@pve' || pveum user add svc-ops@pve --comment "skynet-ops agent"

echo "==> read-only ACL: PVEAuditor at /"
pveum acl modify / --users svc-ops@pve --roles PVEAuditor

echo "==> pool ops-managed (idempotent)"
pveum pool list 2>/dev/null | grep -q 'ops-managed' || pveum pool add ops-managed

echo "==> custom role OpsOperator"
pveum role add OpsOperator \
  -privs "VM.Audit,VM.PowerMgmt,VM.Config.Disk,VM.Config.CPU,VM.Config.Memory,VM.Config.Network,VM.Config.Options,VM.Allocate,VM.Clone,VM.Console,VM.Snapshot,VM.Snapshot.Rollback,Datastore.AllocateSpace,Datastore.Audit" \
  2>/dev/null || pveum role modify OpsOperator \
  -privs "VM.Audit,VM.PowerMgmt,VM.Config.Disk,VM.Config.CPU,VM.Config.Memory,VM.Config.Network,VM.Config.Options,VM.Allocate,VM.Clone,VM.Console,VM.Snapshot,VM.Snapshot.Rollback,Datastore.AllocateSpace,Datastore.Audit"

echo "==> operate ACL: OpsOperator on /pool/ops-managed"
pveum acl modify /pool/ops-managed --tokens 'svc-ops@pve!operate' --roles OpsOperator

echo
echo "==> TOKENS — copy these ONCE, they are shown only now:"
echo "--- readonly (privsep 0, PVEAuditor at /) ---"
pveum user token add svc-ops@pve readonly --privsep 0 --output-format json || \
  echo "(token 'readonly' may already exist — recreate with: pveum user token remove svc-ops@pve readonly)"
echo "--- operate (privsep 1, OpsOperator on ops-managed) ---"
pveum user token add svc-ops@pve operate --privsep 1 --output-format json || \
  echo "(token 'operate' may already exist — recreate with: pveum user token remove svc-ops@pve operate)"
echo
echo "Reminder: OPNsense VM 5001 never joins ops-managed. Same for CT 635, CT 837, VM 2020."
