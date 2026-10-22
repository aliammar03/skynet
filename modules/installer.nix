# A no-touch NixOS installer for one host: boots straight to SSH on the host's static IP (NIC
# matched by MAC) with the agent's key for root, so nixos-anywhere runs from ops and nobody types
# in a console. Only the installer trusts the agent's key; the installed system doesn't.
net:
{ lib, modulesPath, ... }:
{
  imports = [ "${modulesPath}/installer/cd-dvd/installation-cd-minimal.nix" ];

  networking.useNetworkd = true;
  networking.useDHCP = false;
  networking.enableIPv6 = false;
  systemd.network.networks."10-lan" = {
    matchConfig.MACAddress = net.lan.mac;
    address = [ net.lan.address ];
    gateway = [ net.lan.gateway ];
    inherit (net) dns;
  };

  networking.wireless.enable = lib.mkForce false;

  # The minimal ISO ships sshd but leaves it stopped until someone sets a password. Start it, and
  # allow keys only: the console users have empty passwords.
  systemd.services.sshd.wantedBy = lib.mkForce [ "multi-user.target" ];
  services.openssh.settings = {
    PermitRootLogin = lib.mkForce "prohibit-password";
    PasswordAuthentication = false;
    KbdInteractiveAuthentication = false;
  };
  users.users.root.openssh.authorizedKeys.keyFiles = [ ../hosts/ops/agent.pub ];

  boot.kernelParams = [ "console=ttyS0,115200" ];
  boot.supportedFilesystems.zfs = lib.mkForce false; # not used in the lab; smaller ISO
  time.timeZone = "Asia/Karachi";
}
