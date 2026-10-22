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

  skynet.docker.macvlan = {
    name = "adm60";
    parent = "adm60";
    subnet = "10.10.60.0/24";
    gateway = "10.10.60.1";
  };
}
