#!/usr/bin/env bash
# provision-restic.sh — provision a host for restic → Google Drive backups (plan §6 L3, A4.5).
#
# Orchestrated FROM vm-skynet-ops over SSH (like gitops-deploy.sh). One command turns a fresh
# host into a backed-up one: installs restic+rclone, stages secrets 0600, generates the repo
# password ON the host, writes the backup selection, deploys backup-restic.sh + the systemd
# timer, and inits the repo. Handles docker hosts and/or any folders of your choosing.
#
# IDEMPOTENT: safe to re-run — it never regenerates the repo password and never re-inits an
# existing repo (doing either would strand every existing snapshot).
#
# TIER: T2+ — needs an ACTIVE ROOT GRANT to the target (`gr <host>`); connects as root@<ip>.
#
# USAGE:
#   scripts/provision-restic.sh <label> <ssh-target> [options]
#     <label>        repo/env/timer name, e.g. docker-dmz  (repo=Skynet/Backups/restic/<label>)
#     <ssh-target>   root@<ip> — a live grant must cover this host
#   options:
#     --docker             back up /opt/docker/appdata + skynet.backup=protect named volumes
#     --path DIR           back up an extra absolute folder (repeatable)
#     --exclude PAT        extra restic exclude pattern (repeatable)
#     --time HH:MM         nightly schedule (default 02:30)
#     --no-timer           set everything up but do not install/enable the timer
#     --firstrun           run the first backup now (default: leave it to the timer; note the
#                          agent's safety guard may block agent-initiated external uploads)
#
# EXAMPLES:
#   scripts/provision-restic.sh docker-dmz root@10.10.100.15 --docker
#   scripts/provision-restic.sh app-01 root@10.10.90.41 --path /srv/appdata --path /etc/caddy
#   scripts/provision-restic.sh media root@10.10.90.42 --docker --path /srv/library --time 03:15
set -euo pipefail

LABEL="${1:?usage: provision-restic.sh <label> <ssh-target> [options]}"
TARGET="${2:?ssh target, e.g. root@10.10.100.15 (needs a live grant)}"
shift 2

WANT_DOCKER=no; PATHS=(); EXCLUDES=(); SCHED="02:30"; INSTALL_TIMER=yes; FIRSTRUN=no
while [ $# -gt 0 ]; do
  case "$1" in
    --docker)   WANT_DOCKER=yes ;;
    --path)     PATHS+=("${2:?--path needs a dir}"); shift ;;
    --exclude)  EXCLUDES+=("${2:?--exclude needs a pattern}"); shift ;;
    --time)     SCHED="${2:?--time needs HH:MM}"; shift ;;
    --no-timer) INSTALL_TIMER=no ;;
    --firstrun) FIRSTRUN=yes ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
  shift
done

[ "${WANT_DOCKER}" = yes ] || [ "${#PATHS[@]}" -gt 0 ] || {
  echo "nothing to back up: pass --docker and/or --path DIR" >&2; exit 2; }

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RCLONE_SRC="/opt/skynet-ops/secrets/rclone.conf"        # source of truth on skynet-ops
REPO="rclone:gdrive:Skynet/Backups/restic/${LABEL}"
SECRETS="/opt/skynet-ops/secrets"
ENVF="${SECRETS}/restic-${LABEL}.env"
PASSF="${SECRETS}/restic-${LABEL}.pass"

sudo test -r "${RCLONE_SRC}" || { echo "missing ${RCLONE_SRC} on skynet-ops (A2 rclone step)" >&2; exit 1; }

sshc() { ssh -o BatchMode=yes -o ConnectTimeout=10 "${TARGET}" "$@"; }

echo "==> [1/7] preflight: root on ${TARGET}"
sshc 'test "$(id -u)" -eq 0' || { echo "cannot get root on ${TARGET} — is the grant active? (gr <host>)" >&2; exit 1; }

echo "==> [2/7] install restic + rclone"
sshc 'command -v restic >/dev/null && command -v rclone >/dev/null' || \
  sshc 'export DEBIAN_FRONTEND=noninteractive; apt-get update -qq && apt-get install -y -qq restic rclone >/dev/null'
sshc 'echo "    $(restic version | head -1); rclone $(rclone version | head -1 | awk "{print \$2}")"'

echo "==> [3/7] secrets/scripts dirs + rclone.conf (0600)"
sshc 'install -d -m 700 -o root -g root '"${SECRETS}"'; install -d -m 755 -o root -g root /opt/skynet-ops/scripts'
sudo cat "${RCLONE_SRC}" | sshc "umask 077; cat > '${SECRETS}/rclone.conf'; chmod 600 '${SECRETS}/rclone.conf'"

echo "==> [4/7] repo password (generate ONCE, never overwrite)"
sshc "umask 077; if [ ! -s '${PASSF}' ]; then openssl rand -base64 33 > '${PASSF}'; chmod 600 '${PASSF}'; echo '    generated new password'; else echo '    password already present — kept'; fi"

echo "==> [5/7] write ${ENVF}"
# Build BACKUP_PATHS / RESTIC_EXCLUDES strings for the env file.
PATHS_STR="${PATHS[*]:-}"
EXCL_STR="${EXCLUDES[*]:-}"
DOCKER_VAL="no"; [ "${WANT_DOCKER}" = yes ] && DOCKER_VAL="yes"
sshc "umask 077; cat > '${ENVF}' <<EOF
# restic env for ${LABEL} (plan §6 L3) — sourced by backup-restic.sh ${LABEL}
export RESTIC_REPOSITORY='${REPO}'
export RESTIC_PASSWORD_FILE=${PASSF}
export RCLONE_CONFIG=${SECRETS}/rclone.conf
BACKUP_DOCKER=${DOCKER_VAL}
BACKUP_PATHS=\"${PATHS_STR}\"
RESTIC_EXCLUDES=\"${EXCL_STR}\"
EOF
chmod 600 '${ENVF}'; echo '    wrote '${ENVF}"

echo "==> [6/7] deploy backup-restic.sh + init repo"
cat "${REPO_ROOT}/scripts/backup-restic.sh" | sshc "cat > /opt/skynet-ops/scripts/backup-restic.sh; chmod 755 /opt/skynet-ops/scripts/backup-restic.sh"
sshc "set -a; . '${ENVF}'; set +a; restic cat config >/dev/null 2>&1 && echo '    repo already initialised' || restic init 2>&1 | grep -i 'created restic repository' || true"

echo "==> [7/7] systemd timer"
if [ "${INSTALL_TIMER}" = yes ]; then
  cat "${REPO_ROOT}/scripts/systemd/skynet-restic-backup@.service" | sshc 'cat > /etc/systemd/system/skynet-restic-backup@.service'
  # timer with the requested schedule (override OnCalendar from the committed default)
  sshc "cat > /etc/systemd/system/skynet-restic-backup@.timer <<EOF
[Unit]
Description=Nightly skynet restic backup (%i)

[Timer]
OnCalendar=*-*-* ${SCHED}:00
RandomizedDelaySec=30m
Persistent=true

[Install]
WantedBy=timers.target
EOF"
  sshc "systemctl daemon-reload && systemctl enable --now 'skynet-restic-backup@${LABEL}.timer' >/dev/null 2>&1; systemctl list-timers 'skynet-restic-backup@${LABEL}.timer' --no-pager | sed -n '2p'"
else
  echo "    --no-timer: skipped"
fi

if [ "${FIRSTRUN}" = yes ]; then
  echo "==> first backup (now)"
  sshc "/opt/skynet-ops/scripts/backup-restic.sh '${LABEL}'"
fi

cat <<DONE

provisioned '${LABEL}' on ${TARGET}
  repo:    ${REPO}
  backs up: $([ "${WANT_DOCKER}" = yes ] && echo -n 'docker(appdata+protect vols) ' )${PATHS_STR}
  timer:   $([ "${INSTALL_TIMER}" = yes ] && echo "skynet-restic-backup@${LABEL} @ ${SCHED} (+jitter)" || echo 'not installed')

NEXT:
  * Save the repo password to the survival kit (read it during a grant):
      ssh ${TARGET} cat ${PASSF}
  * First backup: $([ "${FIRSTRUN}" = yes ] && echo 'done above' || echo 'runs on the timer, or force with: ssh '"${TARGET}"' /opt/skynet-ops/scripts/backup-restic.sh '"${LABEL}")
DONE
