---
summary: "The survival kit and how each node-loss scenario is recovered; the step-by-step procedures live in runbooks/dr/."
tokens: 947
---

# Spoke · Disaster recovery

> The design of *coming back* — what's in the survival kit, and how the two node-loss scenarios
> are recovered. Governed by [`../system-design.md`](../system-design.md). Sourced from plan §10.
> The step-by-step **procedures** live in [`../../runbooks/dr/`](../../runbooks/dr/); this spoke is
> the design behind them.

## Why recovery is even possible

Skynet is **stateless by design**: everything it knows is in git, and its only unique material
(age key, SSH keypair) is in the survival kit. Truth lives on GitHub — including the firewall
config, which *survives the router* — and the ops brain holds a static IP so it stays reachable
when DHCP (OPNsense) is the thing that died. Those three choices are what make the runbooks work.

## Survival kit (paper + password manager, outside Skynet)

The kit is **load-bearing** — without it, the encrypted backups are noise:

- age private key · restic password · PBS encryption key · **SSH CA private key**
- GitHub fine-grained PATs · rclone Google OAuth config
- Proxmox + OPNsense ISOs on USB
- NIC passthrough PCI IDs + BIOS notes (versioned in `runbooks/dr/pci-passthrough.md`)
- one printed page: *"clone the repo, open `runbooks/dr/`, follow it."*

Verified **quarterly** (a constitution invariant).

## The two scenarios

### Network node dies (`runbooks/dr/DR-network-node.md`)

`server-proxmox-network` dies, taking OPNsense and all routing with it — the exact case the
static IP and GitHub-as-truth exist for:

1. **Workspace:** laptop + phone hotspot, clone both repos, run *any* CLI agent on the laptop —
   the payoff of agent-agnostic design is the DR agent needs nothing from the dead lab.
2. **Hypervisor:** install Proxmox from USB; `server-proxmox-network`, VLAN 50 native, 10.10.50.10.
3. **OPNsense — config-import (primary, ~30 min):** fresh install into VM 5001, redo NIC
   passthrough from the documented PCI IDs, **Restore** `config.xml` from `skynet-opnsense` — VLANs,
   aliases, rules, reservations, WAN failover in one import. (Secondary: PBS restore of VM 5001 —
   valid but needs L2 access to VLAN 20 *before* routing exists; config-import has no chicken-and-egg.)
4. **Verify** routing/DNS/DHCP, then restore remaining guests from PBS.
5. **Reconcile:** collectors run, `inventory/` diffed against the last pre-disaster commit; a green
   diff ends the disaster.

### Core node dies with PBS aboard (`runbooks/dr/DR-core-node.md`)

Core dies **with PBS on it** → pull the datastore from Google Drive (L5), stand PBS up first, then
Unraid, skynet-ops, the rest. This is why L5 (PBS → Drive) exists and why its completeness is
guarded (see the A6 story in [build-log](../history/build-log.md)).

## Design dependencies (don't let these rot)

- **PCI passthrough IDs** must stay current in `runbooks/dr/pci-passthrough.md` (two Intel 82576
  dual-port NICs, bus 03/04, `ovmf`/`q35`) — a wrong ID blocks OPNsense rebuild.
- **The `skynet-opnsense` repo** must actually exist and receive os-git-backup pushes — an A6
  tabletop found the runbook naming a repo that didn't exist. Drilled in graduation; keep it true.
- **L5 completeness** must be guarded, not assumed — the A6 drill found the off-site PBS copy ~46%
  incomplete with nothing checking. Fixed with an `rclone check` completion guard.

## Planned expansion

- A periodic **DR game-day** beyond the graduation drills, on a cadence, as more hosts come under
  management.
- As services grow, `restore-service.md` scales per-service (DB pre-hooks etc.) — tracked in
  [gitops-loop](gitops-loop.md) / [backup-strategy](../backup-strategy.md), not here.
