# NIC passthrough — VM 5001 (OPNsense)

Captured 2026-08-16 from `server-proxmox-network` (A6 DR tabletop). This is the hardware
addressing a DR rebuild needs to re-create OPNsense's NIC passthrough after a fresh install
(`DR-network-node.md` step 2). Not secret — plain PCI/BIOS facts, safe in the repo.

## VM firmware / machine type (required for PCIe passthrough)

| Setting | Value |
|---|---|
| `bios` | **ovmf** (UEFI — OVMF, not SeaBIOS) |
| `machine` | **q35** (PCIe topology; passthrough will not attach on i440fx) |

## Passed-through devices

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

## NOT passed through (the node's own NICs — leave on the host)

For orientation during a rebuild, the network node also has these onboard/other NICs, which
stay with Proxmox (do **not** pass them to 5001):

- `05:00.0` Intel 82574L `[8086:10d3]`
- `06:00.0` Realtek RTL8111/8168/8211/8411 `[10ec:8168]`
- `07:00.0` Intel 82574L `[8086:10d3]`

## Prerequisites (host)

IOMMU must be on for passthrough: `intel_iommu=on` on the kernel cmdline and the `vfio-pci`
modules loaded — standard Proxmox passthrough setup, re-applied during the DR hypervisor install
(`DR-network-node.md` step 1) before 5001 can bind these devices.
