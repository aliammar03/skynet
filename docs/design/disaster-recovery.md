---
summary: "The survival kit and how each node-loss scenario is recovered; the step-by-step procedures live in runbooks/dr/."
---

# Spoke · Disaster recovery

> The design of *coming back* — what's in the survival kit, and how the two node-loss scenarios
> are recovered. Governed by [`../system-design.md`](../system-design.md). Procedures: [`runbooks/dr/`](../../runbooks/dr/).

## Why recovery is even possible

Skynet rebuilds from git; only payload data comes from backups. The survival kit holds the unique
age and SSH keys. GitHub also holds the OPNsense configuration, and the ops brain has a static IP
so it remains reachable when OPNsense/DHCP is unavailable.

## Survival kit (paper + password manager, outside Skynet)

The kit is load-bearing; its recovery procedure and verification are in
[`survival-kit.md`](../../runbooks/dr/survival-kit.md).

- age private key · restic password · PBS encryption key · **SSH CA private key**
- GitHub fine-grained PATs · rclone Google OAuth config
- Proxmox + OPNsense ISOs on USB
- NIC passthrough PCI IDs + BIOS notes ([`pci-passthrough.md`](../../runbooks/dr/pci-passthrough.md))
- one printed page: *"clone the repo, open `runbooks/dr/`, follow it."*

It is verified quarterly.

## The two scenarios

### Network node dies

[`DR-network-node.md`](../../runbooks/dr/DR-network-node.md) rebuilds
`server-proxmox-network` and restores routing. Its primary OPNsense path is a fresh VM 5001 plus
the `skynet-opnsense` `config.xml` import; PBS restore remains the secondary path because it needs
VLAN 20 L2 reachability before routing exists. After routing, recover the remaining PBS guests and
reconcile refreshed inventory against the last pre-disaster commit.

### Core node dies with PBS aboard

[`DR-core-node.md`](../../runbooks/dr/DR-core-node.md) restores the PBS datastore from Google Drive
(L5), then PBS, Unraid, skynet-ops, and remaining guests in that order.

## Ops VM state (census 2026-09-26, SKY-025 P12)

- **Runtime:** checkout `/home/aliammar/skynet`; NixOS 26.05 (nixpkgs `a9e6d84`); `skynet` is a
  system package. One timer, `skynet-nightly` (03:30 ± 15 min), still runs `bin/ops nightly` with the
  Home Manager–owned `~/.config/skynet-ops/ops.env`.
- **Persisted across the tmpfs root** (`nix/modules/impermanence.nix`): `/opt/skynet-ops` (`age.key`;
  `certs/` pins for omada, opnsense, proxmox-core, proxmox-network, technitium; `mirror/skynet-opnsense`;
  `secrets/` symlinks to `/run/secrets`), `/home/aliammar`, `/var/lib/{docker,nixos,systemd}`,
  `/var/log`, `machine-id`, SSH host keys.
- **Ignored local state:**
  - **Recovery-critical:** `tofu/terraform.tfstate` and its timestamped backups. Losing them means
    re-importing every managed resource. Phase 15 moves state to the `tofu-state` branch.
  - **Rebuildable:** `.cache/` (inventory DB, collection lock), `tofu/.terraform/` (provider cache),
    Python tool caches, `result`.
- **Survival-kit path (proven 2026-09-26):** the age master key (recipient
  `age1stah9c426pq0xf3k4qc58e92vs263lf6uvze2f6nmx84nvk86cusfgexyw`) is in the kit, both in the password
  manager and on paper. From Ali's workstation, the kit copy decrypted `secrets/rclone.conf.sops`
  without the ops VM. Off-site restore from the kit is **not** proven: the kit's `rclone.conf` uses the
  disabled Google OAuth client (see `runbooks/backup.md`).

## Design dependencies (don't let these rot)

- **PCI passthrough IDs** must stay current in `runbooks/dr/pci-passthrough.md` (two Intel 82576
  dual-port NICs, bus 03/04, `ovmf`/`q35`) — a wrong ID blocks OPNsense rebuild.
- **The `skynet-opnsense` repo** must exist and receive os-git-backup pushes — a missing or
  misnamed repo blocks the OPNsense rebuild.
- **L5 completeness** is checked with `rclone check`; an unverified off-site copy is not a recovery
  source.
