{
  description = "Skynet v2 — the homelab, declared. Plan: skynetv2.md";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";
    # Fast-moving agent tooling only (claude-code, mcp-nixos); hosts stay on the release.
    nixpkgs-unstable.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    disko = {
      url = "github:nix-community/disko";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    sops-nix = {
      url = "github:Mic92/sops-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    comin = {
      url = "github:nlewo/comin";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    { self, nixpkgs, ... }@inputs:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
      mkHost =
        name:
        nixpkgs.lib.nixosSystem {
          inherit system;
          specialArgs = { inherit inputs; };
          modules = [ ./hosts/${name} ];
        };
      # `nix build .#installer-<host>` → result/iso/*.iso (modules/installer.nix).
      mkInstaller =
        name:
        (nixpkgs.lib.nixosSystem {
          inherit system;
          modules = [ (import ./modules/installer.nix (import ./hosts/${name}/net.nix)) ];
        }).config.system.build.isoImage;
    in
    {
      nixosConfigurations.ops = mkHost "ops";
      nixosConfigurations.docker-admin = mkHost "docker-admin";

      packages.${system}.installer-docker-admin = mkInstaller "docker-admin";

      devShells.${system}.default = pkgs.mkShell {
        packages = with pkgs; [
          sops
          age
          ssh-to-age
          nixos-anywhere
          gh
          jq
        ];
      };

      formatter.${system} = pkgs.nixfmt;
    };
}
