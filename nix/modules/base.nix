{ pkgs, ... }:
# Host baseline: the ops toolchain Nix owns, the docker daemon, and lab-wide defaults.
{
  nix.settings.experimental-features = [ "nix-command" "flakes" ];
  # deploy-rs pushes locally-built (unsigned) store paths as svc-ops; the target must trust it.
  nix.settings.trusted-users = [ "root" "svc-ops" ];

  time.timeZone = "Asia/Karachi"; # PKT — the operator's timezone

  # zsh as a system shell (adds it to /etc/shells + system-wide completion) so aliammar's login
  # shell can be zsh; the per-user config lives in nix/home/shell.nix.
  programs.zsh.enable = true;

  # Serial console (ttyS0) so Proxmox's xterm.js console works — crisper than noVNC, with copy-paste
  # and resize. Keep tty0 first so the noVNC/VGA console still gets a getty too. One-time on the
  # Proxmox node: `qm set <vmid> -serial0 socket`.
  boot.kernelParams = [ "console=tty0" "console=ttyS0,115200" ];

  nixpkgs.config.allowUnfree = true; # claude-code / antigravity are unfree (see nix/home/aliammar.nix)

  # Nix owns the ops toolchain. The agent CLIs are now Nix packages too, owned by home-manager
  # (nix/home/aliammar.nix, from nixpkgs-unstable) — no longer npm-global.
  environment.systemPackages = with pkgs; [
    git
    gh
    sops
    age
    rclone
    restic
    jq
    curl
    rsync
    docker-compose
    htop
    nodejs_22 # runtime for the node-based ops scripts (bin/ops)
    python3 # collect-firewall.sh parses the OPNsense config.xml
    openssl # pin-cert.sh + TLS pinning
    netcat # reachability probes in a few scripts
  ];

  # Arcane (on docker-dmz) owns the services; NixOS owns the daemon. The ops VM runs the
  # docker CLI/daemon to reach remote contexts. docker-group ≈ root — see ops-user.nix.
  virtualisation.docker.enable = true;

  # IPv6 is disabled lab-wide (OPNsense has no v6). Turn it off in the kernel too so the box
  # never advertises/attempts v6 — also avoids IPv6-first DNS stalls with no v6 route.
  networking.enableIPv6 = false;

  networking.firewall.enable = true;
  networking.firewall.allowedTCPPorts = [ 22 ];

  # Upgrades are a reviewed flake diff pushed via deploy-rs, never unattended.
  system.autoUpgrade.enable = false;
}
