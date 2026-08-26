#!/usr/bin/env bash
# skynet-motd — the login landing board for the Skynet ops box. Fast, read-only; printed from
# ~/.zprofile on interactive login (nix/home/shell.nix). Edit here, not in the Nix string.
set -u
e() { printf '\033[%sm' "$1"; }
# Soft muted palette (Catppuccin Macchiato), matching the starship prompt — truecolor, no bold.
RST=$(e 0)
MAV=$(e '38;2;198;160;246')  # mauve  — header
TEA=$(e '38;2;139;213;202')  # teal   — values
SUB=$(e '38;2;165;173;203')  # subtext— keys
OVR=$(e '38;2;110;115;141')  # overlay— rules / dim
GRN=$(e '38;2;166;218;149')  # green  — actions
YEL=$(e '38;2;238;212;159')  # yellow — dirty repo

host=$(cat /proc/sys/kernel/hostname 2>/dev/null || echo '?')
ip=$(hostname -I 2>/dev/null | awk '{print $1}')
osver=$(cut -d. -f1-2 /run/current-system/nixos-version 2>/dev/null)
gen=$(readlink /nix/var/nix/profiles/system 2>/dev/null | grep -oE '[0-9]+' | head -1)
up=$(awk '{s=int($1);d=int(s/86400);h=int((s%86400)/3600);m=int((s%3600)/60);
  if(d>0)printf "%dd %dh",d,h; else if(h>0)printf "%dh %dm",h,m; else printf "%dm",m}' /proc/uptime 2>/dev/null)
repo="$HOME/skynet"
branch=$(git -C "$repo" branch --show-current 2>/dev/null || echo '-')
n=$(git -C "$repo" status --porcelain 2>/dev/null | grep -c '' )
if [ "${n:-0}" -eq 0 ] 2>/dev/null; then tree="${GRN}clean${RST}"; else tree="${YEL}${n} changed${RST}"; fi
head=$(git -C "$repo" log -1 --format='%h %s' 2>/dev/null | cut -c1-46)
rule='──────────────────────────────────────────────'

printf '\n'
printf '  %s◈ SKYNET OPS%s   %sdeclarative · impermanent · least-privilege%s\n' "$MAV" "$RST" "$OVR" "$RST"
printf '  %s%s%s\n' "$OVR" "$rule" "$RST"
printf '   %snode%s   %s%s  ·  %s%s\n' "$SUB" "$RST" "$TEA" "$host" "${ip:-?}" "$RST"
printf '   %sos  %s   %sNixOS %s (gen %s)%s  ·  up %s\n' "$SUB" "$RST" "$TEA" "${osver:-?}" "${gen:-?}" "$RST" "${up:-?}"
printf '   %srepo%s   %s%s%s  ·  %b\n' "$SUB" "$RST" "$TEA" "$branch" "$RST" "$tree"
printf '   %shead%s   %s%s%s\n' "$SUB" "$RST" "$OVR" "$head" "$RST"
printf '  %s%s%s\n' "$OVR" "$rule" "$RST"
printf '   %ssudo -i%s          %sroot shell (your password)%s\n' "$GRN" "$RST" "$SUB" "$RST"
printf '   %sbin/ops collect%s  %srefresh inventory%s\n' "$GRN" "$RST" "$SUB" "$RST"
printf '   %srebuild%s          %ssudo nixos-rebuild switch --flake ~/skynet%s\n' "$GRN" "$RST" "$SUB" "$RST"
printf '   %sz <dir>%s          %sjump around (zoxide)%s  ·  %smotd%s %sreplays this%s\n' "$GRN" "$RST" "$SUB" "$RST" "$GRN" "$RST" "$SUB" "$RST"
printf '\n'
