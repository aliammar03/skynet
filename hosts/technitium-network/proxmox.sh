#!/bin/sh
# Creates the technitium-network VM on server-proxmox-network. Run as root on the node; the installer
# ISO (`nix build .#installer-technitium-network`) must be in local:iso. The MAC must match net.nix.
# net0: VLAN 70 (net services), tagged.
# No ballooning: 1 GB with ~0.4 GB in use leaves nothing worth reclaiming from a DNS server.
set -eu
qm create 7050 --name technitium-network --machine q35 --bios ovmf --ostype l26 --cpu host --cores 2 \
  --memory 1024 --balloon 0 --efidisk0 local-lvm:1,efitype=4m,pre-enrolled-keys=0 \
  --scsihw virtio-scsi-single --scsi0 local-lvm:16,ssd=1,discard=on,iothread=1 \
  --net0 virtio=BC:24:11:70:50:01,bridge=vmbr0,tag=70 \
  --serial0 socket --agent enabled=1 --onboot 1 \
  --ide2 local:iso/nixos-installer-technitium-network.iso,media=cdrom --boot 'order=scsi0;ide2'
qm start 7050
