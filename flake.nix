{
  description = "Skynet host definitions — declarative NixOS, piloted on vm-skynet-ops (SKY-007)";

  # Rationale, layout, and the twin/cutover model live in nix/README.md + docs/system-design.md.
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";
    # Fast-moving agent CLIs (claude-code/codex/antigravity) come from unstable, not npm — see
    # nix/modules/agent-clis.nix. Kept as a separate input so the host stays on stable 26.05.
    nixpkgs-unstable.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    impermanence.url = "github:nix-community/impermanence";
    home-manager = {
      url = "github:nix-community/home-manager/release-26.05";
      inputs.nixpkgs.follows = "nixpkgs";
    };
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
    # lxc-athena's own repo (private) — pinned for break-glass deploy only; the box's day-2 lives
    # THERE (in-place rebuild), not here. flake.lock records the exact rev; fetching needs a GitHub
    # token (the ops account has read access). follows dedupe the shared inputs in our lock.
    athena = {
      url = "github:aliammar03/athena";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.home-manager.follows = "home-manager";
      inputs.deploy-rs.follows = "deploy-rs";
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
          inputs.home-manager.nixosModules.home-manager
          ./hosts/vm-skynet-ops
        ];
      };

      # SKY-021 — the throwaway proof CT (Phase 1). Unprivileged proxmox-lxc; the tarball output
      # below is the CT template. Its deploy-rs node (below) proved magic-rollback + sops-nix work in
      # a container (Phase 2); the real service host gets its own flake host + deploy node in Phase 3.
      nixosConfigurations.lxc-proof = nixpkgs.lib.nixosSystem {
        inherit system;
        specialArgs = { inherit inputs; };
        modules = [ ./hosts/lxc-proof ];
      };

      # `nix build .#lxc-proof-tarball` → the .tar.xz to upload as a Proxmox CT template
      # (local:vztmpl/). The proxmox-lxc module exposes it as system.build.tarball.
      packages.${system}.lxc-proof-tarball =
        self.nixosConfigurations.lxc-proof.config.system.build.tarball;

      # SKY-021 P3 — adguard-core (CT 731), the first real pool CT off the Debian community-script
      # path. Its AdGuard config lives in Nix (rendered via a sops template); day-2 is deploy-rs
      # magic-rollback (P2); secrets via Option C (per-CT age key). sops-nix module wired in here.
      nixosConfigurations.lxc-adguard-core = nixpkgs.lib.nixosSystem {
        inherit system;
        specialArgs = { inherit inputs; };
        modules = [
          sops-nix.nixosModules.sops
          ./hosts/lxc-adguard-core
        ];
      };

      # lxc-athena's INSIDE is owned by its own repo (aliammar03/athena, the `athena` input above) —
      # Ali edits it in place on the box and rebuilds from ~/athena (ATH-000). Skynet keeps only the
      # ENVELOPE: the tofu CT (tofu/pool-cts.tf) + the HOST_ATHENA firewall mapping. The break-glass
      # deploy node below tracks the pinned athena input; bump it with `nix flake lock --update-input
      # athena` (needs a GitHub token for the private repo — the ops account has read access).

      # deploy-rs day-2: magicRollback auto-reverts if it can't reconnect (~30s) — the decisive
      # feature for an LLM operator (a config that kills SSH self-heals instead of bricking).
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

      # SKY-021 P2 — the throwaway proof CT gets the SAME magic-rollback day-2 model, to answer the
      # open question: does profile-switch + canary rollback work in a container (no bootloader)?
      # sshUser=root here (the agent key is baked to root in lxc-base, not a separate svc-ops), so a
      # config that kills SSH must self-heal within confirmTimeout instead of stranding the CT.
      deploy.nodes.lxc-proof = {
        hostname = "10.10.90.99";
        profiles.system = {
          user = "root";
          sshUser = "root";
          path = deploy-rs.lib.${system}.activate.nixos self.nixosConfigurations.lxc-proof;
          magicRollback = true;
          autoRollback = true;
        };
      };

      # SKY-021 P3 — adguard-core (CT 731 @ 10.10.70.31) day-2 over deploy-rs. sshUser=root (the agent
      # key is baked to root in lxc-base).
      deploy.nodes.lxc-adguard-core = {
        hostname = "10.10.70.31";
        profiles.system = {
          user = "root";
          sshUser = "root";
          path = deploy-rs.lib.${system}.activate.nixos self.nixosConfigurations.lxc-adguard-core;
          magicRollback = true;
          autoRollback = true;
        };
      };

      # lxc-athena BREAK-GLASS only — builds the athena repo's own config (the `athena` input), not a
      # skynet-owned one. Use if an in-place `rebuild` on the box severs SSH; magic-rollback protects
      # it. Everyday day-2 is `nixos-rebuild switch --flake ~/athena#lxc-athena` on the box itself.
      deploy.nodes.lxc-athena = {
        hostname = "10.10.100.30";
        profiles.system = {
          user = "root";
          sshUser = "root";
          path = deploy-rs.lib.${system}.activate.nixos inputs.athena.nixosConfigurations.lxc-athena;
          magicRollback = true;
          autoRollback = true;
        };
      };

      # `nix flake check` runs deploy-rs's own schema checks over the node definitions.
      checks.${system} = deploy-rs.lib.${system}.deployChecks self.deploy;
    };
}
