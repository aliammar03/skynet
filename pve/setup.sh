#!/bin/sh
# The Proxmox nodes' observability (skynetv2.md → P5 → Wider eyes), run by Ali as root on each node
# (README.md): Debian's node-exporter with its SMART and NVMe timers, and the journal's upload to
# docker-admin's vlagent, with journald's flood cap and the heartbeat, as on PBS. Re-runnable: it
# shows each file's change as it installs it.
set -eu
cd "$(dirname "$0")/etc"

# Installs etc/<path> at /etc/<path>, first showing what it changes (none of these holds a secret).
put() { # <path>
  if [ -e "/etc/$1" ]; then diff -u "/etc/$1" "$1" || true; else echo "new: /etc/$1"; fi
  install -D -o root -g root -m 644 "$1" "/etc/$1"
}

find . -type f | sort | while read -r f; do
  put "${f#./}"
done

export DEBIAN_FRONTEND=noninteractive
# A repository the node can't read (PVE's enterprise one, without a subscription) fails the update
# but not the install below, which then uses the lists it has.
apt-get update -q || echo "setup: apt-get update had errors (above)" >&2
# node-exporter, its textfile collectors (SMART, NVMe, pending updates; each timer skips hardware the
# node lacks), and the journal's upload.
apt-get install -qy prometheus-node-exporter prometheus-node-exporter-collectors smartmontools \
  nvme-cli systemd-journal-remote
systemctl daemon-reload
# Restarted every run, so a changed drop-in applies. The package doesn't enable the upload.
systemctl enable systemd-journal-upload
systemctl restart systemd-journald prometheus-node-exporter systemd-journal-upload
systemctl enable --now log-heartbeat.timer

# The upload waits ("activating") while docker-admin's vlagent is unreachable.
systemctl is-active prometheus-node-exporter systemd-journal-upload || true
systemctl list-timers --no-pager 'prometheus-node-exporter-*' log-heartbeat.timer
