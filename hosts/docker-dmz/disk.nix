# ext4 for the system (NixOS, the Nix store, Docker's images), btrfs for the apps' data, so btrbk can
# snapshot /opt/appdata for the backups (skynetv2.md → P4 → docker-dmz: /opt/appdata on btrfs).
{
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
        # 25 GB used at the move, 21.6 of it Docker's images; the weekly prune keeps a replaced
        # image for 7 days.
        root = {
          size = "40G";
          content = {
            type = "filesystem";
            format = "ext4";
            mountpoint = "/";
          };
        };
        # No nofail: if this doesn't mount, the host stops at boot instead of starting the apps on
        # an empty /opt/appdata.
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
}
