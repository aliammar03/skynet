{ ... }:
# The ops VM as a flake. Static-first lab (see lab addressing convention); the network identity
# baked here is the CUTOVER target — the 1b/1c twin overrides the address for its temp IP.
{
  imports = [
    ./hardware.nix
    ./disko.nix
    ../../nix/modules/base.nix
    ../../nix/modules/ops-user.nix
    ../../nix/modules/ssh-ca.nix
    ../../nix/modules/timers.nix
    ../../nix/modules/secrets.nix
  ];

  networking.hostName = "vm-skynet-ops";
  networking.useDHCP = false;
  # ens18 = the predictable name for the Proxmox virtio NIC. Verify against the twin at 1b.
  networking.interfaces.ens18.ipv4.addresses = [
    { address = "10.10.90.90"; prefixLength = 24; }
    { address = "10.10.90.99"; prefixLength = 24; } # firewall alias (skynet-ops agent VM)
  ];
  networking.defaultGateway = "10.10.90.1"; # VLAN 90 gateway — confirm at 1b
  networking.nameservers = [ "10.10.70.51" ]; # tdns-core, the real resolver

  # First-install baseline; never advance blind (would trigger stateful migrations on rebuild).
  system.stateVersion = "26.05";
}
