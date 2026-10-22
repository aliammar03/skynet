# Every host: Nix, users, SSH, secrets, and comin (pulls `main` and switches).
{
  config,
  lib,
  pkgs,
  inputs,
  ...
}:
let
  aliammarKey = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIMY3q277EOHizg5Ji/WUU7WvUi4X/ezbRPebk65lQVBJ aliammar@RK-W";
  hostSecrets = ../secrets + "/${config.networking.hostName}.yaml";
  # Key names in a sops file are plaintext, so evaluation can tell which secrets a host has.
  hasSecret =
    key:
    builtins.pathExists hostSecrets && lib.hasInfix "\n${key}:" ("\n" + builtins.readFile hostSecrets);
  # Posts a failed comin deploy (host, status, commit, error) to Discord #alerts. Successes stay quiet:
  # they'd be one post per host for every merge.
  cominNotify = pkgs.writeShellScript "comin-notify" ''
    [ "$COMIN_STATUS" = done ] && exit 0
    msg="**$COMIN_HOSTNAME** deploy $COMIN_STATUS: \`''${COMIN_GIT_SHA:0:7}\` $(printf '%s' "$COMIN_GIT_MSG" | head -n1)"
    [ -n "''${COMIN_ERROR_MSG:-}" ] && msg="$msg
    $COMIN_ERROR_MSG"
    ${pkgs.jq}/bin/jq -n --arg c "$msg" '{content: $c[0:1900]}' |
      ${pkgs.curl}/bin/curl -fsS -m 10 -H 'Content-Type: application/json' -d @- \
        "$(cat ${config.sops.secrets.discord_alerts_webhook.path or "/dev/null"})"
  '';
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
      "aliammar"
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
  users.users.aliammar = {
    isNormalUser = true;
    extraGroups = [ "wheel" ];
    openssh.authorizedKeys.keys = [ aliammarKey ];
  };
  security.sudo.wheelNeedsPassword = false;
  # The agent's diagnose lane on the other hosts: from ops only, no shell features (`restrict`), reads
  # the journal (container logs included, via the journald log driver). No sudo, no Docker socket.
  users.users.skynet = lib.mkIf (config.networking.hostName != "ops") {
    isNormalUser = true;
    extraGroups = [ "systemd-journal" ];
    openssh.authorizedKeys.keys = [
      ''from="10.10.90.91",restrict ${lib.fileContents ../hosts/ops/agent.pub}''
    ];
  };

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
    secrets.discord_alerts_webhook = lib.mkIf (hasSecret "discord_alerts_webhook") { };
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
    postDeploymentCommand = lib.mkIf (hasSecret "discord_alerts_webhook") cominNotify;
  };

  # CI catches a secret the config uses but the host's sops file lacks; on the host that would fail
  # the switch.
  assertions = lib.mapAttrsToList (name: s: {
    assertion = s.sopsFile != hostSecrets || hasSecret s.key;
    message = "secrets/${config.networking.hostName}.yaml has no key `${s.key}`: add it with sops before merging.";
  }) config.sops.secrets;

  system.stateVersion = "26.05";
}
