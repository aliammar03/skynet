# ops — the agent's VM. VMID 9091 · 10.10.90.91 · VLAN 90 · proxmox-core.
{ ... }:
{
  imports = [
    ./hardware.nix
    ./disk.nix
    ../../modules/base.nix
    ../../modules/agent.nix
    ../../modules/pbs-drift.nix
  ];

  networking.hostName = "ops";

  systemd.network.networks."10-lan" = {
    matchConfig.Name = "en*";
    address = [ "10.10.90.91/24" ];
    gateway = [ "10.10.90.1" ];
    dns = [
      "10.10.70.51"
      "10.10.70.50"
    ];
  };
}
