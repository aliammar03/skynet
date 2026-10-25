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
  # A Docker host's doco-cd API key (= its `doco_api_secret`); Claude Code's `headersHelper`
  # (.mcp.json) prints this file.
  docoHeaders = target: {
    owner = "skynet";
    content = builtins.toJSON { x-api-key = config.sops.placeholder."doco_${target}_api_key"; };
  };
  # One interactive session (`skynet-claude <name>`), run by tmux as skynet: its GitHub token, real
  # links through tmux, Remote Control on, in worktree <name>. A worktree that already holds a
  # conversation (after /exit or a reboot) continues it; a new name starts fresh.
  claudeSession = pkgs.writeShellScript "skynet-claude-session" ''
    name=$1
    f=/run/secrets/rendered/agent.env
    [ -r "$f" ] && { set -a; . "$f"; set +a; }
    export FORCE_HYPERLINK=1 # Claude Code prints OSC 8 links; tmux passes them on (terminal-features)
    flags="--name $name --remote-control $name --permission-mode auto"
    wt=${repo}/.claude/worktrees/$name
    if [ -d "$wt" ]; then
      cd "$wt" || exit 1
      # Claude keeps a directory's conversations in ~/.claude/projects/<its path, with / and . as ->.
      if ls ${home}/.claude/projects/"$(printf %s "$wt" | tr /. --)"/*.jsonl >/dev/null 2>&1; then
        exec claude --continue $flags
      fi
      exec claude $flags
    fi
    cd ${repo} && ${pkgs.git}/bin/git fetch -q origin
    exec claude --worktree "$name" $flags
  '';
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
  programs.ssh.knownHosts.technitium-network = {
    hostNames = [ "10.10.70.50" ];
    publicKeyFile = ../hosts/technitium-network/ssh_host.pub;
  };
  programs.ssh.knownHosts.technitium-core = {
    hostNames = [ "10.10.70.51" ];
    publicKeyFile = ../hosts/technitium-core/ssh_host.pub;
  };
  programs.ssh.knownHosts.docker-dmz = {
    hostNames = [ "10.10.100.10" ];
    publicKeyFile = ../hosts/docker-dmz/ssh_host.pub;
  };
  # PBS (VM 2040) isn't a NixOS host; its key from the install, checked through the guest agent.
  programs.ssh.knownHosts.pbs = {
    hostNames = [ "10.10.20.40" ];
    publicKeyFile = ../pbs/ssh_host.pub;
  };

  environment.systemPackages = with pkgs; [
    (writeShellScriptBin "skynet-attach" ''
      exec sudo -iu skynet tmux -L "''${1:-skynet}" attach
    '')
    # `skynet-claude <name>`: the agent's interactive session <name>. Attaches if it runs, else starts
    # it in tmux server `claude` (as skynet). The session is a script file: `sudo -i` hands its
    # command to a login shell with `$` unescaped, so variables written inline would expand there.
    (writeShellScriptBin "skynet-claude" ''
      name=''${1:-}
      case "$name" in
        "")
          echo "usage: skynet-claude <name>   attach to session <name>, or start it (a-z, 0-9, -)"
          exec sudo -iu skynet tmux -L claude ls
          ;;
        *[!a-z0-9-]*)
          echo "skynet-claude: a name is a-z, 0-9 and -" >&2
          exit 2
          ;;
      esac
      exec sudo -iu skynet tmux -L claude new-session -A -s "$name" ${claudeSession} "$name"
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
    secrets.doco_admin_api_key = { };
    secrets.doco_dmz_api_key = { };
    templates."doco-admin.headers.json" = docoHeaders "admin";
    templates."doco-dmz.headers.json" = docoHeaders "dmz";
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

  # `skynet-attach [spawn]` joins a service session, `skynet-claude <name>` an interactive one
  # (detach: F12). For every tmux on ops.
  programs.tmux = {
    enable = true;
    # 256 colours and italics inside tmux; the default ("screen") tells apps they have 8.
    terminal = "tmux-256color";
    historyLimit = 50000; # enough scrollback to find and copy a long session's output
    escapeTime = 10; # Esc reaches Claude at once (it interrupts with Esc); the default holds it 500 ms
    extraConfig = ''
      bind -n F12 detach-client
      set -g mouse on
      set -g status-right "F12 detach "
      # Windows Terminal takes OSC 52 (clipboard), OSC 8 (links) and 24-bit colour; tmux passes all
      # three on, over SSH too, and tells the apps inside about the colour.
      set -g set-clipboard on
      set -as terminal-features ',*:clipboard:hyperlinks:RGB'
      setenv -g COLORTERM truecolor
      # A quiet status bar with the session's name, and a selection that stands out.
      set -g status-style 'bg=colour236,fg=colour250'
      set -g status-left '#[fg=colour39,bold] #S #[default]'
      set -g status-left-length 32
      set -g window-status-current-style 'fg=colour255,bold'
      set -g message-style 'bg=colour39,fg=colour16'
      set -g mode-style 'bg=colour31,fg=colour255'
      set -g pane-border-style 'fg=colour238'
      set -g pane-active-border-style 'fg=colour39'
      # Drag highlights and leaves the selection; right-click copies it to the workstation's
      # clipboard, as in Windows Terminal itself. Right-click elsewhere goes to the app if it wants
      # the mouse; Alt+right-click keeps tmux's menu.
      bind -T copy-mode MouseDragEnd1Pane send -X stop-selection
      bind -T copy-mode-vi MouseDragEnd1Pane send -X stop-selection
      bind -n MouseDown3Pane if -F '#{pane_in_mode}' { send -X copy-selection-and-cancel } { if -F '#{mouse_any_flag}' { send -M } }
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
