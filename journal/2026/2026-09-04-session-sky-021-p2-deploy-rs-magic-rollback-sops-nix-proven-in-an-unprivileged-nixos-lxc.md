---
date: 2026-09-04
kind: session          # session | incident | decision
title: SKY-021 P2 — deploy-rs magic-rollback + sops-nix proven in an unprivileged NixOS LXC
tier_touched: [T2]      # T2: self-provisioned + destroyed a throwaway CT on core; deploy over SSH
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-021, SKY-007, SKY-008]
---

# 2026-09-04 · session · SKY-021 P2 — deploy-rs magic-rollback + sops-nix proven in an unprivileged NixOS LXC

## What happened
Ran SKY-021 Phase 2 on a fresh throwaway CT: prove (a) deploy-rs **magic-rollback** auto-reverts an
SSH-breaking change in an unprivileged NixOS LXC — the open question was whether container systemd
cooperates with profile-switch + canary rollback with **no bootloader** — and (b) **sops-nix
decrypt-to-tmpfs** activates in a container. Both PASS.

The `/`-broaden from P1 had landed (operate token holds the full VM/Datastore/Pool/SDN set at `/` on
core, bright lines `Permissions.Modify`/`Sys.*` still absent), so the token **self-provisioned the CT
id** — no ⚠ Ali CT-shell mint this time (the SKY-007 P1b wall is gone on core). CT 9099 recreated from
the P1 template `local:vztmpl/nixos-lxc-proof-26.05.tar.xz` via `POST /nodes/server-proxmox-core/lxc`
(unpriv, nesting=1, cmode console, rootfs local-lvm:8, net0 vmbr0 tag=90 ip=10.10.90.99/24
gw=10.10.90.1, ostype=nixos). Booted gen 1 (the template), SSH root@10.10.90.99 (agentKey baked).
Had to `ssh-keygen -R 10.10.90.99` first — stale P1 host key in known_hosts.

**deploy-rs wired** in flake.nix: `deploy.nodes.lxc-proof` → hostname 10.10.90.99, sshUser=root
(agent key is baked to root in lxc-base, not a separate svc-ops), magicRollback + autoRollback.
`nix flake check` (deploy-rs deployChecks) green.

**Trivial round-trip** (`nix run github:serokell/deploy-rs -- .#lxc-proof --skip-checks`): built on the
ops VM, copied closure to the CT, activated. Benign `/boot`/`init-script-builder.sh` warning (no
bootloader in a CT, same as P1). "Magic rollback is enabled, setting up confirmation hook… Found
canary file… Deployment confirmed." gen 1→2, `hello` now present, `systemctl is-system-running`=running.

**Decisive magic-rollback test:** temp (uncommitted) edit to hosts/lxc-proof adding
`services.openssh.ports = [ 2222 ]` → deploy. Activation SUCCEEDED on gen 3 (sshd moved to 2222),
deploy-rs then couldn't reconnect on 22 to confirm → confirmTimeout elapsed → the container
auto-reverted: `De-activating due to error → switching profile from version 3 to 2 → Removing
generation by ID 3 → Attempting to re-activate the last generation`. Post-check: SSH reachable on 22
again, current gen back to 2, `ss -tlnp` shows sshd on :22 not :2222, `hello` still present. So
profile-switch + canary rollback WORK in a container with no bootloader. Reverted the temp edit.

**sops-nix decrypt-to-tmpfs test:** deliberately did NOT put the lab master age key on a throwaway CT
(§2 credential-handling checkpoint + crown-jewel spread). Instead used the container's OWN ssh host
key as the age identity: `ssh-to-age` on `/etc/ssh/ssh_host_ed25519_key.pub` →
`age1n8dznn7q…stva02z`; `sops --encrypt --age <that>` a proof plaintext → `secrets/lxc-proof-marker.sops`
(temp). Temp flake edit imported `sops-nix.nixosModules.sops` into lxc-proof with
`sops.age.sshKeyPaths = [ "/etc/ssh/ssh_host_ed25519_key" ]` + one binary secret. Deploy →
`sops-install-secrets: Imported /etc/ssh/ssh_host_ed25519_key as age key … age1n8dznn7q…`,
`run-secrets.d.mount` started. Post-check: `/run/secrets/lxc-proof-marker` = the expected plaintext,
mode `-r--------` root, filesystem **ramfs** (tmpfs), and the plaintext is NOT anywhere in /nix/store.
Reverted all temp edits + removed the proof secret.

**Committed artifact (branch feat/sky-021-nixos-lxc-p2):** only `deploy.nodes.lxc-proof` in flake.nix
+ a refreshed lxc-proof comment. The sops proof was intentionally left uncommitted (Phase 3 wires
sops-nix on the real service host, where key distribution to a pool CT is a design choice — see below).

CT 9099 **stopped** at end (reversible); **destroy held as a §6 hard checkpoint** for Ali to confirm.

## Actions & outcomes
- `POST /lxc` self-provision CT 9099 from P1 template (token minted the id, no Ali mint) → running ✓
- add `deploy.nodes.lxc-proof` (magic+autoRollback, sshUser=root) → `nix flake check` green ✓
- trivial `deploy .#lxc-proof` → activated, confirmed, gen 1→2, `hello` present ✓
- SSH-breaking deploy (sshd→2222) → activation ok, confirm timed out, **auto-rollback to gen 2**, SSH
  restored on :22 ✓ (VERDICT: magic-rollback WORKS in an unprivileged LXC)
- sops-nix via host-key age identity → `/run/secrets/lxc-proof-marker` decrypted to ramfs, 0400 root,
  plaintext absent from /nix/store ✓ (VERDICT: decrypt-to-tmpfs WORKS)
- revert all temp edits; commit only the deploy node → clean diff ✓
- `POST /lxc/9099/status/stop` → stopped; destroy PENDING Ali confirm (§6)

## Graveyard — tried & abandoned
- `nix run github:Mic92/sops-nix#ssh-to-age` → no such attr (sops-nix ships `ssh-to-pgp`); the age
  converter is `nixpkgs#ssh-to-age`. Used that.
- Encrypting the proof secret from the repo root with `sops --age …` → "no matching creation rules
  found" / 0-byte output, because `.sops.yaml`'s `secrets/.*\.sops$` rule intercepted. Fixed by
  running sops from the scratchpad cwd (no creation rules there) with the explicit `--age` recipient.
- **Copying the lab master age key onto the throwaway CT** to test against "the lab age key" literally
  → abandoned: the master key is the root of the whole secret world (.sops.yaml), spreading it to a
  disposable CT trips the §2 credential-handling checkpoint for no proof value. Host-key-derived age
  proves the same mechanism with zero crown-jewel handling.

## Follow-ups / open threads
- **Destroy CT 9099** (throwaway) once Ali confirms; reclaim VMID. Currently stopped.
- **P3 key-distribution design (surfaced here):** a pool CT needs an age identity to decrypt its
  secrets. Two clean options proven/visible: (1) the lab's ONE-key model → the CT must receive the lab
  master key (how? provisioning-time copy is crown-jewel spread — weigh against the survival-kit
  doctrine); (2) host-key-derived age (`sshKeyPaths`, proven here) → per-CT recipient, secrets
  re-encrypted to multiple recipients, no master-key spread. Decide in P3 (hosts/lxc-adguard-network).
- P3: author the real `hosts/lxc-adguard-network/` (services.adguardhome in Nix), snapshot/PBS-back
  the existing CT, cut over keeping the old CT stopped as rollback, and **PR docs/system-design.md**
  for the new-CT default = NixOS for pool-able LXCs.
