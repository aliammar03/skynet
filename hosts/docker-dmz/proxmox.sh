#!/bin/sh
# Creates the docker-dmz VM on server-proxmox-core. Run as root on the node; the installer ISO
# (`nix build .#installer-docker-dmz`) must be in local:iso. The MAC must match net.nix.
# net0: VLAN 100 (DMZ), tagged: the host IP and the doors' macvlan parent.
# Ballooning: 6 GB guaranteed (apps use ~4.2 GB); the rest, mostly page cache, goes back to the node
# when it passes 80%.
set -eu
qm create 10010 --name docker-dmz --machine q35 --bios ovmf --ostype l26 --cpu host --cores 6 \
  --memory 10240 --balloon 6144 --efidisk0 local-lvm:1,efitype=4m,pre-enrolled-keys=0 \
  --scsihw virtio-scsi-single --scsi0 local-lvm:128,ssd=1,discard=on,iothread=1 \
  --net0 virtio=BC:24:11:00:10:01,bridge=vmbr0,tag=100 \
  --serial0 socket --agent enabled=1 --onboot 1 \
  --ide2 local:iso/nixos-installer-docker-dmz.iso,media=cdrom --boot 'order=scsi0;ide2'
qm start 10010
