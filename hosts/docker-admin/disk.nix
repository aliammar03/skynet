# ext4 for the system (NixOS, the Nix store, Docker's images) on the first disk; the apps' data on a
# second, btrfs, so btrbk can snapshot /opt/appdata for the backups and restores, as on docker-dmz
# (skynetv2.md → P6 → PRs and order, step 4). The second disk came after the install: its first
# format was by hand to this layout, which a rebuild then repeats.
{
  disko.devices.disk.data = {
    type = "disk";
    device = "/dev/sdb";
    content = {
      type = "gpt";
      partitions = {
        # 32 GiB (proxmox.sh): 13 months of metrics (~12 GB at P5's 30 MB a day), logs up to 4 GiB,
        # Grafana's 0.8 GB, and a week of snapshots. No nofail: if this doesn't mount, the host
        # stops at boot instead of starting the apps on an empty /opt/appdata.
        appdata = {
          size = "100%";
          content = {
            type = "btrfs";
            extraArgs = [
              "-f"
              "-L"
              "appdata"
            ];
            # The top level, where btrbk finds @appdata and keeps @snapshots beside it.
            mountpoint = "/mnt/appdata-pool";
            mountOptions = [ "noatime" ];
            subvolumes = {
              "@appdata" = {
                mountpoint = "/opt/appdata";
                mountOptions = [ "noatime" ];
              };
              "@snapshots" = { };
            };
          };
        };
      };
    };
  };
  disko.devices.disk.main = {
    type = "disk";
    device = "/dev/sda";
    content = {
      type = "gpt";
      partitions = {
        ESP = {
          size = "512M";
          type = "EF00";
          content = {
            type = "filesystem";
            format = "vfat";
            mountpoint = "/boot";
            mountOptions = [ "umask=0077" ];
          };
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
