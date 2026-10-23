# technitium-core — DNS server. VMID 7051 · 10.10.70.51 · VLAN 70 · proxmox-core.
{ ... }:
let
  net = import ./net.nix;
in
{
  imports = [
    ./hardware.nix
    ./disk.nix
    ../../modules/base.nix
    ../../modules/dns.nix
  ];

  networking.hostName = "technitium-core";

  systemd.network.links."10-lan" = {
    matchConfig.MACAddress = net.lan.mac;
    linkConfig.Name = "lan";
  };
  systemd.network.networks."10-lan" = {
    matchConfig.Name = "lan";
    address = [ net.lan.address ];
    gateway = [ net.lan.gateway ];
  };
  # resolved is off (dns.nix), so resolv.conf comes from here: its own Technitium first.
  networking.nameservers = [ "127.0.0.1" ] ++ net.dns;
}
