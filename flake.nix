{
  description = "Skynet v2 — the homelab, declared. Plan: skynetv2.md";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";
    # Fast-moving tooling only (claude-code, mcp-nixos, PBS's install assistant); hosts stay on the
    # release.
    nixpkgs-unstable.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    disko = {
      url = "github:nix-community/disko";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    sops-nix = {
      url = "github:Mic92/sops-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    # Pinned to a commit, so the weekly flake.lock can't move it: comin deploys every host, and a
    # broken one can't deploy its own revert. The pin goes once a host change proves itself under a
    # timed rollback before it merges (skynetv2.md → P6 → Verify and roll back; the hosts PR). Its
    # newest release, v0.14.0, is older than this commit.
    comin = {
      url = "github:nlewo/comin/f95451172287f3cb36249a2cdef56efa9bbeef19";
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
      nixosConfigurations.technitium-network = mkHost "technitium-network";
      nixosConfigurations.technitium-core = mkHost "technitium-core";
      nixosConfigurations.docker-dmz = mkHost "docker-dmz";

      # One attrset: Nix can't merge repeated `packages.${system}.…` (a dynamic attribute name).
      packages.${system} = {
        installer-docker-admin = mkInstaller "docker-admin";
        installer-technitium-network = mkInstaller "technitium-network";
        installer-technitium-core = mkInstaller "technitium-core";
        installer-docker-dmz = mkInstaller "docker-dmz";
        # PBS isn't NixOS: Proxmox's own ISO, with pbs/answer.toml built in. The assistant comes from
        # unstable to match the ISO's installer (9.2; 26.05 has 9.1).
        installer-pbs = pkgs.callPackage ./pbs/installer.nix {
          inherit (inputs.nixpkgs-unstable.legacyPackages.${system}) proxmox-auto-install-assistant;
        };
      };

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
