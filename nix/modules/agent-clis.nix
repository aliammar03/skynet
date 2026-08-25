{ pkgs, inputs, ... }:
# Agent CLIs, declaratively, from nixpkgs-unstable (NOT npm-global — supersedes the old
# "runtime is replaceable" decision now that they're packaged). Fast-moving, so they ride the
# separate `nixpkgs-unstable` input (bump that input to update them); the host stays on 26.05.
let
  unstable = import inputs.nixpkgs-unstable {
    inherit (pkgs) system;
    config.allowUnfree = true;
  };
in
{
  environment.systemPackages = [
    unstable.claude-code
    unstable.codex
    unstable.antigravity
    unstable.pi-coding-agent
    unstable.opencode
    unstable.aider-chat
  ];
}
