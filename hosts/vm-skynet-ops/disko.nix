{ ... }:
# Declarative disk layout — nixos-anywhere reprovisions the twin's disk to this at 1b.
# Single VirtIO Block disk (/dev/vda), GPT, UEFI: an ESP for systemd-boot + an ext4 root.
# Disk size comes from the VM shell (root takes 100%), so the twin's 64 GB is honored.
{
  disko.devices.disk.main = {
    type = "disk";
    device = "/dev/vda";
    content = {
      type = "gpt";
      partitions = {
        ESP = {
          size = "1G"; # roomy for many systemd-boot generations (kernel+initrd each) — 512M fills
          type = "EF00"; # EFI System Partition (UEFI/OVMF)
          content = {
            type = "filesystem";
            format = "vfat";
            mountpoint = "/boot";
            mountOptions = [ "umask=0077" ];
          };
        };
        # Impermanence: / is a tmpfs (see nix/modules/impermanence.nix); this ext4 holds the Nix
        # store at /nix plus the persisted state under /nix/persist. Named "nix" for clarity.
        nix = {
          size = "100%";
          content = {
            type = "filesystem";
            format = "ext4";
            mountpoint = "/nix";
          };
        };
      };
    };
  };
}
