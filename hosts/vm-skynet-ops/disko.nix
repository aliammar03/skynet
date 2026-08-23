{ ... }:
# Declarative disk layout — nixos-anywhere reprovisions the twin's disk to this at 1b.
# Single virtio disk, GPT, legacy-BIOS grub. Matches 9090's virtio profile (device sizes
# come from the VM shell, not here — the root partition takes 100%).
{
  disko.devices.disk.main = {
    type = "disk";
    device = "/dev/vda";
    content = {
      type = "gpt";
      partitions = {
        boot = {
          size = "1M";
          type = "EF02"; # BIOS boot partition for grub on GPT (SeaBIOS)
        };
        root = {
          size = "100%";
          content = {
            type = "filesystem";
            format = "ext4";
            mountpoint = "/";
          };
        };
      };
    };
  };
}
