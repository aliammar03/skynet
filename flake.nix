{
  description = "Skynet host definitions — declarative NixOS";

  # Rationale, layout, and the twin/cutover model live in nix/README.md + docs/system-design.md.
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";
    # Fast-moving agent CLIs (claude-code/codex/antigravity) come from unstable, not npm — see
    # nix/modules/agent-clis.nix. Kept as a separate input so the host stays on stable 26.05.
    nixpkgs-unstable.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    # Codex rides slightly ahead of the unstable *channel*: nixpkgs master carries a newer codex
    # (0.153.4) days before the channel promotes it. Pinned to the exact master rev that bumped it
    # and sourced ONLY for programs.codex.package (nix/home/aliammar.nix) — the rest of the toolchain
    # stays on the channel. Bump with `nix flake lock --update-input nixpkgs-codex` to a newer master
    # rev; delete this input and revert codex to `unstable.codex` once the channel catches up.
    nixpkgs-codex.url = "github:NixOS/nixpkgs/b300481863bac7c2d2ccad622900c2d903f03bc8";
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
      pkgs = import nixpkgs { inherit system; };
      skynet = pkgs.callPackage ./nix/packages/skynet.nix { };
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

      # NixOS LXC build target. The tarball output below is the CT template.
      nixosConfigurations.lxc-base = nixpkgs.lib.nixosSystem {
        inherit system;
        specialArgs = { inherit inputs; };
        modules = [ ./hosts/lxc-base ];
      };

      # `nix build .#lxc-base-tarball` produces the Proxmox CT template tarball.
      # (local:vztmpl/). The proxmox-lxc module exposes it as system.build.tarball.
      packages.${system} = {
        lxc-base-tarball = self.nixosConfigurations.lxc-base.config.system.build.tarball;
        inherit skynet;
      };

      apps.${system}.skynet = {
        type = "app";
        program = "${skynet}/bin/skynet";
      };

      devShells.${system}.default = pkgs.mkShell {
        packages = [
          skynet
          pkgs.python3
          pkgs.python3Packages.pytest
          pkgs.ruff
          pkgs.mypy
        ];
      };

      # adguard-core (CT 731) is a NixOS LXC. Its AdGuard config is rendered from a sops template;
      # deploy-rs supplies day-two rollback and the host has a per-CT age key.
      nixosConfigurations.lxc-adguard-core = nixpkgs.lib.nixosSystem {
        inherit system;
        specialArgs = { inherit inputs; };
        modules = [
          sops-nix.nixosModules.sops
          ./hosts/lxc-adguard-core
        ];
      };

      # lxc-athena's inside is owned by its own repo (aliammar03/athena, the `athena` input above).
      # Skynet keeps only the envelope: the tofu CT (tofu/pool-cts.tf) and HOST_ATHENA firewall mapping. The break-glass
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

      # adguard-core (CT 731 @ 10.10.70.31) day-two over deploy-rs. sshUser=root (the agent
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
      checks.${system} = (deploy-rs.lib.${system}.deployChecks self.deploy) // {
        skynet = pkgs.runCommand "skynet-checks" {
          nativeBuildInputs = [ skynet pkgs.python3Packages.pytest ];
        } ''
          outside="$(mktemp -d)"
          cd "$outside"
          unset PYTHONPATH
          export SSL_CERT_FILE=${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt
          skynet --help >/dev/null
          skynet --version >/dev/null
          skynet doctor >/dev/null
          skynet doctor --json >/dev/null
          if skynet collect >/dev/null 2>&1; then
            echo "incomplete collect command unexpectedly succeeded" >&2
            exit 1
          fi
          PYTHONPATH=${skynet}/${pkgs.python3.sitePackages} SKYNET_ENTRYPOINT=console \
            pytest -q ${skynet.source}/tests
          touch "$out"
        '';
      };
    };
}
