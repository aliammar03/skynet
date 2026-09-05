# aliammar's interactive shell — zsh + starship + zoxide/fzf/eza/bat, and a login that drops you in
# a landing dir with a status board. Interactive ONLY: the nightly/timers and `ssh host <cmd>` run
# bash scripts and never source this (zsh reads .zprofile/.zshrc for login/interactive shells only),
# so the ops loop is unaffected. Icons/glyphs assume a Nerd Font in YOUR terminal — see the PR notes.
#
# Parameterized (`landingDir` = where an interactive login lands, `motdSource` = the board script) so
# it's reusable; the ops VM imports it with `{ }` (defaults below). athena keeps its own vendored copy
# in aliammar03/athena, so this file serves only the ops VM today.
{ landingDir ? "$HOME/skynet", motdSource ? ./skynet-motd.sh }:
{ pkgs, ... }:
{
  home.sessionPath = [ "$HOME/.local/bin" ];

  # Supporting CLIs (the eza/bat/etc. binaries come from their programs.* modules below).
  home.packages = with pkgs; [ eza fd ripgrep tree dust ];

  programs.zsh = {
    enable = true;
    autocd = true; # type a dir name to cd into it
    enableCompletion = true;
    autosuggestion = {
      enable = true; # fish-style ghost suggestions from history
      highlight = "fg=#6e738d"; # dim overlay so the ghost text stays subtle
    };
    syntaxHighlighting.enable = true; # command-line syntax colors
    historySubstringSearch.enable = true; # ↑/↓ search history by the prefix you typed
    history = {
      size = 50000;
      save = 50000;
      ignoreDups = true;
      ignoreSpace = true;
      share = true;
      extended = true;
    };
    shellAliases = {
      ls = "eza --group-directories-first --icons=auto";
      ll = "eza -lah --group-directories-first --git --icons=auto";
      la = "eza -a --group-directories-first --icons=auto";
      lt = "eza --tree --level=2 --icons=auto";
      cat = "bat --paging=never";
      gs = "git status -sb";
      gd = "git diff";
      gl = "git log --oneline --graph --decorate -20";
      # Now that aliammar has password sudo, the simplest day-2 rebuild: build locally, activate as
      # root. `--flake ~/skynet` auto-selects nixosConfigurations.<hostname>, so it survives the
      # rename at cutover. deploy-rs (magic-rollback) stays the safer path for risky changes.
      rebuild = "sudo nixos-rebuild switch --flake ~/skynet";
      motd = "~/.local/bin/skynet-motd";
    };
    # Nicer completion: case-insensitive, a selectable menu, LS_COLORS-tinted.
    initContent = ''
      zstyle ':completion:*' matcher-list 'm:{a-zA-Z}={A-Za-z}'
      zstyle ':completion:*' menu select
      zstyle ':completion:*' list-colors "''${(s.:.)LS_COLORS}"
      setopt AUTO_PUSHD PUSHD_IGNORE_DUPS PUSHD_SILENT
      # Soften zsh-syntax-highlighting to the muted palette (defaults are quite bright/harsh).
      typeset -gA ZSH_HIGHLIGHT_STYLES
      ZSH_HIGHLIGHT_STYLES[command]='fg=#a6da95'
      ZSH_HIGHLIGHT_STYLES[builtin]='fg=#8bd5ca'
      ZSH_HIGHLIGHT_STYLES[function]='fg=#8aadf4'
      ZSH_HIGHLIGHT_STYLES[alias]='fg=#a6da95'
      ZSH_HIGHLIGHT_STYLES[path]='fg=#cad3f5'
      ZSH_HIGHLIGHT_STYLES[unknown-token]='fg=#ed8796'
    '';
    # .zprofile — login shells only. Land in the configured dir and print the board.
    profileExtra = ''
      if [[ -o interactive ]]; then
        cd ${landingDir} 2>/dev/null || true
        [ -x ~/.local/bin/skynet-motd ] && ~/.local/bin/skynet-motd
      fi
    '';
  };

  programs.starship = {
    enable = true;
    enableZshIntegration = true;
    # Soft muted palette (Catppuccin Macchiato) — pastel, no bold, gentle on the eyes. Two-line:
    #   user@host  dir  branch status
    #   ❯
    settings = {
      add_newline = true;
      format = "$username$hostname$directory$git_branch$git_status$nix_shell$cmd_duration$line_break$character";
      username = { show_always = true; style_user = "#c6a0f6"; format = "[$user]($style)"; }; # mauve
      hostname = { ssh_only = false; style = "#8aadf4"; format = "[@$hostname]($style)"; }; # blue
      directory = { style = "#8bd5ca"; truncation_length = 4; truncation_symbol = "…/"; format = "  [$path]($style) "; }; # teal
      git_branch = { symbol = " "; style = "#f5a97f"; format = "[$symbol$branch]($style) "; }; # peach
      git_status = { style = "#eed49f"; format = "[$all_status$ahead_behind]($style)"; }; # yellow
      nix_shell = { symbol = " "; style = "#a5adcb"; format = "[$symbol$name]($style) "; };
      cmd_duration = { min_time = 2000; style = "#6e738d"; format = "[ $duration]($style)"; }; # overlay/dim
      character = { success_symbol = "[❯](#a6da95)"; error_symbol = "[❯](#ed8796)"; }; # soft green / soft red
    };
  };

  programs.zoxide = { enable = true; enableZshIntegration = true; }; # `z <frecent-dir>`
  programs.fzf = { enable = true; enableZshIntegration = true; }; # Ctrl-R history, Ctrl-T files
  programs.bat = { enable = true; config = { style = "plain"; paging = "never"; }; };

  # Public half of the agent key (private half arrives via sops-nix → ~/.ssh/id_ed25519, see
  # nix/modules/secrets.nix). Declarative because it's public; ssh derives it from the key anyway.
  home.file.".ssh/id_ed25519.pub".text =
    "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDaJEkEwSMl7iSgXeokZIKSVj4TgE4p8Bljx26LmrK0d svc-ops@vm-skynet-ops\n";

  home.file.".local/bin/skynet-motd" = {
    source = motdSource;
    executable = true;
  };
}
