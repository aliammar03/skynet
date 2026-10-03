---
summary: "Provision a VM: a PR carrying its approved plan, applied by skynet tofu after merge; creates have no automatic rollback."
trigger: "Set up a VM for X, hardened, with restic"
tier: "T2 PR-gated create + T2+ root grant"
executor: "skynet tofu (proxmox-core stack), onboard-host.sh, and provision-restic.sh"
rollback: "No automatic rollback for a new VM; operator recovery on partial create"
---

# Runbook — provision a hardened VM

**Tier:** T2 PR-gated create; a T2+ root grant is required for guest hardening.

## Preconditions

- Agree name, VMID/IP, resources, purpose, backup scope, hardening, and partial-create recovery. The merge approves the PR's `approved-plan.json`.

## Steps

1. Plan VLAN/IP (VMID = VLAN + last octet), resources, purpose, and rollback, then receive approval.
2. Declare a `proxmox_virtual_environment_vm` in `tofu/proxmox-core/` that clones `ubuntu-2404-base` (VMID 9000) into `ops-managed`. Set network and a temporary bootstrap SSH key with the API-native `initialization` block; never use a node-SSH snippet. The base image does not contain CA trust or `svc-ops`: log in once with the temporary bootstrap key, run `scripts/onboard-host.sh` as root, then use the expiring root grant. Do not pool OPNsense 5001, CT 635/837, or VM 2020.
3. On a branch rebased on `main`, commit the declaration, run `skynet tofu plan proxmox-core --approve` (expect one create), commit `approved-plan.json`, and open the PR. After Ali merges it, `skynet tofu apply --pending` applies it (the `skynet-tofu` timer, each minute) (`skynet log --kind tofu`); a held result means the merged plan differs, so re-plan in a new PR. Check `/cluster/resources` through the read API. A failed create alerts; stop: the executor never auto-destroys a partial VM.
4. Request the narrowest root grant (for example `gr <newhost> 2h` on the workstation), validate its certificate, then harden SSH, install updates/fail2ban as appropriate, and configure backups:
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
- Retiring it later is not a rollback: removing the declaration defers the delete (one alert); after Ali approves, destroy it as in [diagnose/tofu-stuck](diagnose/tofu-stuck.md#retire-a-guest-deferred-delete).

## Evidence

- Preserve the PR with its `approved-plan.json`, the `skynet log` line, provisioning/hardening definitions, and refreshed inventory.
