{ config, lib, pkgs, ... }:
# lxc-athena (CT 10030 @ 10.10.100.30, VLAN 100 / DMZ) — a coding-agent DEV SANDBOX. Claude Code,
# Codex and opencode set up like the ops VM (nix/home/athena.nix), on the lean pool-CT spine
# (lxc-base: nix/flakes, the agent SSH key for deploy-rs day-2, sshd key-only). By contract this box
# has NO lab authority: no svc-ops operate tokens, no grant-root CA trust, no Proxmox/DNS/firewall
# reach — it builds code, it doesn't operate Skynet. Provision + rollback: runbooks/provision-lxc.md.
{
  imports = [ ../../nix/modules/lxc-base.nix ];

  networking.hostName = "lxc-athena";
  # Unprivileged CT on VLAN 100, which OPNsense already governs — the host-local nftables firewall
  # needs caps an unprivileged CT lacks (same reason as adguard-core). No host firewall here.
  networking.firewall.enable = false;
  networking.nameservers = [ "10.10.70.51" ]; # tdns-core, the real resolver

  nixpkgs.config.allowUnfree = true; # claude-code / antigravity are unfree

  # zsh as a system shell so aliammar's login shell can be zsh (per-user config in nix/home/athena.nix).
  programs.zsh.enable = true;

  # The dev operator. Declarative-only (mutableUsers=false) to match the flake-is-truth model. This
  # is a sandbox with no lab creds on the box, so wheel is passwordless — the convenience is bought
  # with the box holding nothing worth stealing (no tokens, no CA trust). Ali logs in with his
  # workstation key; the console autologs in as aliammar (overriding lxc-base's root autologin).
  users.mutableUsers = false;
  users.users.aliammar = {
    isNormalUser = true;
    description = "Ali — dev sandbox";
    shell = pkgs.zsh;
    extraGroups = [ "wheel" ];
    openssh.authorizedKeys.keys = [
      "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIMY3q277EOHizg5Ji/WUU7WvUi4X/ezbRPebk65lQVBJ aliammar@RK-W"
    ];
  };
  security.sudo.wheelNeedsPassword = false; # sandbox: no password on the box, so no password gate
  services.getty.autologinUser = lib.mkForce "aliammar";

  # Option C: this CT's age identity, injected to keyFile at provision (before the first deploy).
  sops.age.keyFile = "/var/lib/sops-nix/age.key";

  # Seeded gh token (dual-recipient sops). Decrypts to /run/secrets/gh-token (owner aliammar); the
  # login shell exports it as GH_TOKEN (nix/home/athena.nix) so `gh` and the git credential helper
  # authenticate unattended. claude/codex provider auth is still a one-time interactive OAuth login.
  sops.secrets."gh-token" = {
    sopsFile = ../../secrets/lxc-athena/gh-token.sops;
    format = "binary";
    owner = "aliammar";
    mode = "0400";
  };

  system.stateVersion = "26.05";
}
