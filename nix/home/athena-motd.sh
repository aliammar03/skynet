#!/usr/bin/env bash
# athena-motd — minimal, nix-focused login board for lxc-athena (the Obsidian vault librarian).
# Printed from ~/.zprofile on interactive login (nix/home/shell.nix). Edit here, not in the Nix
# string. No ops actions — this box has no lab authority; it curates the vault under ~/athena.
set -u
e() { printf '\033[%sm' "$1"; }
# Catppuccin Macchiato, matching the starship prompt — truecolor, no bold.
RST=$(e 0)
MAV=$(e '38;2;198;160;246')  # mauve  — header
TEA=$(e '38;2;139;213;202')  # teal   — values
SUB=$(e '38;2;165;173;203')  # subtext— keys
OVR=$(e '38;2;110;115;141')  # overlay— rules / dim
GRN=$(e '38;2;166;218;149')  # green  — clean / actions

host=$(cat /proc/sys/kernel/hostname 2>/dev/null || echo '?')
ip=$(hostname -I 2>/dev/null | awk '{print $1}')
osver=$(cut -d. -f1-2 /run/current-system/nixos-version 2>/dev/null)
gen=$(readlink /nix/var/nix/profiles/system 2>/dev/null | grep -oE '[0-9]+' | head -1)
up=$(awk '{s=int($1);h=int((s%86400)/3600);m=int((s%3600)/60);d=int(s/86400);
  if(d>0)printf "%dd %dh",d,h; else if(h>0)printf "%dh %dm",h,m; else printf "%dm",m}' /proc/uptime 2>/dev/null)
vault="$HOME/athena"
notes=$(find "$vault" -type f -name '*.md' 2>/dev/null | grep -c '')
rule='──────────────────────────────────────────────'

printf '\n'
printf '  %s◈ ATHENA%s   %sObsidian vault librarian · NixOS%s\n' "$MAV" "$RST" "$OVR" "$RST"
printf '  %s%s%s\n' "$OVR" "$rule" "$RST"
printf '   %snode %s   %s%s  ·  %s%s\n' "$SUB" "$RST" "$TEA" "$host" "${ip:-?}" "$RST"
printf '   %snixos%s   %s%s (gen %s)%s  ·  up %s\n' "$SUB" "$RST" "$TEA" "${osver:-?}" "${gen:-?}" "$RST" "${up:-?}"
printf '   %svault%s   %s~/athena%s  ·  %s%s notes%s\n' "$SUB" "$RST" "$TEA" "$RST" "$GRN" "${notes:-0}" "$RST"
printf '  %s%s%s\n' "$OVR" "$rule" "$RST"
printf '   %sclaude%s / %scodex%s   %scoding agents%s  ·  %sz <dir>%s jump  ·  %smotd%s replay\n' \
  "$GRN" "$RST" "$GRN" "$RST" "$SUB" "$RST" "$GRN" "$RST" "$GRN" "$RST"
printf '\n'
