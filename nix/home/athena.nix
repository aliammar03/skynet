{ pkgs, inputs, ... }:
# aliammar's home on lxc-athena — the OBSIDIAN VAULT LIBRARIAN. Same agent-CLI stack as the ops VM
# (claude-code / codex / opencode + mcp-nixos) and the SAME interactive shell (nix/home/shell.nix),
# but landing in the vault working dir ~/athena with a minimal nix-focused board — not the ops repo.
# No ops-VM couplings (no docker-dmz context, no OPS_ENGINE selector) and no lab authority: this box
# curates the vault, it doesn't operate Skynet. The git identity is Ali's own; auth is interactive —
# `gh auth login` for GitHub (the credential helper reads gh's stored auth) and a one-time OAuth
# login for claude/codex. No seeded tokens on the box.
let
  # Fast-moving agent CLIs ride nixpkgs-unstable (bump that input to update them); the CT stays on
  # stable 26.05. allowUnfree: claude-code / antigravity are unfree.
  unstable = import inputs.nixpkgs-unstable {
    inherit (pkgs) system;
    config.allowUnfree = true;
  };
in
{
  # The ops VM's shell verbatim (zsh + starship + tooling), but a login lands in the vault dir with
  # a minimal nix-focused board instead of the ops repo + ops board.
  imports = [ (import ./shell.nix { landingDir = "$HOME/athena"; motdSource = ./athena-motd.sh; }) ];

  home.username = "aliammar";
  home.homeDirectory = "/home/aliammar";
  home.stateVersion = "26.05";

  # Ali's own git identity (not the Skynet-OPS bot). GitHub auth is interactive (`gh auth login`);
  # the credential helper reads gh's stored auth — same helper as the ops VM. No GH_TOKEN env var
  # (it would block `gh auth login`).
  programs.git = {
    enable = true;
    settings.user = {
      name = "aliammar";
      email = "aliammar03@gmail.com";
    };
    settings.credential."https://github.com".helper = "!${pkgs.gh}/bin/gh auth git-credential";
  };
  programs.delta = { enable = true; enableGitIntegration = true; };

  # mcp-nixos: the package-search MCP server, folded into each agent CLI below via
  # enableMcpIntegration (identical to the ops VM).
  programs.mcp = {
    enable = true;
    servers.mcp-nixos.command = "${pkgs.mcp-nixos}/bin/mcp-nixos";
  };

  # --- Agent CLIs — copied from nix/home/aliammar.nix so athena behaves like the ops VM. ----------
  # The OS user account is the wall; these permission lists are prompt ERGONOMICS, not the security
  # boundary. This box has no tokens/secrets/T2/T3 authority, so the only real checkpoints kept are
  # the human-merge gate (`gh pr merge`) — grant-root has no meaning here (no CA trust) but is left
  # in for parity.
  programs.claude-code = {
    enable = true;
    package = unstable.claude-code;
    enableMcpIntegration = true;
    settings.permissions = {
      defaultMode = "acceptEdits";
      allow = [ "Bash" "WebFetch" ];
      ask = [
        "Bash(gh pr merge:*)"
      ];
      deny = [
        "Read(**/age.key)"
      ];
    };
  };
  programs.codex = {
    enable = true;
    package = unstable.codex;
    enableMcpIntegration = true;
    settings = {
      model = "gpt-5.6-sol";
      model_reasoning_effort = "medium";
      approval_policy = "on-request";
      sandbox_mode = "danger-full-access";
      projects."/home/aliammar".trust_level = "trusted";
    };
    rules.skynet = ''
      prefix_rule(
        pattern = ["gh", "pr", "merge"],
        decision = "prompt",
        justification = "Authored pull requests require an explicit human merge decision",
      )
    '';
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
        "gh pr merge*" = "ask";
      };
    };
  };

  # The remaining CLIs + the mcp-nixos binary (same set as the ops VM). gh is the interactive
  # GitHub CLI (the git credential helper uses its absolute store path regardless, but Ali wants
  # `gh` on PATH like the ops VM has).
  home.packages = [
    pkgs.gh
    pkgs.mcp-nixos
    unstable.pi-coding-agent
    unstable.aider-chat
    unstable.antigravity-ide
  ];
}
