# The agent: user `skynet` (no sudo) running Claude Code, reachable via Discord and the Claude app.
{
  config,
  lib,
  pkgs,
  inputs,
  ...
}:
let
  unstable = import inputs.nixpkgs-unstable {
    inherit (pkgs.stdenv.hostPlatform) system;
    config.allowUnfree = true;
  };
  home = "/home/skynet";
  repo = "${home}/skynet";
  hasSecrets = builtins.pathExists (../secrets + "/${config.networking.hostName}.yaml");
  # The Proxmox nodes are standalone (no cluster), so each has its own `skynet@pve!read` token.
  pveHeader = node: {
    owner = "skynet";
    content = ''
      Authorization: PVEAPIToken=skynet@pve!read=${config.sops.placeholder."pve_${node}_read_token"}
    '';
  };
  # A Claude session in its own tmux server (one server per unit, so restarting one session never
  # kills another). As skynet: `tmux -L <name> attach` to see or drive it.
  session = name: cmd: {
    description = "Skynet agent session: ${name}";
    wantedBy = [ "multi-user.target" ];
    wants = [ "network-online.target" ];
    after = [
      "network-online.target"
      "skynet-clone.service"
      "skynet-discord-token.service"
    ];
    # The same PATH as a login shell: every package installed on the host is visible to the agent.
    environment.PATH = lib.mkForce "/run/wrappers/bin:/run/current-system/sw/bin";
    serviceConfig = {
      User = "skynet";
      WorkingDirectory = repo;
      Type = "forking";
      Restart = "always";
      RestartSec = 10;
      EnvironmentFile = "-${config.sops.templates."agent.env".path or "/dev/null"}";
      # Start on current main, so the session reads today's plan, AGENTS.md and .mcp.json (work
      # happens in worktrees). `-`: a dirty checkout or no network still starts the session.
      # Both sessions start together, so a lock keeps their git runs from colliding.
      ExecStartPre = "-${pkgs.writeShellScript "skynet-fresh-main" ''
        cd ${repo} || exit 1
        exec 9>.git/skynet-fresh-main.lock && ${pkgs.util-linux}/bin/flock 9 || exit 1
        ${pkgs.git}/bin/git fetch -q origin &&
          ${pkgs.git}/bin/git switch -q main && ${pkgs.git}/bin/git merge -q --ff-only origin/main
      ''}";
      ExecStart = "${pkgs.tmux}/bin/tmux -L ${name} new-session -d -s ${name} '${cmd}'";
      ExecStop = "${pkgs.tmux}/bin/tmux -L ${name} kill-server";
    };
  };
in
{
  users.users.skynet = {
    isNormalUser = true;
    inherit home;
    createHome = true;
  };
  # Host keys of the hosts the agent SSHes into (diagnose lane, base.nix), each checked against its
  # sops age recipient (`ssh-to-age`) when added.
  programs.ssh.knownHosts.docker-admin = {
    hostNames = [ "10.10.50.40" ];
    publicKeyFile = ../hosts/docker-admin/ssh_host.pub;
  };
  # Build IP and final IP (P2 cutover), so the cutover needs no change here.
  programs.ssh.knownHosts.technitium-network = {
    hostNames = [
      "10.10.70.52"
      "10.10.70.50"
    ];
    publicKeyFile = ../hosts/technitium-network/ssh_host.pub;
  };
  programs.ssh.knownHosts.technitium-core = {
    hostNames = [
      "10.10.70.53"
      "10.10.70.51"
    ];
    publicKeyFile = ../hosts/technitium-core/ssh_host.pub;
  };

  environment.systemPackages = with pkgs; [
    (writeShellScriptBin "skynet-attach" ''
      exec sudo -iu skynet tmux -L "''${1:-skynet}" attach
    '')
    # A fresh terminal Claude session as the agent, in its own git worktree (`claude --worktree`).
    # The session is a script file: `sudo -i` hands its command to a login shell with `$` unescaped,
    # so variables written inline would expand there, empty.
    (writeShellScriptBin "skynet-claude" ''
      exec sudo -iu skynet ${writeShellScript "skynet-claude-session" ''
        f=/run/secrets/rendered/agent.env
        [ -r "$f" ] && { set -a; . "$f"; set +a; }
        cd ~/skynet && git fetch -q origin
        exec claude --worktree --permission-mode auto "$@"
      ''} "$@"
    '')
    unstable.claude-code
    unstable.mcp-nixos
    bun
    nodejs
    gh
    sops
    age
    ssh-to-age
    yq-go
    ripgrep
    fd
    python3
  ];

  sops = lib.mkIf hasSecrets {
    secrets.discord_bot_token = {
      owner = "skynet";
      restartUnits = [
        "skynet-discord-token.service"
        "skynet-agent.service"
      ];
    };
    secrets.github_token.owner = "skynet";
    templates."agent.env" = {
      owner = "skynet";
      content = ''
        GH_TOKEN=${config.sops.placeholder.github_token}
      '';
    };

    # Read-only lab APIs (diagnose lane). Rendered as files curl reads itself, so a value never
    # lands in an environment, a command line or the transcript. Usage: hosts/ops/README.md.
    secrets.pve_core_read_token = { };
    secrets.pve_network_read_token = { };
    secrets.opnsense_read_key = { };
    secrets.opnsense_read_secret = { };
    templates."pve-core.header" = pveHeader "core";
    templates."pve-network.header" = pveHeader "network";
    templates."opnsense.netrc" = {
      owner = "skynet";
      content = ''
        machine 10.10.50.1 login ${config.sops.placeholder.opnsense_read_key} password ${config.sops.placeholder.opnsense_read_secret}
      '';
    };
    # docker-admin's doco-cd API key; Claude Code's `headersHelper` (.mcp.json) prints this file.
    secrets.doco_admin_api_key = { };
    templates."doco-admin.headers.json" = {
      owner = "skynet";
      content = builtins.toJSON { x-api-key = config.sops.placeholder.doco_admin_api_key; };
    };
  };

  # The Discord channel plugin reads its token from ~/.claude/channels/discord/.env; Claude doesn't
  # pass the session's environment to plugin servers. A real file, not a symlink: the plugin refuses
  # to send files under that folder, and a symlink pointing outside it would slip past that check.
  systemd.services.skynet-discord-token = lib.mkIf hasSecrets {
    description = "Give the Discord channel plugin its bot token";
    wantedBy = [ "multi-user.target" ];
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
      User = "skynet";
      UMask = "0077";
    };
    script = ''
      dir=${home}/.claude/channels/discord
      mkdir -p "$dir" && chmod 700 "$dir"
      printf 'DISCORD_BOT_TOKEN=%s\n' "$(cat ${
        config.sops.secrets.discord_bot_token.path or "/dev/null"
      })" > "$dir/.env.new"
      mv "$dir/.env.new" "$dir/.env"
    '';
  };

  # `skynet-attach [spawn]` joins a running session (detach: F12); `skynet-claude` starts a new one.
  programs.tmux = {
    enable = true;
    extraConfig = ''
      bind -n F12 detach-client
      set -g mouse on
      set -g status-right "F12 detach "
    '';
  };

  # The agent's SSH key, for nixos-anywhere into installer ISOs (hosts/ops/agent.pub; the installed
  # systems don't trust it). Generated once; a rebuilt ops gets a new key → update agent.pub.
  systemd.services.skynet-ssh-key = {
    description = "Generate the agent's SSH key";
    wantedBy = [ "multi-user.target" ];
    path = [ pkgs.openssh ];
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
      User = "skynet";
    };
    script = ''
      mkdir -p -m 700 ${home}/.ssh
      [ -e ${home}/.ssh/id_ed25519 ] || ssh-keygen -q -t ed25519 -N "" -C skynet@ops -f ${home}/.ssh/id_ed25519
    '';
  };

  # First boot: clone the repo and set the agent's git identity (pushes go to branches; main is ruleset-guarded).
  systemd.services.skynet-clone = {
    description = "Clone the Skynet repo for the agent";
    wantedBy = [ "multi-user.target" ];
    wants = [ "network-online.target" ];
    after = [ "network-online.target" ];
    path = [ pkgs.git ];
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
      User = "skynet";
    };
    script = ''
      if [ ! -d ${repo}/.git ]; then
        git clone https://github.com/aliammar03/skynet.git ${repo}
      fi
      git config --global user.name aliammar-skynet
      git config --global user.email 316666232+aliammar-skynet@users.noreply.github.com
      git config --global credential.helper '!gh auth git-credential'
    '';
  };

  # Persistent conversation (Discord + Claude app) and on-demand app sessions in their own worktrees.
  systemd.services.skynet-agent = session "skynet" "claude --remote-control Skynet --channels plugin:discord@claude-plugins-official --permission-mode auto";
  systemd.services.skynet-spawn = session "spawn" "claude remote-control --spawn worktree --permission-mode auto";
}
