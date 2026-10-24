#!/bin/sh
# Creates the docker-admin VM on server-proxmox-network. Run as root on the node; the installer ISO
# (`nix build .#installer-docker-admin`) must be in local:iso. MACs must match net.nix.
# net0: VLAN 50 is vmbr0's untagged VLAN on this node, so no tag. net1: VLAN 60, macvlan parent.
# Ballooning: 2 GB guaranteed (~0.9 GB in use); the rest, mostly page cache, goes back to the node
# when it passes 80%.
set -eu
qm create 5040 --name docker-admin --machine q35 --bios ovmf --ostype l26 --cpu host --cores 2 \
  --memory 4096 --balloon 2048 --efidisk0 local-lvm:1,efitype=4m,pre-enrolled-keys=0 \
  --scsihw virtio-scsi-single --scsi0 local-lvm:32,ssd=1,discard=on,iothread=1 \
  --net0 virtio=BC:24:11:50:40:01,bridge=vmbr0 \
  --net1 virtio=BC:24:11:50:40:60,bridge=vmbr0,tag=60 \
  --serial0 socket --agent enabled=1 --onboot 1 \
  --ide2 local:iso/nixos-installer-docker-admin.iso,media=cdrom --boot 'order=scsi0;ide2'
qm start 5040
