{ pkgs, ... }:
# NixOS LXC build target.
# (flake-built template → pct create → boot → in-place `nixos-rebuild switch` applies) once, on a
# container we destroy at the end. Not a real service host — hosts/lxc-adguard-network/ (Phase 3) is
# the first of those. Keep it minimal: the base module plus a hostname and one marker package whose
# presence/absence is the decisive in-place-rebuild test (add it, switch, confirm it lands).
{
  imports = [ ../../nix/modules/lxc-base.nix ];

  networking.hostName = "lxc-proof";

  # In-place rebuild marker: add a package, `nixos-rebuild switch`,
  # confirm it applies. Its presence in a NEW generation = the historically-broken step works here.
  environment.systemPackages = [ pkgs.hello ];

  # First-install baseline; never advance blind (would trigger stateful migrations on rebuild).
  system.stateVersion = "26.05";
}
