{
  description = "Skynet host definitions — declarative NixOS, piloted on vm-skynet-ops (SKY-007)";

  # Rationale, layout, and the twin/cutover model live in nix/README.md + docs/system-design.md.
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";
    # Fast-moving agent CLIs (claude-code/codex/antigravity) come from unstable, not npm — see
    # nix/modules/agent-clis.nix. Kept as a separate input so the host stays on stable 26.05.
    nixpkgs-unstable.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    impermanence.url = "github:nix-community/impermanence";
    disko = {
      url = "github:nix-community/disko";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    sops-nix = {
      url = "github:Mic92/sops-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    deploy-rs = {
      url = "github:serokell/deploy-rs";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    { self, nixpkgs, disko, sops-nix, deploy-rs, ... }@inputs:
    let
      system = "x86_64-linux";
    in
    {
      nixosConfigurations.vm-skynet-ops = nixpkgs.lib.nixosSystem {
        inherit system;
        specialArgs = { inherit inputs; };
        modules = [
          disko.nixosModules.disko
          sops-nix.nixosModules.sops
          inputs.impermanence.nixosModules.impermanence
          ./hosts/vm-skynet-ops
        ];
      };

      # The parallel twin on a temp IP (Phase 1b). Same host, only the network identity differs;
      # retired at cutover (1d).
      nixosConfigurations.vm-skynet-ops-nix = nixpkgs.lib.nixosSystem {
        inherit system;
        specialArgs = { inherit inputs; };
        modules = [
          disko.nixosModules.disko
          sops-nix.nixosModules.sops
          inputs.impermanence.nixosModules.impermanence
          ./hosts/vm-skynet-ops-nix
        ];
      };

      # deploy-rs day-2: magicRollback auto-reverts if it can't reconnect (~30s) — the decisive
      # feature for an LLM operator (a config that kills SSH self-heals instead of bricking).
      # hostname is the CUTOVER identity; 1b/1c drive the twin over its temp IP with --hostname.
      deploy.nodes.vm-skynet-ops = {
        hostname = "10.10.90.90";
        profiles.system = {
          user = "root";
          sshUser = "svc-ops";
          path = deploy-rs.lib.${system}.activate.nixos self.nixosConfigurations.vm-skynet-ops;
          magicRollback = true;
          autoRollback = true;
        };
      };

      # The twin's day-2 node (Phase 1b/1c). deploy .#vm-skynet-ops-nix drives the temp IP;
      # the 1c magic-rollback round-trip is proven here, never on the live box.
      deploy.nodes.vm-skynet-ops-nix = {
        hostname = "10.10.90.91";
        profiles.system = {
          user = "root";
          sshUser = "svc-ops";
          path = deploy-rs.lib.${system}.activate.nixos self.nixosConfigurations.vm-skynet-ops-nix;
          magicRollback = true;
          autoRollback = true;
        };
      };

      # `nix flake check` runs deploy-rs's own schema checks over the node definitions.
      checks.${system} = deploy-rs.lib.${system}.deployChecks self.deploy;
    };
}
