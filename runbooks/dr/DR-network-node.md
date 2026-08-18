---
summary: "Recover when server-proxmox-network is dead — OPNsense and routing gone."
trigger: "Network node or OPNsense is dead"
tokens: 350
---

# DR — server-proxmox-network is dead (OPNsense + routing gone)

This is the reason truth lives on GitHub and skynet-ops has a static IP. The DR agent
needs **nothing** from the dead lab.

## 0. Workspace
Laptop + phone hotspot. Clone **both** repos (`skynet`, `skynet-opnsense`). Run any
CLI agent on the laptop (agent-agnostic design = the DR agent needs no lab resource).

## 1. Hypervisor
Install Proxmox VE from USB. Bring up `server-proxmox-network`, VLAN 50 native, 10.10.50.10.
(The switch still holds L2 config.)

## 2. OPNsense — config-import path (primary, ~30 min)
1. Fresh install into a new VM 5001.
2. Redo NIC passthrough from the documented PCI IDs (`runbooks/dr/pci-passthrough.md` + survival kit).
3. **System → Configuration → Restore** with `config.xml` from `skynet-opnsense`.
   VLANs, aliases, rules, reservations, WAN failover — one import.

> Secondary path: PBS restore of VM 5001 — valid but needs L2 access to VLAN 20 *before*
> routing exists. Config-import has no chicken-and-egg; prefer it.

## 3. Verify
Routing, DNS, DHCP all up. Then restore the node's remaining guests from PBS normally.

## 4. Reconcile
Run the collectors; diff `inventory/` against the last pre-disaster commit. A green diff
ends the disaster.
