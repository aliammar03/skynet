---
summary: "Provision a NixOS pool LXC: declare it in tofu (API-only create from the NixOS vztmpl), inject its Option C age key, deploy-rs its flake host. Tofu owns the envelope, nix owns the inside."
trigger: "Set up / deploy a new LXC for X"
tokens: 965
---

# Runbook — provision a NixOS pool LXC (declarative)

**Tier:** T2 (tofu apply via the operator token, API-only — no node SSH; deploy-rs over SSH).
**Trigger:** *"Set up a new LXC for X" / "deploy a new container."*

> **Tofu makes the box, Nix defines it.** A new pool CT is **a tofu resource block + a flake host + a
> PR** — no hand-rolled `pct`/API curl. SKY-021 proved the NixOS-LXC path; SKY-024 made create
> declarative (API-only) under the **one operator token** (`svc-ops!operate`). The reference resource
> is [`tofu/lxc-adguard-core.tf`](../tofu/lxc-adguard-core.tf); the reference host is
> [`hosts/lxc-adguard-core/`](../hosts/lxc-adguard-core/).

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

4. **Declare the CT in `tofu/`** — a `proxmox_virtual_environment_container` from the NixOS base vztmpl
   (`operating_system.type = "nixos"`, `template_file_id = "local:vztmpl/nixos-lxc-proof-26.05.tar.xz"`),
   `unprivileged = true`, `features { nesting = true }`, `initialization.ip_config` for the address, and
   a **pinned `network_interface.mac_address`** (declarative → a reprovision reuses it, never churns the
   gateway ARP — the SKY-021 lesson). Core self-provisions new VMIDs; on the **network node** a new VMID
   needs a human (⚠ — that node is pool-scoped by design; OPNsense lives there). **Never** pool an
   excluded guest (OPNsense 5001, CT 635/837, VM 2020, PBS 240).

5. **Apply + specialize.** `eval "$(scripts/tofu-env.sh)"` then (from `tofu/`) `tofu plan` → after merge
   `tofu apply` creates the CT (API-only). Then:
   ```
   scripts/ct-age-identity.sh inject lxc-<name> root@<ip>   # if it has secrets, BEFORE the first deploy
   nix run github:serokell/deploy-rs -- .#lxc-<name>        # first activation; magic-rollback protects you
   ```

6. **Verify + PR.** Confirm the service works; `bin/ops collect` refreshes inventory; the entity audit
   must stay green (VMID↔IP). Land the flake host + tofu block via PR (the agent never self-merges).
   Day-2 is then just edit → `deploy .#lxc-<name>`; rollback = `git revert` (+ deploy) or `tofu destroy`.

## Bringing an EXISTING container under tofu (zero-drift import)
Import instead of create: model the resource on [`tofu/lxc-adguard-core.tf`](../tofu/lxc-adguard-core.tf)
(declared to the read-back values, `lifecycle.ignore_changes` for what bpg can't round-trip — on a
fresh raw-API-created CT that includes **`cpu`**, plus `operating_system`/`initialization`/`pool_id`/
`vm_id`/timeouts), then `tofu import proxmox_virtual_environment_container.<name> <node>/<vmid>` and
iterate `plan` to **zero changes** before committing.
