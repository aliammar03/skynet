#!/usr/bin/env bash
# bootstrap-proxmox.sh — one-time Proxmox operate-access setup (docs/design/access-and-trust.md)
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

# Node-aware scope (SKY-021). The two nodes are standalone PVE instances with separate ACL DBs, so
# each runs its own OpsOperator. NETWORK = pool-scoped (the original shape). CORE = full ownership of
# guests/storage/network/pools, bound at / (agent self-provisions pool CTs) — with the bright lines
# held out: NO Permissions.Modify (self-leash rewrite) and NO Sys.Modify/PowerMgmt/Console (node root).
# The ACL-audit gate (invariants.json operate_token_scope + check-invariants.sh) enforces both.
case "$(hostname)" in
  *core*)    IS_CORE=1 ;;
  *network*) IS_CORE=0 ;;
  *) echo "hostname '$(hostname)' is neither *core* nor *network* — refusing to guess node scope" >&2; exit 1 ;;
esac

NET_PRIVS="VM.Audit,VM.PowerMgmt,VM.Config.Disk,VM.Config.CPU,VM.Config.Memory,VM.Config.Network,VM.Config.Options,VM.Allocate,VM.Clone,VM.Console,VM.Snapshot,VM.Snapshot.Rollback,VM.Backup,Datastore.AllocateSpace,Datastore.Audit"
CORE_PRIVS="VM.Allocate,VM.Audit,VM.Backup,VM.Clone,VM.Config.CDROM,VM.Config.CPU,VM.Config.Cloudinit,VM.Config.Disk,VM.Config.HWType,VM.Config.Memory,VM.Config.Network,VM.Config.Options,VM.Console,VM.GuestAgent.Audit,VM.GuestAgent.FileRead,VM.GuestAgent.FileSystemMgmt,VM.GuestAgent.FileWrite,VM.GuestAgent.Unrestricted,VM.Migrate,VM.PowerMgmt,VM.Replicate,VM.Snapshot,VM.Snapshot.Rollback,Datastore.Allocate,Datastore.AllocateSpace,Datastore.AllocateTemplate,Datastore.Audit,Pool.Allocate,Pool.Audit,SDN.Allocate,SDN.Audit,SDN.Use,Sys.Audit,Mapping.Audit,Mapping.Use"
if [ "${IS_CORE}" -eq 1 ]; then PRIVS="${CORE_PRIVS}"; else PRIVS="${NET_PRIVS}"; fi

echo "==> custom role OpsOperator ($([ "${IS_CORE}" -eq 1 ] && echo 'core: full guests/storage/network/pools' || echo 'network: pool-scoped'))"
pveum role add OpsOperator -privs "${PRIVS}" 2>/dev/null || pveum role modify OpsOperator -privs "${PRIVS}"

# Tokens MUST exist before any ACL can reference them (access-and-trust.md — token-before-ACL order).
echo
echo "==> TOKENS — copy these ONCE, they are shown only now:"
echo "--- readonly (privsep 0, PVEAuditor at /) ---"
pveum user token add svc-ops@pve readonly --privsep 0 --output-format json || \
  echo "(token 'readonly' may already exist — recreate with: pveum user token remove svc-ops@pve readonly)"
echo "--- operate (privsep 1, OpsOperator on ops-managed) ---"
pveum user token add svc-ops@pve operate --privsep 1 --output-format json || \
  echo "(token 'operate' may already exist — recreate with: pveum user token remove svc-ops@pve operate)"

echo "==> operate ACL: OpsOperator on /pool/ops-managed (token created above)"
# The operate token is privilege-separated (--privsep 1), so its EFFECTIVE rights are the
# intersection of the user's rights and the token's ACL. The user only holds PVEAuditor at /,
# so without the user ALSO holding OpsOperator on the pool the intersection strips every write
# privilege — the token can list but never snapshot/backup/operate. Grant BOTH. (A6 finding.)
pveum acl modify /pool/ops-managed --users svc-ops@pve --roles OpsOperator
pveum acl modify /pool/ops-managed --tokens 'svc-ops@pve!operate' --roles OpsOperator
# Pool.Audit on the pool path — /pools/<id> membership isn't visible from PVEAuditor at / alone.
# Lets collect-proxmox.sh capture pool membership for the SKY-011 invariants gate. Read-only.
pveum acl modify /pool/ops-managed --users svc-ops@pve --roles PVEAuditor
# Backup target: vzdump needs Datastore.AllocateSpace on the storage it writes to. 'local' is
# the on-node backup target for ops-managed guests that can't be snapshotted (e.g. the PBS CT,
# whose NFS-backed datastore mountpoint blocks LXC snapshots). Grant the role there too.
pveum acl modify /storage/local --users svc-ops@pve --roles OpsOperator
pveum acl modify /storage/local --tokens 'svc-ops@pve!operate' --roles OpsOperator

if [ "${IS_CORE}" -eq 1 ]; then
  # CORE broaden (SKY-021): bind OpsOperator at / for BOTH user and token (privsep intersection) —
  # full guests/storage/network/pools across the node + self-provisioning of new VMIDs. This
  # supersedes the pool/storage bindings above on core (they stay as harmless documentation of the
  # base scope). The bright lines are held by OpsOperator NOT carrying them (see role privs above);
  # the ACL-audit gate fails the build if they ever appear, or if / VM.Allocate shows up on network.
  echo "==> CORE: OpsOperator at / (full guests/storage/network/pools; bright lines held out)"
  pveum acl modify / --users  svc-ops@pve            --roles OpsOperator
  pveum acl modify / --tokens 'svc-ops@pve!operate'  --roles OpsOperator
fi
echo
echo "Reminder: OPNsense VM 5001 never joins ops-managed. Same for CT 635, CT 837, VM 2020."
echo "         Core /-bind grants the VM envelope of 2020 (not guest OS root, still T3); 5001/635/837 are on the network node."
