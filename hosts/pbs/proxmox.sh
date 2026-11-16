#!/bin/sh
# Creates PBS's VM on server-proxmox-core. Run as root on the node; the automated-install ISO
# (`nix build .#installer-pbs`, README.md → Install) must be in local:iso as pbs-installer.iso.
# The VM installs PBS on its own and reboots into it. The disk comes first in the boot order: the
# empty disk falls through to the ISO once, and from then on the installed system boots.
# net0: VLAN 20 (Servers), tagged; answer.toml picks this NIC by its MAC.
# net1: VLAN 50 (Mgmt), untagged (vmbr0's native VLAN): the nodes' backups and restores reach PBS
# there without crossing OPNsense (README.md → Network). setup.sh names it and gives it its address.
# Ballooning: 1 GB guaranteed (0.6 GB peak in a week; 2026-10-29); verify, GC and backups use the
# rest as cache.
set -eu
qm create 2040 --name pbs --machine q35 --bios ovmf --ostype l26 --cpu host --cores 2 \
  --memory 4096 --balloon 1024 --efidisk0 local-lvm:1,efitype=4m,pre-enrolled-keys=0 \
  --scsihw virtio-scsi-single --scsi0 local-lvm:32,ssd=1,discard=on,iothread=1 \
  --net0 virtio=BC:24:11:20:40:01,bridge=vmbr0,tag=20 \
  --net1 virtio=BC:24:11:20:40:02,bridge=vmbr0 \
  --agent enabled=1 --onboot 1 \
  --ide2 local:iso/pbs-installer.iso,media=cdrom --boot 'order=scsi0;ide2'
qm start 2040
