# Placeholder until install: nixos-anywhere --generate-hardware-config overwrites this file.
{ modulesPath, ... }:
{
  imports = [ (modulesPath + "/profiles/qemu-guest.nix") ];
  boot.initrd.availableKernelModules = [
    "ahci"
    "xhci_pci"
    "virtio_pci"
    "virtio_scsi"
    "sd_mod"
    "sr_mod"
  ];
  nixpkgs.hostPlatform = "x86_64-linux";
}
