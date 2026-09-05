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

## Design dependencies (don't let these rot)

- **PCI passthrough IDs** must stay current in `runbooks/dr/pci-passthrough.md` (two Intel 82576
  dual-port NICs, bus 03/04, `ovmf`/`q35`) — a wrong ID blocks OPNsense rebuild.
- **The `skynet-opnsense` repo** must exist and receive os-git-backup pushes — a missing or
  misnamed repo blocks the OPNsense rebuild.
- **L5 completeness** is checked with `rclone check`; an unverified off-site copy is not a recovery
  source.
