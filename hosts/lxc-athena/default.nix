{ config, lib, pkgs, ... }:
# lxc-athena (CT 10030 @ 10.10.100.30, VLAN 100 / DMZ) — the OBSIDIAN VAULT LIBRARIAN: a coding-agent
# box (Claude Code / Codex / opencode, set up like the ops VM — nix/home/athena.nix) that curates
# Ali's Obsidian vault under ~/athena. Built on the lean pool-CT spine (lxc-base: nix/flakes, the
# agent SSH key for deploy-rs day-2, sshd key-only). By contract it has NO lab authority: no svc-ops
# operate tokens, no grant-root CA trust, no Proxmox/DNS/firewall reach — it tends the vault, it
# doesn't operate Skynet. Provision + rollback: runbooks/provision-lxc.md.
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

  # The librarian operator. Declarative-only (mutableUsers=false) to match the flake-is-truth model.
  # No lab creds live on this box, so wheel is passwordless — the convenience is bought with the box
  # holding nothing worth stealing (no tokens, no CA trust). Ali logs in with his workstation key;
  # the console autologs in as aliammar (overriding lxc-base's root autologin).
  users.mutableUsers = false;
  users.users.aliammar = {
    isNormalUser = true;
    description = "Ali — Obsidian vault librarian";
    shell = pkgs.zsh;
    extraGroups = [ "wheel" ];
    openssh.authorizedKeys.keys = [
      "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIMY3q277EOHizg5Ji/WUU7WvUi4X/ezbRPebk65lQVBJ aliammar@RK-W"
    ];
  };
  security.sudo.wheelNeedsPassword = false; # no password on the box, so no password gate

  # The vault working dir a login lands in (nix/home/shell.nix cd's here). Created empty; the vault
  # itself is synced/curated at runtime.
  systemd.tmpfiles.rules = [ "d /home/aliammar/athena 0755 aliammar users -" ];

  services.getty.autologinUser = lib.mkForce "aliammar";

  # No secrets on this box: git/gh auth is done by Ali interactively (`gh auth login`), not seeded.
  # If the vault ever needs a secret, mint an Option C age identity then (runbooks/provision-lxc.md)
  # and re-add sops-nix here + to flake.nix.

  system.stateVersion = "26.05";
}
