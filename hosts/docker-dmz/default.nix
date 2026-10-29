# docker-dmz — apps Docker host. VMID 10010 · 10.10.100.10 · VLAN 100 · proxmox-core.
{ pkgs, ... }:
let
  net = import ./net.nix;
in
{
  imports = [
    ./hardware.nix
    ./disk.nix
    ../../modules/base.nix
    ../../modules/docker-host.nix
  ];

  networking.hostName = "docker-dmz";

  # One NIC, renamed by MAC: it carries the host IP and is the macvlan's parent.
  systemd.network.links."10-dmz" = {
    matchConfig.MACAddress = net.dmz.mac;
    linkConfig.Name = "dmz";
  };
  systemd.network.networks."10-dmz" = {
    matchConfig.Name = "dmz";
    address = [ net.dmz.address ];
    gateway = [ net.dmz.gateway ];
    inherit (net) dns;
  };

  # The doors' macvlan shares the host's NIC. The host and the macvlan's containers can't reach each
  # other directly, and nothing needs them to.
  skynet.docker.macvlan = {
    name = "dmz";
    parent = "dmz";
    subnet = "10.10.100.0/24";
    gateway = "10.10.100.1";
  };
  # calibre and kapowarr have no login of their own: caddy-apps reaches each on a network only the
  # two share. Komga and Uchiyomi have one, but read Ali's files, so nothing else on `edge` reaches
  # them either.
  skynet.docker.doorNetworks = [
    "door-calibre"
    "door-kapowarr"
    "door-komga"
    "door-uchiyomi"
  ];
  skynet.docker.docoTarget = "dmz";
  # /opt/appdata is btrfs (disk.nix): btrbk snapshots it for the backup and local restores.
  skynet.docker.appdataSnapshots = true;

  # Redis (paperless, jikan, aiometadata) asks for it at every start: its background saves fork.
  boot.kernel.sysctl."vm.overcommit_memory" = 1;

  # Unraid's share `Storage`, for every stack's storage and media (P8: comics and manga under
  # Books/). Unraid writes everything from here as nobody:users (99:100, all_squash). Mounted on first
  # access, and never idles out: the containers' bind mounts hold it. hard: a lost server stalls a
  # write until it is back, rather than failing it halfway (a torn CBZ); a mount that can't start in
  # 30 s fails the container's start instead, and doco-cd retries it.
  fileSystems."/mnt/storage" = {
    device = "10.10.20.20:/mnt/user/Storage";
    fsType = "nfs";
    options = [
      "nfsvers=4.2"
      "hard"
      "noauto"
      "x-systemd.automount"
      "x-systemd.mount-timeout=30s"
    ];
  };

  # Uchiyomi's extension engine runs as its image's user 1000 and doesn't take its folder over
  # (skynetv2.md → Conventions → Data).
  systemd.tmpfiles.rules = [ "d /opt/appdata/uchiyomi/engine 0750 1000 1000 -" ];

  # So copies can arrive over SSH (`--rsync-path='sudo rsync'`), as v1's data did.
  environment.systemPackages = [ pkgs.rsync ];

  # The agent is root here (D11): wheel = passwordless sudo (base.nix), each command logged in the
  # journal. Its key is still accepted from ops only.
  users.users.skynet.extraGroups = [ "wheel" ];
}
