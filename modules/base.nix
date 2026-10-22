# Every host: Nix, users, SSH, secrets, and comin (pulls `main` and switches).
{
  config,
  lib,
  pkgs,
  inputs,
  ...
}:
let
  aliKey = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIMY3q277EOHizg5Ji/WUU7WvUi4X/ezbRPebk65lQVBJ aliammar@RK-W";
  hostSecrets = ../secrets + "/${config.networking.hostName}.yaml";
in
{
  imports = [
    inputs.disko.nixosModules.disko
    inputs.sops-nix.nixosModules.sops
    inputs.comin.nixosModules.comin
    ./nix-cache.nix
  ];

  nix.settings = {
    experimental-features = [
      "nix-command"
      "flakes"
    ];
    trusted-users = [
      "root"
      "ali"
    ];
    auto-optimise-store = true;
  };
  nix.gc = {
    automatic = true;
    dates = "weekly";
    options = "--delete-older-than 14d";
  };
  nixpkgs.config.allowUnfree = true;

  boot.loader.systemd-boot.enable = true;
  boot.loader.efi.canTouchEfiVariables = true;
  # tty0 for noVNC, ttyS0 for the Proxmox xterm.js console (VM needs `--serial0 socket`).
  boot.kernelParams = [
    "console=tty0"
    "console=ttyS0,115200"
  ];

  time.timeZone = "Asia/Karachi";
  i18n.defaultLocale = "en_US.UTF-8";

  networking.useNetworkd = true;
  networking.enableIPv6 = false; # the lab has no IPv6
  networking.firewall.enable = true;
  networking.firewall.allowedTCPPorts = [ 22 ];

  services.openssh = {
    enable = true;
    settings = {
      PasswordAuthentication = false;
      KbdInteractiveAuthentication = false;
      PermitRootLogin = "no";
    };
  };

  users.mutableUsers = false;
  users.users.ali = {
    isNormalUser = true;
    extraGroups = [ "wheel" ];
    openssh.authorizedKeys.keys = [ aliKey ];
  };
  security.sudo.wheelNeedsPassword = false;

  services.qemuGuest.enable = true;
  services.journald.extraConfig = "MaxRetentionSec=2week";

  environment.systemPackages = with pkgs; [
    git
    curl
    jq
    htop
    dnsutils
    tmux
  ];

  # Host secrets exist only after the host's age key is added to .sops.yaml (see skynetv2.md P0).
  sops = lib.mkIf (builtins.pathExists hostSecrets) {
    defaultSopsFile = hostSecrets;
    age.sshKeyPaths = [ "/etc/ssh/ssh_host_ed25519_key" ];
  };

  services.comin = {
    enable = true;
    remotes = [
      {
        name = "origin";
        url = "https://github.com/aliammar03/skynet.git";
        branches.main.name = "main";
        poller.period = 60;
      }
    ];
  };

  system.stateVersion = "26.05";
}
