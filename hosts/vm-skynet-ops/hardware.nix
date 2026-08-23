{ modulesPath, ... }:
# VirtIO guest on Proxmox q35 + OVMF (UEFI). Boot layout pairs with disko.nix.
{
  imports = [ (modulesPath + "/profiles/qemu-guest.nix") ];

  # q35 exposes virtio over PCIe; VirtIO Block gives /dev/vda (see disko.nix).
  boot.initrd.availableKernelModules = [ "virtio_pci" "virtio_scsi" "virtio_blk" "sd_mod" ];
  boot.kernelModules = [ ];

  # UEFI/OVMF: systemd-boot on the ESP. canTouchEfiVariables registers the boot entry in the
  # VM's EFI NVRAM (Proxmox provides the EFI disk when you add one to the shell).
  boot.loader.systemd-boot.enable = true;
  boot.loader.systemd-boot.configurationLimit = 10; # cap generations so the ESP can't fill
  boot.loader.efi.canTouchEfiVariables = true;
}
