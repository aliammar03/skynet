#!/usr/bin/env bash
# recon.sh — T1 read-only host snapshot: one structured picture, no grant to observe.
# TIER: T1. Runs as the unprivileged svc-ops user (local or over SSH). Never needs root —
#   that is the point: *looking* stays inside T1. Where root would reveal more (process
#   names on ports, full journal), the section degrades and says so instead of failing.
# USAGE:
#   scripts/recon.sh                      # recon THIS host (the ops VM)
#   scripts/recon.sh <host>               # recon a remote host as svc-ops over SSH
#   scripts/recon.sh svc-ops@10.10.100.15 # explicit ssh target (user@host)
#   scripts/recon.sh docker-dmz > snap.md # a bare label maps to svc-ops@<label>
# Output: a Markdown snapshot on stdout — services, unit health, disk/mem/cpu, listening
#   ports, container health, recent warnings, and recent config/package changes. Redirect
#   it to a file to attach to a journal incident record (see runbooks/recon.md).
set -uo pipefail   # NOT -e: recon must survive individual probes failing.

case "${1:-}" in
  -h|--help)
    sed -n '2,17p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
esac

target="${1:-local}"

# ── the remote/local probe bundle ─────────────────────────────────────────────
# One self-contained snippet, fed to bash via stdin (`bash -s`) so it runs the same
# way locally or over SSH with zero quoting games. Read-only commands only.
read -r -d '' PROBE <<'PROBE_EOF' || true
set +e
have() { command -v "$1" >/dev/null 2>&1; }
sec()  { printf '\n## %s\n\n' "$1"; }
fence(){ printf '```\n'; }

printf '# recon: %s\n' "$(hostname -f 2>/dev/null || hostname)"
printf 'collected: %s   as: %s@%s\n' "$(date -Iseconds)" "$(id -un)" "$(hostname)"

sec 'Host'
fence
printf 'kernel : %s\n' "$(uname -sr)"
if have hostnamectl; then hostnamectl 2>/dev/null | sed -n 's/^ *Operating System: /os     : /p'; fi
printf 'uptime : %s\n' "$(uptime -p 2>/dev/null || uptime)"
printf 'booted : %s\n' "$(uptime -s 2>/dev/null || echo '?')"
fence

sec 'Load / memory / CPU'
fence
printf 'load   : %s   (cores: %s)\n' "$(cut -d' ' -f1-3 /proc/loadavg 2>/dev/null)" "$(nproc 2>/dev/null)"
have free && free -h 2>/dev/null
fence

sec 'Disk — usage then inodes (fullest first)'
fence
df -hP -x tmpfs -x devtmpfs -x overlay -x squashfs 2>/dev/null | (read -r h; echo "$h"; sort -k5 -hr)
printf -- '--- inodes ---\n'
df -iP -x tmpfs -x devtmpfs -x overlay -x squashfs 2>/dev/null | (read -r h; echo "$h"; sort -k5 -hr)
fence

sec 'systemd — failed units'
fence
if have systemctl; then
  f="$(systemctl --failed --no-legend --plain --no-pager 2>/dev/null)"
  [ -n "$f" ] && echo "$f" || echo '(none failed)'
else echo '(no systemd on this host)'; fi
fence

sec 'Listening sockets (TCP/UDP)'
fence
if have ss; then
  ss -tulnH 2>/dev/null | awk '{printf "%-5s %-6s %s\n",$1,$2,$5}' | sort -u
  echo '(process names need root — run a diagnosis runbook under a grant if you need them)'
else echo '(ss unavailable)'; fi
fence

sec 'Containers (docker, unprivileged)'
fence
if have docker && docker info >/dev/null 2>&1; then
  docker ps --all --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}' 2>/dev/null
  unh="$(docker ps --filter health=unhealthy --format '{{.Names}}' 2>/dev/null)"
  [ -n "$unh" ] && printf -- '--- UNHEALTHY: %s\n' "$unh"
else echo '(no docker access from this user)'; fi
fence

sec 'Recent warnings/errors (journal, last boot)'
fence
if have journalctl && journalctl -n0 >/dev/null 2>&1; then
  journalctl -p warning -b --no-pager 2>/dev/null | tail -n 40
else echo '(journal not readable as this user — add to systemd-journal group or use a grant)'; fi
fence

sec 'Recent config changes — /etc modified in last 7 days'
fence
find /etc -type f -mtime -7 2>/dev/null | sort | head -n 40
[ "$(find /etc -type f -mtime -7 2>/dev/null | wc -l)" -eq 0 ] && echo '(none)'
fence

sec 'Recent package changes (last 20)'
fence
if [ -f /var/log/dpkg.log ]; then
  grep -hE ' (install|upgrade|remove) ' /var/log/dpkg.log /var/log/dpkg.log.1 2>/dev/null \
    | awk '{print $1, $2, $3, $4, $5}' | tail -n 20
elif have rpm; then rpm -qa --last 2>/dev/null | head -n 20
else echo '(no dpkg/rpm history found)'; fi
fence

printf '\n_recon complete — T1 read-only. Reason over this, then pick a diagnosis runbook._\n'
PROBE_EOF

# ── dispatch: local or over SSH ───────────────────────────────────────────────
selfhost="$(hostname -s 2>/dev/null || hostname)"
case "${target}" in
  local|localhost|"${selfhost}")
    exec bash -s <<<"${PROBE}" ;;
  *)
    ssh_target="${target}"
    [[ "${target}" == *@* ]] || ssh_target="svc-ops@${target}"
    if ! ssh -o BatchMode=yes -o ConnectTimeout=8 "${ssh_target}" true 2>/dev/null; then
      echo "recon: cannot reach ${ssh_target} over SSH (unprivileged svc-ops). Is the host onboarded?" >&2
      exit 1
    fi
    exec ssh -o BatchMode=yes -o ConnectTimeout=8 "${ssh_target}" bash -s <<<"${PROBE}" ;;
esac
