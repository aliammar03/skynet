{ ... }:
# Impermanence ("erase your darlings"): the root filesystem is a tmpfs, wiped clean on EVERY boot.
# Only /nix (the store) and the paths declared below (kept on the /nix partition under /nix/persist)
# survive. Anything not persisted or declared by the flake evaporates on reboot — drift is impossible.
#
# Piloted while the old ops VM (9090) is a live fallback (SKY-007 1d). Persist-list reviewed by Ali;
# /var/log is kept (Ali's call). ~/.npm-global is NOT persisted — the agent CLIs are Nix now.
{
  # Ephemeral root in RAM. /nix + /boot are real (disko); everything else here is bind-mounted back.
  fileSystems."/" = {
    device = "tmpfs";
    fsType = "tmpfs";
    options = [ "defaults" "size=2G" "mode=755" ];
    neededForBoot = true;
  };

  environment.persistence."/nix/persist" = {
    hideMounts = true;
    directories = [
      "/opt/skynet-ops" # age.key (root 0600), certs, mirror — the bootstrap secret + T1 mirror
      "/home/aliammar" # repo checkout, gh auth, ops.env, known_hosts
      "/var/lib/docker" # docker daemon data
      "/var/lib/nixos" # uid/gid allocation stability across rebuilds
      "/var/lib/systemd" # timer Persistent= state, random seed
      "/var/log" # logs across reboots (Ali's call)
    ];
    files = [
      "/etc/machine-id" # stable machine-id
      "/etc/ssh/ssh_host_ed25519_key"
      "/etc/ssh/ssh_host_ed25519_key.pub"
      "/etc/ssh/ssh_host_rsa_key"
      "/etc/ssh/ssh_host_rsa_key.pub"
    ];
  };
}
