---
summary: "Provision a VM from merged source and an explicitly approved saved plan; creates are supervised T2 without automatic rollback."
trigger: "Set up a VM for X, hardened, with restic"
tier: "Supervised T2 saved-plan create + T2+ root grant"
executor: "OpenTofu saved-plan wrapper, onboard-host.sh, and provision-restic.sh"
rollback: "No automatic rollback for a new VM; operator recovery on partial create"
---

# Runbook — provision a hardened VM

**Tier:** supervised T2 saved-plan create; a T2+ root grant is required for guest hardening.

## Preconditions

- Agree name, VMID/IP, resources, purpose, backup scope, hardening, and partial-create recovery. The merged declaration and exact plan both need approval.

## Steps

1. Plan VLAN/IP (VMID = VLAN + last octet), resources, purpose, and rollback, then receive approval.
2. Declare a `proxmox_virtual_environment_vm` in `tofu/` that clones `ubuntu-2404-base` (VMID 9000) into `ops-managed`. Set network and a temporary bootstrap SSH key with the API-native `initialization` block; never use a node-SSH snippet. The base image does not contain CA trust or `svc-ops`: log in once with the temporary bootstrap key, run `scripts/onboard-host.sh` as root, then use the expiring root grant. Do not pool OPNsense 5001, CT 635/837, or VM 2020.
3. Open a PR with the declaration and speculative plan. After Ali merges it, save and show the plan, receive approval, then apply exactly it:
   ```bash
   eval "$(scripts/tofu-env.sh)"
   tofu -chdir=tofu plan -out=/tmp/provision-<newhost>.tfplan
   tofu -chdir=tofu show -no-color /tmp/provision-<newhost>.tfplan
   TOFU_APPLY_SCOPE=proxmox-core scripts/tofu-apply.sh /tmp/provision-<newhost>.tfplan
   ```
   Check `/cluster/resources` through the read API. On any create/verification failure, stop: the wrapper never auto-destroys a partial VM.
4. Request the narrowest root grant (for example `bin/grant-root <newhost> 2h`), validate its certificate, then harden SSH, install updates/fail2ban as appropriate, and configure backups:
   ```bash
   scripts/provision-restic.sh <newhost> root@<ip> --docker
   scripts/provision-restic.sh <newhost> root@<ip> --path /srv/data
   ```
   The backup script is idempotent and creates its password on the host; save that password to the survival kit.
5. Land hardening definitions and refreshed inventory in a follow-up PR. Apps-Caddy records derive from the Caddyfile; standalone host records are separately tofu-managed.

## Verify

- The read API reports the VM running; onboarding/hardening and backups completed inside the grant, and the intended service/DNS path works.

## Rollback

- A new VM has no pre-change snapshot. Stop for operator recovery on partial create; later declaration changes use human-merged `git revert`.

## Evidence

- Preserve the saved plan, approval, provisioning/hardening definitions, and refreshed inventory.
