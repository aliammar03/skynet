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
#   scripts/recon.sh <host> --json        # machine-readable object instead of Markdown
# Output: a Markdown snapshot (default) or JSON (--json) on stdout — services, unit health,
#   disk/mem/cpu, listening ports, container health, recent warnings, and recent config/
#   package changes. Redirect it to a file to attach to a journal incident record (see
#   runbooks/recon.md). Each probe is bounded by RECON_TIMEOUT (default 6s) so a hung mount
#   or wedged daemon can never freeze the snapshot.
set -uo pipefail   # NOT -e: recon must survive individual probes failing.

# ── args ──────────────────────────────────────────────────────────────────────
mode=md
target=""
for a in "$@"; do
  case "$a" in
    -h|--help) sed -n '2,16p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    --json)    mode=json ;;
    -*)        echo "recon: unknown flag '$a' (see --help)" >&2; exit 2 ;;
    *)         target="$a" ;;
  esac
done
target="${target:-local}"

# ── the remote/local probe bundle ─────────────────────────────────────────────
# One self-contained snippet, fed to bash via stdin (`bash -s`) so it runs the same
# way locally or over SSH with zero quoting games. Read-only commands only. Output is a
# neutral marker stream (@@META@@ / @@SEC@@) that the local renderers turn into Markdown
# or JSON — one source of truth, two renderings. `t` bounds every external probe so one
# hung command (stale NFS df, wedged docker) can't stall the whole snapshot.
read -r -d '' PROBE <<'PROBE_EOF' || true
set +e
have() { command -v "$1" >/dev/null 2>&1; }
t()    { if have timeout; then timeout "${RECON_TIMEOUT:-6}" "$@"; else "$@"; fi; }
sec()  { printf '@@SEC@@%s\n' "$1"; }

printf '@@META@@host\t%s\n'      "$(hostname -f 2>/dev/null || hostname)"
printf '@@META@@collected\t%s\n' "$(date -Iseconds)"
printf '@@META@@as\t%s@%s\n'     "$(id -un)" "$(hostname)"

sec 'Host'
printf 'kernel : %s\n' "$(uname -sr)"
if have hostnamectl; then hostnamectl 2>/dev/null | sed -n 's/^ *Operating System: /os     : /p'; fi
printf 'uptime : %s\n' "$(uptime -p 2>/dev/null || uptime)"
printf 'booted : %s\n' "$(uptime -s 2>/dev/null || echo '?')"

sec 'Load / memory / CPU'
printf 'load   : %s   (cores: %s)\n' "$(cut -d' ' -f1-3 /proc/loadavg 2>/dev/null)" "$(nproc 2>/dev/null)"
have free && t free -h 2>/dev/null

sec 'Disk — usage then inodes (fullest first)'
t df -hP -x tmpfs -x devtmpfs -x overlay -x squashfs 2>/dev/null | (read -r h; echo "$h"; sort -k5 -hr)
printf -- '--- inodes ---\n'
t df -iP -x tmpfs -x devtmpfs -x overlay -x squashfs 2>/dev/null | (read -r h; echo "$h"; sort -k5 -hr)

sec 'systemd — failed units'
if have systemctl; then
  f="$(t systemctl --failed --no-legend --plain --no-pager 2>/dev/null)"
  [ -n "$f" ] && echo "$f" || echo '(none failed)'
else echo '(no systemd on this host)'; fi

sec 'Listening sockets (TCP/UDP)'
if have ss; then
  t ss -tulnH 2>/dev/null | awk '{printf "%-5s %-6s %s\n",$1,$2,$5}' | sort -u
  echo '(process names need root — run a diagnosis runbook under a grant if you need them)'
else echo '(ss unavailable)'; fi

sec 'Containers (docker, unprivileged)'
if have docker && t docker info >/dev/null 2>&1; then
  t docker ps --all --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}' 2>/dev/null
  unh="$(t docker ps --filter health=unhealthy --format '{{.Names}}' 2>/dev/null)"
  [ -n "$unh" ] && printf -- '--- UNHEALTHY: %s\n' "$unh"
else echo '(no docker access from this user)'; fi

sec 'Recent warnings/errors (journal, last boot)'
if have journalctl && journalctl -n0 >/dev/null 2>&1; then
  t journalctl -p warning -b --no-pager 2>/dev/null | tail -n 40
else echo '(journal not readable as this user — add to systemd-journal group or use a grant)'; fi

sec 'Recent config changes — /etc modified in last 7 days'
changed="$(t find /etc -type f -mtime -7 2>/dev/null | sort)"
[ -n "$changed" ] && echo "$changed" | head -n 40 || echo '(none)'

sec 'Recent package changes (last 20)'
if [ -f /var/log/dpkg.log ]; then
  grep -hE ' (install|upgrade|remove) ' /var/log/dpkg.log /var/log/dpkg.log.1 2>/dev/null \
    | awk '{print $1, $2, $3, $4, $5}' | tail -n 20
elif have rpm; then t rpm -qa --last 2>/dev/null | head -n 20
else echo '(no dpkg/rpm history found)'; fi
PROBE_EOF

# ── renderers: neutral marker stream → Markdown or JSON ───────────────────────
# Parse once into ordered sections, then emit the requested format.
render() {
  local -a order=(); declare -A sect=()
  local host='' collected='' as='' cur=''
  local line kv k v
  while IFS= read -r line; do
    case "$line" in
      '@@META@@'*) kv="${line#@@META@@}"; k="${kv%%$'\t'*}"; v="${kv#*$'\t'}"
                   case "$k" in host) host="$v";; collected) collected="$v";; as) as="$v";; esac ;;
      '@@SEC@@'*)  cur="${line#@@SEC@@}"; order+=("$cur"); sect["$cur"]='' ;;
      *)           [ -n "$cur" ] && sect["$cur"]+="$line"$'\n' ;;
    esac
  done
  if [ "${mode}" = json ]; then
    { for s in "${order[@]}"; do jq -n --arg k "$s" --arg v "${sect[$s]}" '{key:$k,value:$v}'; done; } \
      | jq -s --arg host "$host" --arg collected "$collected" --arg as "$as" \
          '{host:$host, collected:$collected, as:$as, sections:(map({(.key):.value})|add)}'
  else
    printf '# recon: %s\ncollected: %s   as: %s\n' "$host" "$collected" "$as"
    # shellcheck disable=SC2016  # %s are printf specifiers, not shell expansions — single quotes are correct
    for s in "${order[@]}"; do printf '\n## %s\n\n```\n%s```\n' "$s" "${sect[$s]}"; done
    # Routing: map observed signals to the matching diagnosis runbook, so recon points at the
    # next step instead of leaving the reader to match the table (SKY-005 P2). Signals only fire
    # on what a host snapshot can actually see (crash-loop, disk/inode pressure, failed units,
    # backup units) — cert/DNS are symptom-driven, reached from their own triggers.
    local all='' s2; for s2 in "${order[@]}"; do all+="${sect[$s2]}"$'\n'; done
    local -a nextr=()
    printf '%s' "$all" | grep -qiE 'restarting|unhealthy|Exited \([1-9]' \
      && nextr+=('a container is crash-looping / unhealthy → runbooks/diagnose/container-crashloop.md')
    printf '%s' "$all" | awk '{for(i=1;i<=NF;i++) if($i ~ /^[0-9]+%$/ && $i+0>=90) f=1} END{exit !f}' \
      && nextr+=('a filesystem or inode table is ≥90% full → runbooks/diagnose/disk-full.md')
    printf '%s' "$all" | grep -qiE 'restic|pbs|backup' \
      && nextr+=('a backup/restic/pbs unit is present → runbooks/diagnose/backup-missed.md')
    case "${sect['systemd — failed units']:-}" in
      *'(none failed)'*|'') : ;;
      *) nextr+=('a systemd unit is failed → read the unit, then the matching runbook above') ;;
    esac
    if [ "${#nextr[@]}" -gt 0 ]; then
      printf '\n## Next — likely diagnosis runbooks\n\n'
      local r; for r in "${nextr[@]}"; do printf -- '- %s\n' "$r"; done
    fi
    printf '\n_recon complete — T1 read-only. Reason over this, then pick a diagnosis runbook._\n'
  fi
}

# ── dispatch: local or over SSH → the renderer ────────────────────────────────
selfhost="$(hostname -s 2>/dev/null || hostname)"
probe() {
  case "${target}" in
    local|localhost|"${selfhost}") bash -s <<<"${PROBE}" ;;
    *)
      local ssh_target="${target}"
      [[ "${target}" == *@* ]] || ssh_target="svc-ops@${target}"
      if ! ssh -o BatchMode=yes -o ConnectTimeout=8 "${ssh_target}" true 2>/dev/null; then
        echo "recon: cannot reach ${ssh_target} over SSH (unprivileged svc-ops). Is the host onboarded?" >&2
        return 1
      fi
      ssh -o BatchMode=yes -o ConnectTimeout=8 "${ssh_target}" bash -s <<<"${PROBE}" ;;
  esac
}

out="$(probe)" || exit 1
[ -n "${out}" ] || { echo "recon: no data collected from ${target}" >&2; exit 1; }
printf '%s\n' "${out}" | render
