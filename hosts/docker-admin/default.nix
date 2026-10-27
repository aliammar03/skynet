# docker-admin — admin Docker host. VMID 5040 · 10.10.50.40 · VLAN 50 (+60) · proxmox-network.
{ config, lib, ... }:
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

  # Alertmanager runs as nobody (65534) and doesn't take its folder over by itself (skynetv2.md →
  # Conventions → Data).
  systemd.tmpfiles.rules = [ "d /opt/appdata/alertmanager/data 0700 65534 65534 -" ];

  # P5 (stacks/admin/metrics, stacks/admin/logs). This host's own containers reach its exporters and
  # vlagent from a Docker bridge, not from 10.10.50.40. vlagent runs on the host's network, so this
  # firewall, not a published port, decides who may send it logs: the hosts that ship their journal
  # (modules/observability.nix; PBS from pbs/etc/), as OPNsense's ROLE_LOG_SHIPPERS does.
  networking.firewall.extraCommands =
    let
      ports = lib.concatMapStringsSep "," toString (config.skynet.metricsPorts ++ [ 9429 ]);
      shippers = [
        "10.10.90.91" # ops
        "10.10.100.10" # docker-dmz
        "10.10.70.50" # technitium-network
        "10.10.70.51" # technitium-core
        "10.10.20.40" # PBS
        "10.10.50.24" # PBS on VLAN 50: its upload to this host leaves by that NIC (pbs/README.md)
      ];
    in
    ''
      iptables -A nixos-fw -i br-+ -p tcp -m multiport --dports ${ports} -j nixos-fw-accept
    ''
    + lib.concatMapStrings (ip: ''
      iptables -A nixos-fw -p tcp -s ${ip} --dport 9429 -j nixos-fw-accept
    '') shippers;
}
