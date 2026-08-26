{ inputs, ... }:
# Wires home-manager as a NixOS module so ~aliammar is declarative too (the "flake proper, not
# the bootstrap" decision). useUserPackages puts home.packages in the system profile; the actual
# operator config lives in nix/home/aliammar.nix.
{
  home-manager.useGlobalPkgs = true;
  home-manager.useUserPackages = true;
  # First activation over a freshly-bootstrapped ~aliammar may find pre-existing files; keep a
  # backup instead of failing the switch.
  home-manager.backupFileExtension = "hm-bak";
  home-manager.extraSpecialArgs = { inherit inputs; };
  home-manager.users.aliammar = import ../home/aliammar.nix;
}
