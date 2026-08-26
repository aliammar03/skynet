#!/usr/bin/env bash
# skynet-motd — the login landing board for the Skynet ops box. Fast, read-only; printed from
# ~/.zprofile on interactive login (nix/home/shell.nix). Edit here, not in the Nix string.
set -u
e() { printf '\033[%sm' "$1"; }
RST=$(e 0); CYA=$(e '1;36'); DIM=$(e '2;37'); YEL=$(e '1;33'); GRN=$(e '1;32')

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
printf '  %s◈ SKYNET OPS%s   %sdeclarative · impermanent · least-privilege%s\n' "$CYA" "$RST" "$DIM" "$RST"
printf '  %s%s%s\n' "$DIM" "$rule" "$RST"
printf '   %snode%s   %s  ·  %s\n' "$YEL" "$RST" "$host" "${ip:-?}"
printf '   %sos  %s   NixOS %s (gen %s)  ·  up %s\n' "$YEL" "$RST" "${osver:-?}" "${gen:-?}" "${up:-?}"
printf '   %srepo%s   %s  ·  %b\n' "$YEL" "$RST" "$branch" "$tree"
printf '   %shead%s   %s%s%s\n' "$YEL" "$RST" "$DIM" "$head" "$RST"
printf '  %s%s%s\n' "$DIM" "$rule" "$RST"
printf '   %ssudo -i%s          root shell (your password)\n' "$GRN" "$RST"
printf '   %sbin/ops collect%s  refresh inventory\n' "$GRN" "$RST"
printf '   %srebuild%s          sudo nixos-rebuild switch --flake ~/skynet\n' "$GRN" "$RST"
printf '   %sz <dir>%s          jump around (zoxide)  ·  %smotd%s replays this\n' "$GRN" "$RST" "$GRN" "$RST"
printf '\n'
