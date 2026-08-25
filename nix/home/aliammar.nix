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
  programs.claude-code = { enable = true; package = unstable.claude-code; enableMcpIntegration = true; };
  programs.codex = { enable = true; package = unstable.codex; enableMcpIntegration = true; };
  programs.opencode = { enable = true; package = unstable.opencode; enableMcpIntegration = true; };

  # The remaining CLIs (no home-manager module / no MCP config to manage) + the mcp-nixos binary.
  home.packages = [
    pkgs.mcp-nixos
    unstable.pi-coding-agent
    unstable.aider-chat
    unstable.antigravity-ide
  ];
}
