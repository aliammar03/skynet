{ pkgs, inputs, ... }:
# The ops operator's home, declaratively. Git identity, the ops-engine selector, and the agent
# CLIs with their shared mcp-nixos registration. home-manager owns the CLIs end-to-end now (the
# "flake proper, not the bootstrap" decision) — package *and* config — so the MCP-consuming ones
# must be installed here, not system-wide (home-manager refuses to manage a CLI's MCP config
# unless it also owns that CLI's package).
let
  # Fast-moving agent CLIs ride nixpkgs-unstable (bump that input to update them); the host stays
  # on stable 26.05. allowUnfree: claude-code / antigravity are unfree.
  unstable = import inputs.nixpkgs-unstable {
    inherit (pkgs) system;
    config.allowUnfree = true;
  };
in
{
  imports = [
    ./shell.nix # zsh + starship + tooling + the login landing board
    ./docker.nix # the docker-dmz remote context for collect-docker.sh
  ];

  home.username = "aliammar";
  home.homeDirectory = "/home/aliammar";
  # Matches system.stateVersion; never advance blind (triggers stateful migrations).
  home.stateVersion = "26.05";

  # Git identity for the agent's commits (Skynet-OPS authors PRs; see AGENTS.md).
  programs.git = {
    enable = true;
    settings.user = {
      name = "Skynet-OPS";
      email = "aliammar.skynet@gmail.com";
    };
    # Auth to the private GitHub remote via the gh token (seeded at ~/.config/gh) — declaratively,
    # so `git fetch/pull/push` and the nightly work without a per-repo helper set up by hand.
    settings.credential."https://github.com".helper = "!${pkgs.gh}/bin/gh auth git-credential";
  };
  # delta: syntax-highlighted, side-by-side-capable git diffs.
  programs.delta = { enable = true; enableGitIntegration = true; };

  # Engine selector read by the nightly timer's EnvironmentFile (nix/modules/timers.nix) and bin/ops.
  home.file.".config/skynet-ops/ops.env".text = "OPS_ENGINE=codex\n";

  # mcp-nixos: the package-search MCP server (this very tool), from stable 26.05 (2.4.3) — no
  # docker wrapper needed on the box. Declared once in the shared programs.mcp.servers; each CLI's
  # enableMcpIntegration below merges it into that CLI's own config.
  programs.mcp = {
    enable = true;
    servers.mcp-nixos.command = "${pkgs.mcp-nixos}/bin/mcp-nixos";
  };

  # CLIs home-manager has a module for: it owns package (unstable) + config, and folds mcp-nixos
  # in via enableMcpIntegration.
  #
  # DEFAULT PERMISSIONS — the box's OS user model is the security wall (aliammar has no general root:
  # locked password + sudo scoped to `systemctl skynet-*`, can't read the root-owned age.key/secrets).
  # So these lists are prompt ERGONOMICS, not the security boundary: allow local read/write/run/edit
  # freely (incl. writing and running scripts) so the agent isn't nagged every few seconds, and pause
  # only on the few things the OS won't stop that cross a real boundary — push to the remote, open/merge
  # a PR (the human-merge gate), request root — plus never dump decrypted secrets to stdout.
  programs.claude-code = {
    enable = true;
    package = unstable.claude-code;
    enableMcpIntegration = true;
    settings.permissions = {
      # acceptEdits: Write/Edit land without a prompt (matches the ops loop's --permission-mode flag).
      defaultMode = "acceptEdits";
      allow = [ "Bash" "WebFetch" ]; # all Bash + web reads; ask/deny carve out exceptions (deny > ask > allow).
      ask = [
        # `git push` alone stays gated: blanket-allow would let a direct push to main bypass the
        # propose-via-PR gate. Opening/merging goes through gh below; a branch push asks once.
        "Bash(git push:*)"
        "Bash(gh pr merge:*)"
        "Bash(bin/grant-root:*)"
        "Bash(./bin/grant-root:*)"
      ];
      deny = [
        "Read(/run/secrets/**)"
        "Read(/opt/skynet-ops/secrets/**)"
        "Read(/nix/persist/opt/skynet-ops/secrets/**)"
        "Read(**/age.key)"
      ];
    };
  };
  programs.codex = {
    enable = true;
    package = unstable.codex;
    enableMcpIntegration = true;
    # on-failure: run sandboxed silently, only surface when a command needs to escalate. workspace-write
    # + network_access: the collectors hit the Proxmox/DNS/Docker APIs, so the sandbox must reach the net.
    # trust_level: skip the per-project trust prompt for the box's repo.
    settings = {
      approval_policy = "on-failure";
      sandbox_mode = "workspace-write";
      sandbox_workspace_write.network_access = true;
      projects."/home/aliammar/skynet".trust_level = "trusted";
    };
  };
  programs.opencode = {
    enable = true;
    package = unstable.opencode;
    enableMcpIntegration = true;
    settings.permission = {
      edit = "allow";
      webfetch = "allow";
      bash = {
        "*" = "allow";
        "git push*" = "ask";
        "gh pr merge*" = "ask";
      };
    };
  };

  # The remaining CLIs (no home-manager module / no MCP config to manage) + the mcp-nixos binary.
  home.packages = [
    pkgs.mcp-nixos
    unstable.pi-coding-agent
    unstable.aider-chat
    unstable.antigravity-ide
  ];
}
