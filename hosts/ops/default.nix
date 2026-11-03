# ops — the agent's VM. VMID 9091 · 10.10.90.91 · VLAN 90 · proxmox-core.
{ config, ... }:
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

  # On Ali's tailnet as `tag:ops` (D14), in userspace: ops's own routes and DNS stay as they are, and
  # the agent reaches tailnet machines over SSH through `tailscale nc` (`Host *.ts.net`). What
  # `tag:ops` may reach is the tailnet policy's. The auth key serves the first login only; the node
  # key then stays in /var/lib/tailscale.
  services.tailscale = {
    enable = true;
    interfaceName = "userspace-networking";
    authKeyFile = config.sops.secrets.tailscale_authkey.path;
    extraUpFlags = [
      "--advertise-tags=tag:ops"
      "--accept-dns=false"
      "--operator=skynet" # the agent may run `tailscale nc` and `tailscale status`
    ];
  };
  sops.secrets.tailscale_authkey = { };
  programs.ssh.extraConfig = ''
    Host *.ts.net
      ProxyCommand ${config.services.tailscale.package}/bin/tailscale nc %h %p
  '';
}
