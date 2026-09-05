{ ... }:
# Generic NixOS LXC template configuration.
{
  imports = [ ../../nix/modules/lxc-base.nix ];

  networking.hostName = "lxc-base";

  # First-install baseline; do not advance without reviewing stateful migrations.
  system.stateVersion = "26.05";
}
