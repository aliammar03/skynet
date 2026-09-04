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
        # The propose-via-PR gate is enforced server-side (GitHub branch protection on main) + the
        # no-self-merge contract, NOT a client-side push prompt — a prompt on every branch push just
        # trains a rubber-stamp. So a plain `git push` (branches) runs free; the real gate is `gh pr
        # merge` below, which still asks. Root grants still ask too.
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
    # Match Claude's acceptEdits + Bash allow posture: the aliammar OS account is the security wall,
    # so the interactive lead may read/write/run anything that account can. This also keeps Nix,
    # normal git work, branch pushes, and `gh pr create` prompt-free. The two real checkpoints live
    # in skynet.rules below. SKY-022 helpers remain bounded because bin/agent passes an explicit
    # per-role --sandbox, overriding this interactive-lead default.
    settings = {
      model = "gpt-5.6-sol";
      model_reasoning_effort = "medium";
      approval_policy = "on-request";
      sandbox_mode = "danger-full-access";
      projects."/home/aliammar/skynet".trust_level = "trusted";
    };
    # Use a named managed rule file instead of default.rules: Codex owns the latter when Ali accepts
    # a remembered command interactively, and Home Manager must not collide with that local file.
    # Rule precedence is restrictive, so these prompts override any remembered allow rule.
    rules.skynet = ''
      prefix_rule(
        pattern = ["gh", "pr", "merge"],
        decision = "prompt",
        justification = "Authored pull requests require an explicit human merge decision",
      )
      prefix_rule(
        pattern = ["bin/grant-root"],
        decision = "prompt",
        justification = "Root access requires an explicit time-bounded grant",
      )
      prefix_rule(
        pattern = ["./bin/grant-root"],
        decision = "prompt",
        justification = "Root access requires an explicit time-bounded grant",
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
        "gh pr merge*" = "ask";  # git push runs free (branch pushes); PR-merge stays the gate, matching Claude above
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
