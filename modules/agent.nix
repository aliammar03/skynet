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
  sessionPath = (
    with pkgs;
    [
      unstable.claude-code
      unstable.mcp-nixos
      bun # Claude Code channel plugins run on Bun
      nodejs
      git
      gh
      tmux
      coreutils
      bash
    ]
  );
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
    path = sessionPath;
    serviceConfig = {
      User = "skynet";
      WorkingDirectory = repo;
      Type = "forking";
      Restart = "always";
      RestartSec = 10;
      EnvironmentFile = "-${config.sops.templates."agent.env".path or "/dev/null"}";
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

  environment.systemPackages = with pkgs; [
    (writeShellScriptBin "skynet-attach" ''
      exec sudo -iu skynet tmux -L "''${1:-skynet}" attach
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

  # Attaching: `skynet-attach` (or `skynet-attach spawn`). Detach: F12, or Ctrl+B then D.
  programs.tmux = {
    enable = true;
    extraConfig = ''
      bind -n F12 detach-client
      set -g mouse on
      set -g status-right "F12 detach "
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
