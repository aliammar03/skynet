---
summary: "Provision a NixOS core-managed LXC from merged source and an explicitly approved saved plan; creates are supervised T2 without automatic rollback."
trigger: "Set up / deploy a new LXC for X"
tier: "Supervised T2 saved-plan create"
executor: "OpenTofu saved-plan wrapper and deploy-rs"
rollback: "No automatic rollback for a new LXC; operator recovery on partial create"
---

# Runbook — provision a NixOS core-managed LXC (declarative)

**Tier:** T2 (reviewed saved-plan apply via the operator token, API-only — no node SSH; deploy-rs over SSH).
**Trigger:** *"Set up a new LXC for X" / "deploy a new container."*

> **Tofu makes the box, Nix defines it.** A new core-managed CT is **one data entry in
> `tofu/pool-cts.tf` + a
> flake host + a PR** — no hand-rolled `pct`/API curl. Create is API-only under the operator token
> (`svc-ops@pve!operate`); the CT
> into a `for_each` data entry. Core service CTs are currently intentionally **unpooled**; the core
> node's envelope ACL is the management boundary. The reference module is [`tofu/pool-cts.tf`](../tofu/pool-cts.tf); the
> reference host is
> [`hosts/lxc-adguard-core/`](../hosts/lxc-adguard-core/).

> [!warning] **Create is supervised, not automatically reversible.** A new VMID has no pre-change
> snapshot. `scripts/tofu-apply.sh` applies the exact approved plan but never auto-destroys a partial
> create. Inspect failures and request separate approval before any cleanup; this path stays below A4.

## Preconditions

- Agree name, VMID/IP, resources, purpose, and partial-create recovery plan. The merged source and exact saved plan need explicit approval.

## Steps

1. **Plan first** (system-design §9): name, **VLAN + last octet → VMID** (the naming law, e.g. VLAN 70
   `.42` → 742; the entity audit enforces it), resources, purpose, rollback. One-word approval.

2. **Author the flake host** `hosts/lxc-<name>/default.nix` — `imports = [ ../../nix/modules/lxc-base.nix ]`
   (gives nix/flakes, the agent SSH key, sshd key-only, PKT, console root-autologin) + the service. Add
   to `flake.nix`: `nixosConfigurations.lxc-<name>` (add `sops-nix.nixosModules.sops` if it has secrets)
   and a `deploy.nodes.lxc-<name>` (hostname = its IP, `sshUser = "root"`, magic+autoRollback).

3. **If it has secrets — mint an Option C identity** (see [secrets](../docs/design/secrets.md)):
   ```
   scripts/ct-age-identity.sh new lxc-<name>       # commits the lab-encrypted per-CT key + .pub
   ```
   Add the printed `.sops.yaml` dual-recipient rule; put service secrets under `secrets/lxc-<name>/`;
   set `sops.age.keyFile = "/var/lib/sops-nix/age.key"` in the host.

4. **Add one entry to `local.native_core_cts` in `tofu/pool-cts.tf`** — `{ vmid, node, vlan, octet, mac, cores,
   memory, swap, disk, tags }`. The `for_each` module turns it into the full container (NixOS vztmpl,
   unprivileged, nesting, network from `vlan`/`octet`). **`mac` is required and pinned** → a reprovision
   reuses it and never churns the gateway ARP. `vmid` must satisfy the VMID↔IP law
   (the entity audit enforces it). Core self-provisions new VMIDs; on the **network node** a new VMID
   needs a human (⚠ — that node is pool-scoped by design; OPNsense lives there). **Never** add an
   excluded guest (OPNsense 5001, CT 635/837, VM 2020) to either map. PBS CT 240 is an existing
   `ops-managed` import, not an excluded guest.

5. **PR, save, and apply the reviewed plan.** Open a PR with the flake/tofu declarations
   and speculative plan output; Ali merges. From that merged revision, save and show the exact plan:
   ```
   eval "$(scripts/tofu-env.sh)"
   tofu -chdir=tofu plan -out=/tmp/provision-lxc-<name>.tfplan
   tofu -chdir=tofu show -no-color /tmp/provision-lxc-<name>.tfplan
   # STOP: Ali explicitly approves this exact create plan.
   TOFU_APPLY_SCOPE=proxmox-core scripts/tofu-apply.sh /tmp/provision-lxc-<name>.tfplan
   ```
   Verify the new CT is running through `/cluster/resources`. If apply or verification fails, stop:
   the wrapper does not auto-destroy a partial create. After a clean create, continue:
   ```
   scripts/ct-age-identity.sh inject lxc-<name> root@<ip>   # if it has secrets, BEFORE the first deploy
   nix run github:serokell/deploy-rs -- .#lxc-<name>        # first activation; magic-rollback protects you
   ```

6. Confirm the service works; `bin/ops collect` refreshes inventory; the entity audit must stay green
   (VMID↔IP). Day-2 is edit → PR → `deploy .#lxc-<name>`.

## Bringing an EXISTING container under tofu (zero-drift import)
Import instead of create: model the resource in `local.imported_core_cts` on
[`tofu/pool-cts.tf`](../tofu/pool-cts.tf)
(declared to the read-back values, `lifecycle.ignore_changes` for what bpg can't round-trip — on a
fresh raw-API-created CT that includes **`cpu`**, plus `operating_system`/`initialization`/`pool_id`/
`vm_id`/timeouts), then `tofu import proxmox_virtual_environment_container.<name> <node>/<vmid>` and
iterate `plan` to **zero changes** before committing.

## Verify

- Confirm the CT is running through the read API, deploy-rs activation succeeds, the service is healthy, and `bin/ops entities` remains green.

## Rollback

- A new CT has no pre-change snapshot. On a partial-create or verification failure, stop for operator recovery; do not auto-destroy. Day-two configuration rollback is a human-merged `git revert` plus deploy.

## Evidence

- Land the reviewed source, saved-plan output, approval record, read-API result, deploy result, and refreshed inventory via PR.
