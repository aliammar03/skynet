# docker-admin — admin Docker host. VMID 5040 · 10.10.50.40 · VLAN 50 (+60) · proxmox-network.
{ ... }:
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

  networking.hostName = "docker-admin";

  # NICs renamed by MAC, so `lan` and `adm60` never swap.
  systemd.network.links."10-lan" = {
    matchConfig.MACAddress = net.lan.mac;
    linkConfig.Name = "lan";
  };
  systemd.network.links."10-adm60" = {
    matchConfig.MACAddress = net.adm60.mac;
    linkConfig.Name = "adm60";
  };
  systemd.network.networks."10-lan" = {
    matchConfig.Name = "lan";
    address = [ net.lan.address ];
    gateway = [ net.lan.gateway ];
    inherit (net) dns;
  };
  # Up with no address: only the macvlan's containers live on VLAN 60.
  systemd.network.networks."20-adm60" = {
    matchConfig.Name = "adm60";
    networkConfig.LinkLocalAddressing = "no";
    linkConfig.RequiredForOnline = "no";
  };

  # PBS's datastore (Unraid share `pbs`), read-only, for pbs-offsite; mounted on first access, so a
  # down Unraid only fails that night's copy. Unraid maps every read from here to uid 34, PBS's
  # `backup`, which owns the datastore. soft: a lost server fails the read instead of hanging it.
  fileSystems."/mnt/pbs-datastore" = {
    device = "10.10.20.20:/mnt/user/pbs";
    fsType = "nfs";
    options = [
      "ro"
      "nfsvers=4.2"
      "soft"
      "noauto"
      "x-systemd.automount"
      "x-systemd.idle-timeout=15min"
      "x-systemd.mount-timeout=30s"
    ];
  };

  skynet.docker.macvlan = {
    name = "adm60";
    parent = "adm60";
    subnet = "10.10.60.0/24";
    gateway = "10.10.60.1";
  };
  skynet.docker.docoTarget = "admin";
}
