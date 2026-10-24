#!/bin/sh
# Creates the ops VM on server-proxmox-core. Run as root on the node; the ISO must be in local:iso.
# Ballooning: 5 GB guaranteed (~2.2 GB in use, plus nix builds' peaks); the rest, mostly page cache,
# goes back to the node when it passes 80%.
set -eu
qm create 9091 --name ops --machine q35 --bios ovmf --ostype l26 --cpu host --cores 4 \
  --memory 8192 --balloon 5120 --efidisk0 local-lvm:1,efitype=4m,pre-enrolled-keys=0 \
  --scsihw virtio-scsi-single --scsi0 local-lvm:64,ssd=1,discard=on,iothread=1 \
  --net0 virtio,bridge=vmbr0,tag=90 --serial0 socket --agent enabled=1 --onboot 1 \
  --ide2 local:iso/latest-nixos-minimal-x86_64-linux.iso,media=cdrom --boot 'order=scsi0;ide2'
qm start 9091
