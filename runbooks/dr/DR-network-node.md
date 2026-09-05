---
summary: "Recover when server-proxmox-network is dead — OPNsense and routing gone."
trigger: "Network node or OPNsense is dead"
tier: "T3"
executor: "human-supervised Proxmox and OPNsense recovery"
rollback: "preserve surviving configuration and stop before irreversible steps"
---

# DR — server-proxmox-network is dead (OPNsense + routing gone)

**Tier:** **T3** (human-supervised hypervisor and OPNsense recovery). **Trigger:**
`server-proxmox-network` or OPNsense is unavailable and routing is gone.

The recovery agent needs no resource from the dead lab; use the versioned repositories and survival kit.

## Preconditions

- Use a laptop with phone-hotspot connectivity; the dead lab is not a dependency.
- Clone both repositories (`skynet`, `skynet-opnsense`) and have the survival kit, install media, and
  documented PCI IDs available.

## Steps

### Prepare the workspace

Run the recovery CLI from the laptop. Keep the source repositories unchanged.

### Rebuild the hypervisor
Install Proxmox VE from USB. Bring up `server-proxmox-network`, VLAN 50 native, 10.10.50.10.
(The switch still holds L2 config.)

### Restore OPNsense — config import path (primary)
1. Fresh install into a new VM 5001.
2. Redo NIC passthrough from the documented PCI IDs (`runbooks/dr/pci-passthrough.md` + survival kit).
3. **System → Configuration → Restore** with `config.xml` from `skynet-opnsense`.
   VLANs, aliases, rules, reservations, WAN failover — one import.

Secondary path: restore VM 5001 from PBS only when L2 access to VLAN 20 is already available.

### Restore remaining guests

Restore the node's remaining guests from PBS after routing and DNS are available.

## Verify
Confirm routing, DNS, and DHCP are working, then verify guest reachability and service health.

## Rollback

If the fresh VM or config import fails, stop it and retry from the untouched `config.xml` or a PBS
restore into a fresh target. Do not overwrite the source repository or destroy the only recovery copy.

## Evidence

Run the collectors; diff `inventory/` against the last pre-disaster commit. A green diff
and a journal entry recording the import source, VMID, guest restores, and verification ends the
disaster.
