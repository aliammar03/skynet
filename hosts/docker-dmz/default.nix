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
  # calibre has no login of its own: caddy-apps reaches it on a network only the two share.
  skynet.docker.doorNetworks = [ "door-calibre" ];
  skynet.docker.docoTarget = "dmz";

  # Redis (paperless, jikan, aiometadata) asks for it at every start: its background saves fork.
  boot.kernel.sysctl."vm.overcommit_memory" = 1;

  # The receiving end of v1's data copy (README.md → v1's data).
  environment.systemPackages = [ pkgs.rsync ];

  # The agent is root here (D11): wheel = passwordless sudo (base.nix), each command logged in the
  # journal. Its key is still accepted from ops only.
  users.users.skynet.extraGroups = [ "wheel" ];
}
