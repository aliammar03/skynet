---
summary: "Re-establish NIC passthrough for VM 5001 (OPNsense) after a rebuild."
trigger: "NIC passthrough for OPNsense"
tier: "T3"
executor: "human-supervised Proxmox host configuration"
rollback: "restore prior VM and host PCI configuration"
---

# NIC passthrough — VM 5001 (OPNsense)

**Tier:** **T3** (human-supervised Proxmox host configuration). **Trigger:** a fresh or rebuilt VM
5001 needs OPNsense NIC passthrough. These are non-secret PCI and BIOS facts.

## Preconditions

- Proxmox is installed on the network node and VM 5001 is stopped.
- IOMMU is enabled and `vfio-pci` is available on the host.
- Confirm the four Intel 82576 functions by device ID before applying addresses; PCI enumeration can
  change after hardware or BIOS changes.

## Steps

### Set VM firmware and machine type

| Setting | Value |
|---|---|
| `bios` | **ovmf** (UEFI — OVMF, not SeaBIOS) |
| `machine` | **q35** (PCIe topology; passthrough will not attach on i440fx) |

### Attach the four NIC functions

VM 5001 passes **all four ports of two Intel 82576 dual-port GbE cards** — one card on PCI
bus `03`, the other on bus `04`. Re-add each as a PCIe host device in the same order:

| qm config | PCI address | Device | Vendor:Device |
|---|---|---|---|
| `hostpci0` | `0000:03:00.0` | Intel 82576 Gigabit (card A, port 0) | `8086:10e8` |
| `hostpci1` | `0000:03:00.1` | Intel 82576 Gigabit (card A, port 1) | `8086:10e8` |
| `hostpci2` | `0000:04:00.0` | Intel 82576 Gigabit (card B, port 0) | `8086:10e8` |
| `hostpci3` | `0000:04:00.1` | Intel 82576 Gigabit (card B, port 1) | `8086:10e8` |

Each entry is `pcie=1`. Recreate with, e.g.:

```bash
qm set 5001 --hostpci0 0000:03:00.0,pcie=1 \
             --hostpci1 0000:03:00.1,pcie=1 \
             --hostpci2 0000:04:00.0,pcie=1 \
             --hostpci3 0000:04:00.1,pcie=1
qm set 5001 --bios ovmf --machine q35
```

> ⚠️ **Match by device, not just address.** If PCI enumeration shifts after a hardware/BIOS
> change, find the four `[8086:10e8]` 82576 functions with `lspci -nn | grep 10e8` and pass
> *those* addresses — the ordering (card A then card B) is what OPNsense's `config.xml` expects
> its interfaces to map onto.

### Leave the node NICs on the host

For orientation during a rebuild, the network node also has these onboard/other NICs, which
stay with Proxmox (do **not** pass them to 5001):

- `05:00.0` Intel 82574L `[8086:10d3]`
- `06:00.0` Realtek RTL8111/8168/8211/8411 `[10ec:8168]`
- `07:00.0` Intel 82574L `[8086:10d3]`

## Verify

Run `qm config 5001` and confirm `bios: ovmf`, `machine: q35`, and `hostpci0` through `hostpci3`
match the four `[8086:10e8]` functions in card-A then card-B order. Boot OPNsense and verify its
interfaces map to the intended VLAN/WAN/LAN ports.

## Rollback

Stop VM 5001 and remove the `hostpci0`–`hostpci3` assignments if the passthrough prevents boot. Keep
the host NICs unassigned to the VM; retry only after confirming IOMMU and the device addresses.

## Evidence

Record `qm config 5001`, the `lspci -nn` device matches, and the OPNsense interface mapping in the
recovery journal. Do not record credentials or private key material.
