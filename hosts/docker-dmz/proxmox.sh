#!/bin/sh
# Creates the docker-dmz VM on server-proxmox-core. Run as root on the node; the installer ISO
# (`nix build .#installer-docker-dmz`) must be in local:iso. The MAC must match net.nix.
# net0: VLAN 100 (DMZ), tagged: the host IP and the doors' macvlan parent.
# Ballooning: 10 GB guaranteed, up to 12 (its containers held 6.3 GiB before Mylar3 and SABnzbd, and
# the node had squeezed it to its old 8 GB floor, 0.7 GiB left; 2026-10-29), and double the balloon
# shares, so when the node passes 80% this VM gives back its page cache last.
# On the running VM: qm set 10010 --memory 12288 --balloon 10240, then qm reboot 10010.
# scsi0: 193 GiB, thin: the ESP, a 64 GiB root and 128 GiB of btrfs (disk.nix).
set -eu
qm create 10010 --name docker-dmz --machine q35 --bios ovmf --ostype l26 --cpu host --cores 6 \
  --memory 12288 --balloon 10240 --shares 2000 --efidisk0 local-lvm:1,efitype=4m,pre-enrolled-keys=0 \
  --scsihw virtio-scsi-single --scsi0 local-lvm:193,ssd=1,discard=on,iothread=1 \
  --net0 virtio=BC:24:11:00:10:01,bridge=vmbr0,tag=100 \
  --serial0 socket --agent enabled=1 --onboot 1 \
  --ide2 local:iso/nixos-installer-docker-dmz.iso,media=cdrom --boot 'order=scsi0;ide2'
qm start 10010
