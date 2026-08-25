{ lib, ... }:
# The parallel twin (SKY-007 Phase 1b): the ops-VM flake on a TEMP identity, so provisioning and
# validation never touch the live 10.10.90.90/.99. Everything else is inherited from the real host
# unchanged — this override is only the network identity. At cutover (1d) the twin takes the real
# identity (deploy .#vm-skynet-ops) and this config + its CI line are retired.
{
  imports = [ ../vm-skynet-ops ];

  networking.hostName = lib.mkForce "vm-skynet-ops-nix";
  networking.interfaces.ens18.ipv4.addresses = lib.mkForce [
    { address = "10.10.90.91"; prefixLength = 24; }
  ];
}
