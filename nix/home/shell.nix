{ pkgs, ... }:
# aliammar's interactive shell — zsh + starship + zoxide/fzf/eza/bat, and a login that drops you in
# the repo with a status board. Interactive ONLY: the nightly/timers and `ssh host <cmd>` run bash
# scripts and never source this (zsh reads .zprofile/.zshrc for login/interactive shells only), so
# the ops loop is unaffected. Icons/glyphs assume a Nerd Font in YOUR terminal — see the PR notes.
{
  home.sessionPath = [ "$HOME/.local/bin" ];

  # Supporting CLIs (the eza/bat/etc. binaries come from their programs.* modules below).
  home.packages = with pkgs; [ eza fd ripgrep tree dust ];

  programs.zsh = {
    enable = true;
    autocd = true; # type a dir name to cd into it
    enableCompletion = true;
    autosuggestion.enable = true; # fish-style ghost suggestions from history
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
    '';
    # .zprofile — login shells only. Land in the repo and print the board.
    profileExtra = ''
      if [[ -o interactive ]]; then
        cd ~/skynet 2>/dev/null || true
        [ -x ~/.local/bin/skynet-motd ] && ~/.local/bin/skynet-motd
      fi
    '';
  };

  programs.starship = {
    enable = true;
    enableZshIntegration = true;
    settings = {
      add_newline = true;
      # It's a server — always show who/where, in Skynet red.
      hostname = { ssh_only = false; style = "bold red"; format = "[$hostname]($style) "; };
      username = { show_always = true; style_user = "bold yellow"; format = "[$user]($style)@"; };
      directory = { truncation_length = 4; style = "bold cyan"; };
      git_branch = { symbol = " "; style = "bold magenta"; };
      git_status = { style = "bold yellow"; };
      cmd_duration = { min_time = 1000; style = "dim white"; };
      nix_shell = { symbol = " "; format = "[$symbol$name]($style) "; };
      character = { success_symbol = "[▸](bold green)"; error_symbol = "[▸](bold red)"; };
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
    source = ./skynet-motd.sh;
    executable = true;
  };
}
