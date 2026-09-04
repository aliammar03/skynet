---
date: 2026-09-04
kind: session          # session | incident | decision
title: SKY-021 P1 — NixOS-in-LXC path proven; in-place nixos-rebuild works on 26.05
tier_touched: [T2]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-021, SKY-007, SKY-008]
---

# 2026-09-04 · session · SKY-021 P1 — NixOS-in-LXC path proven; in-place nixos-rebuild works on 26.05

## What happened
Ran SKY-021 Phase 1: prove the LXC NixOS path end-to-end on a throwaway CT, and record a verdict on
whether in-place `nixos-rebuild switch` reliably applies in an unprivileged Proxmox LXC (the
historically-broken step, per the directive's research). It works on our stack.

Authored the flake path on branch `feat/sky-021-nixos-lxc-p1`:
- `nix/modules/lxc-base.nix` — reusable container baseline, imports `(modulesPath +
  "/virtualisation/proxmox-lxc.nix")`. The 26.05 module ALREADY bakes in the historically-broken
  fixes (`boot.isContainer`, `register-nix-paths` which sets `/nix/var/nix/profiles/system`,
  `getty@tty1`) — the `NIX_REMOTE=""` workaround was NOT needed.
- `hosts/lxc-proof/default.nix` — throwaway host (hostname lxc-proof, stateVersion 26.05).
- `flake.nix` — `nixosConfigurations.lxc-proof` + `packages.x86_64-linux.lxc-proof-tarball`.
- `nix build .#lxc-proof-tarball` → 261M `nixos-image-lxc-proxmox-26.05...tar.xz`, clean.

Then the live path — which surfaced a cascade of Proxmox permission walls on the `svc-ops@pve!operate`
token (a privsep token: effective perms = intersection of USER perms ∩ TOKEN perms per path). Ali
granted each via `pveum` (permission admin = T3, his hands):
1. Template upload needs `Datastore.AllocateTemplate` on `/storage/local` → added to OpsOperator role.
2. New-VMID create needs `VM.Allocate` at `/vms` root (pool-scoped can't mint a not-yet-in-pool id —
   the SKY-007 P1b wall). Granted OpsOperator at `/vms` — BUT only showed VM.Audit until the USER
   side of the intersection was also bound (`--users` in addition to `--tokens`). Same for
   `Datastore.AllocateSpace` on `/storage/local-lvm` (CT rootfs).
3. Upload then failed "write to temporary file failed" → `local` storage was FULL (96.9/100G, 0 avail),
   stuffed with ~80G of stale manual vzdumps (the real backups are in PBS). Ali OK'd deleting Tier
   A (orphaned: 4015/275/540/231) + Tier B (superseded live-guest dumps: old 10015, old 9090×2) →
   freed to 59.9G avail. Deleted via `DELETE /nodes/.../storage/local/content/{volid}` (worked via
   the token's VM.Backup at /vms).
4. `pct create` (POST /nodes/.../lxc) then hit `SDN.Use` on `/sdn/zones/localnetwork/vmbr0/90`
   (Proxmox 9 SDN enforcement) → granted OpsOperator+SDN.Use at `/sdn/zones/localnetwork/vmbr0`
   (user+token).

CT 9099 (hostname lxc-proof, unprivileged, nesting=1, cmode console, rootfs local-lvm:8,
net0 vmbr0 tag=90 ip=10.10.90.99/24) created + started from `ostype=nixos` template. Booted NixOS
26.05, pingable, SSH as root@10.10.90.99 (agentKey baked in). `ostype=nixos` handled network
injection — no manageNetwork=true rebuild needed.

**Decisive test:** `hello` absent → added `pkgs.hello` to hosts/lxc-proof → `nixos-rebuild switch
--flake .#lxc-proof --target-host root@10.10.90.99` (build on ops VM, activate remote). Activated
cleanly (benign `/boot` warning — no bootloader in a CT). After: `hello` present + runs,
current-system `swxk9mc8…`→`1rad2cd…`, generations system-1-link→system-2-link,
`systemctl is-system-running` = running. IN-PLACE REBUILD WORKS.

Also, on Ali's direction, broadened the operate token toward "fully own guests/storage/network/pools
on CORE only" — full VM/Datastore/Pool/SDN set bound at `/`, deliberately holding back the two bright
lines: NO `Permissions.Modify` (self-leash rewrite) and NO `Sys.Console/Modify/PowerMgmt` (node root).
Network node unchanged; OPNsense 5001 / CT 635 / CT 837 stay T3 there. Recorded in the
docs/system-design.md edit on the branch.

## Actions & outcomes
- `nix build .#lxc-proof-tarball` → 261M proxmox-lxc tarball ✓
- upload template (after freeing `local`) → `local:vztmpl/nixos-lxc-proof-26.05.tar.xz` ✓
- `pct create 9099` + start → running, SSH-reachable at 10.10.90.99 ✓
- in-place `nixos-rebuild switch` adds `pkgs.hello` → applied, gen advanced, systemd healthy ✓ (VERDICT: PASS)
- CT 9099 destroy → PENDING Ali confirm (destroy = hard checkpoint at every level, §6)

## Graveyard — tried & abandoned
- Granting the /vms + local-lvm perms to the TOKEN only (`--tokens`) → showed VM.Audit only; a
  privsep token needs the USER bound too (perms = user ∩ token). Fixed by also `--users`.
- Considered manageNetwork=true + baked static IP to de-risk networking → NOT needed; `ostype=nixos`
  injected the network config and networkd picked it up. Left as the Phase-3 option if a host wants
  Nix to own its address.
- First template upload → "write to temporary file failed" (not a perms issue) = `local` full.

## Follow-ups / open threads
- Destroy CT 9099 (throwaway) once Ali confirms; reclaim VMID.
- P1 close-out: PR the branch `feat/sky-021-nixos-lxc-p1` (flake path + system-design blast-radius edit).
- ENFORCEMENT GAP: check-invariants.sh checks POOL membership, but the core `/vms`-root ACL confers
  VM ops WITHOUT pooling → the gate's guarantee is narrower on core than its "why" text claims.
  Proposed: an ACL-audit checker asserting the operate token's granted scope == the declared core
  exception (catches silent widening, e.g. someone adding /vms on the network node). Build in P1 or
  as a fast follow-up.
- P2: deploy-rs magic-rollback round-trip in the container (the open question is whether container
  systemd cooperates with profile-switch + canary rollback — no bootloader involved).
- Lab hygiene: `local` on core accumulates manual vzdumps; the backup design says PBS/restic, not
  local. Consider a retention/no-manual-dump policy.
