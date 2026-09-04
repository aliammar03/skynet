{ pkgs, inputs, ... }:
# aliammar's home on lxc-athena — the DEV SANDBOX twin of nix/home/aliammar.nix. Same agent-CLI
# stack (claude-code / codex / opencode + mcp-nixos) so "the agents are set up like the ops VM",
# but WITHOUT the ops-VM couplings: no docker-dmz remote context, no OPS_ENGINE nightly selector,
# and the git identity is Ali's own (this box authors nothing on Skynet's behalf — it has no lab
# authority). Provider auth for claude/codex is a one-time interactive OAuth login by Ali; the gh
# token is seeded from sops (see hosts/lxc-athena/default.nix) and exported as GH_TOKEN below.
let
  # Fast-moving agent CLIs ride nixpkgs-unstable (bump that input to update them); the CT stays on
  # stable 26.05. allowUnfree: claude-code / antigravity are unfree.
  unstable = import inputs.nixpkgs-unstable {
    inherit (pkgs) system;
    config.allowUnfree = true;
  };
in
{
  home.username = "aliammar";
  home.homeDirectory = "/home/aliammar";
  home.stateVersion = "26.05";

  # A usable interactive shell for the dev box (the ops VM's shell.nix carries the ops landing board;
  # a sandbox doesn't need it). GH_TOKEN is sourced from the sops-decrypted secret when present, so
  # both `gh` and the `gh auth git-credential` helper below authenticate with no hosts.yml dance.
  programs.zsh = {
    enable = true;
    initContent = ''
      [ -r /run/secrets/gh-token ] && export GH_TOKEN="$(cat /run/secrets/gh-token)"
    '';
  };
  programs.starship.enable = true;

  # Ali's own git identity (not the Skynet-OPS bot). Auth to GitHub via the seeded gh token, same
  # credential helper as the ops VM.
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

  # The remaining CLIs + the mcp-nixos binary (same set as the ops VM).
  home.packages = [
    pkgs.mcp-nixos
    unstable.pi-coding-agent
    unstable.aider-chat
    unstable.antigravity-ide
  ];
}
