{ modulesPath, ... }:
# Virtio guest on Proxmox. Boot layout pairs with disko.nix.
{
  imports = [ (modulesPath + "/profiles/qemu-guest.nix") ];

  boot.initrd.availableKernelModules = [ "virtio_pci" "virtio_scsi" "virtio_blk" "ahci" "sd_mod" ];
  boot.kernelModules = [ ];

  # Proxmox default is SeaBIOS (legacy). grub on the GPT BIOS-boot partition (see disko.nix).
  # If the twin is created with OVMF/UEFI at 1b, switch to systemd-boot + an ESP there.
  boot.loader.grub = {
    enable = true;
    device = "/dev/vda";
    efiSupport = false;
  };
}
