---
summary: "Provision a NixOS core-managed LXC from merged source and an explicitly approved saved plan; creates are supervised T2 without automatic rollback."
trigger: "Set up / deploy a new LXC for X"
tier: "Supervised T2 saved-plan create"
executor: "OpenTofu saved-plan wrapper and deploy-rs"
rollback: "No automatic rollback for a new LXC; operator recovery on partial create"
---

# Runbook — provision a NixOS core-managed LXC

**Tier:** supervised T2 create, API-only; deploy-rs activates over SSH. Core CTs are intentionally unpooled and use the core envelope ACL. The operator identity is `svc-ops@pve!operate`.

## Preconditions

- Agree name, VMID/IP, resources, purpose, and partial-create recovery. Merged source and the exact saved plan require explicit approval.

## Steps

1. Plan name, VLAN + last-octet VMID, resources, purpose, and recovery; receive approval.
2. Add `hosts/lxc-<name>/default.nix`, its `flake.nix` configuration and `deploy.nodes` entry. Import `nix/modules/lxc-base.nix`; add `sops-nix` only if the guest has secrets.
3. For secrets, run `scripts/ct-age-identity.sh new lxc-<name>`, add its dual-recipient `.sops.yaml` rule and `secrets/lxc-<name>/`, then configure `sops.age.keyFile` in the host.
4. Add the guest to `local.native_core_cts` in [`../tofu/pool-cts.tf`](../tofu/pool-cts.tf), including pinned `mac`, VMID, VLAN/octet, and resources. Do not add OPNsense 5001, CT 635/837, or VM 2020. PBS CT 240 is an existing `ops-managed` import, not an excluded guest.
5. Open a PR with the declarations and speculative plan; after it merges, save and show the exact plan, receive approval, then apply it:
   ```bash
   eval "$(scripts/tofu-env.sh)"
   tofu -chdir=tofu plan -out=/tmp/provision-lxc-<name>.tfplan
   tofu -chdir=tofu show -no-color /tmp/provision-lxc-<name>.tfplan
   TOFU_APPLY_SCOPE=proxmox-core scripts/tofu-apply.sh /tmp/provision-lxc-<name>.tfplan
   ```
   If creation/verification fails, stop; never auto-destroy a partial create. After success, inject a required age identity before first deploy and run `nix run github:serokell/deploy-rs -- .#lxc-<name>`.
6. Verify the service, refresh inventory, and keep the entity audit green. Day-two changes are edit → PR → deploy.

### Import an existing CT

Model it under `local.imported_core_cts`, import it, and iterate plan to zero changes before commit. Preserve only provider round-trip exceptions in `lifecycle.ignore_changes`; do not convert an import into a create.

## Verify

- The read API reports the CT running, deploy-rs succeeds, service health is good, and `bin/ops entities` is green.

## Rollback

- New CTs have no pre-change snapshot. Stop for operator recovery on partial creation; later configuration rolls back through human-merged revert plus deploy.

## Evidence

- Preserve the source PR, saved plan, approval, API/deploy result, and refreshed inventory.
