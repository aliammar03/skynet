---
summary: "Provision a NixOS core-managed LXC: a PR carrying its approved plan, applied by skynet tofu after merge; creates have no automatic rollback."
trigger: "Set up / deploy a new LXC for X"
tier: "T2 PR-gated create"
executor: "skynet tofu (proxmox-core stack) and deploy-rs"
rollback: "No automatic rollback for a new LXC; operator recovery on partial create"
---

# Runbook — provision a NixOS core-managed LXC

**Tier:** T2 create, PR-gated and API-only; deploy-rs activates over SSH. Core CTs are intentionally unpooled and use the core envelope ACL. The operator identity is `svc-ops@pve!operate`.

## Preconditions

- Agree name, VMID/IP, resources, purpose, and partial-create recovery. The PR's approved plan is what the merge approves.

## Steps

1. Plan name, VLAN + last-octet VMID, resources, purpose, and recovery; receive approval.
2. Add `hosts/lxc-<name>/default.nix`, its `flake.nix` configuration and `deploy.nodes` entry. Import `nix/modules/lxc-base.nix`; add `sops-nix` only if the guest has secrets.
3. For secrets, run `scripts/ct-age-identity.sh new lxc-<name>`, add its dual-recipient `.sops.yaml` rule and `secrets/lxc-<name>/`, then configure `sops.age.keyFile` in the host.
4. Add the guest to `local.native_core_cts` in [`../tofu/proxmox-core/pool-cts.tf`](../tofu/proxmox-core/pool-cts.tf), including pinned `mac`, VMID, VLAN/octet, and resources. Do not add OPNsense 5001, CT 635/837, or VM 2020. PBS CT 240 is an existing `ops-managed` import, not an excluded guest.
5. On a branch rebased on `main`, commit the declarations, then write and commit the approved plan:
   ```bash
   skynet tofu plan proxmox-core --approve   # expect one create; the PR diff shows approved-plan.json
   ```
   Open the PR. After the merge, `skynet tofu apply --pending` applies it (the `skynet-tofu` timer, each minute) (`skynet log --kind tofu`). A
   held result means the merged plan no longer matches: re-plan in a new PR. If the create fails it
   alerts; stop, and never auto-destroy a partial create. After success, inject a required age identity before first deploy and run `nix run github:serokell/deploy-rs -- .#lxc-<name>`.
6. Verify the service, refresh inventory, and keep the entity audit green. Day-two changes are edit → PR → deploy.

### Import an existing CT

Model it under `local.imported_core_cts` with an `import {}` block, and iterate `skynet tofu plan proxmox-core` until only the import remains; approve and merge that, then drop the block in a follow-up. Preserve only provider round-trip exceptions in `lifecycle.ignore_changes`; do not convert an import into a create.

## Verify

- The read API reports the CT running, deploy-rs succeeds, service health is good, and `skynet entities` is green.

## Rollback

- New CTs have no pre-change snapshot. Stop for operator recovery on partial creation; later configuration rolls back through human-merged revert plus deploy.

## Evidence

- Preserve the PR with its `approved-plan.json`, the `skynet log` line, the deploy result, and refreshed inventory.
