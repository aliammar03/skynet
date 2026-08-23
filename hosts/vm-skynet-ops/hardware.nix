{ modulesPath, ... }:
# Virtio guest on Proxmox. Boot layout pairs with disko.nix.
{
  imports = [ (modulesPath + "/profiles/qemu-guest.nix") ];

  boot.initrd.availableKernelModules = [ "virtio_pci" "virtio_scsi" "virtio_blk" "ahci" "sd_mod" ];
  boot.kernelModules = [ ];

  # Proxmox default is SeaBIOS (legacy). disko registers /dev/vda with grub via the EF02
  # boot partition (see disko.nix) — so we only ENABLE grub here; setting .device too would
  # list vda twice ("duplicated devices in mirroredBoots"). If the twin is OVMF/UEFI at 1b,
  # switch to systemd-boot + an ESP there.
  boot.loader.grub.enable = true;
}
