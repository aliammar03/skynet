#!/bin/sh
# PBS's setup after Proxmox's installer, run by the agent as root (README.md → Install): updates
# without a subscription, the guest agent, the datastore on Unraid, node-exporter and the journal's
# upload (P5), and etc/ copied into /etc.
# Re-runnable; a rebuild runs it the same way and reuses the datastore as it is on Unraid. From ops:
#   tar -C pbs -c setup.sh etc | ssh root@10.10.20.40 'rm -rf /root/pbs && mkdir /root/pbs &&
#     tar -C /root/pbs -x && sh /root/pbs/setup.sh; s=$?; rm -r /root/pbs; exit $s'
set -eu
cd "$(dirname "$0")/etc"
store=/mnt/datastore/skynet

# Installs etc/<path> at /etc/<path>, first showing what it changes (none of these holds a secret).
put() { # <path> <owner:group> <mode>
  if [ -e "/etc/$1" ]; then diff -u "/etc/$1" "$1" || true; else echo "new: /etc/$1"; fi
  install -D -o "${2%:*}" -g "${2#*:}" -m "$3" "$1" "/etc/$1"
}

# The OS part: apt sources, resolv.conf, the datastore's mount units, node-exporter's and the
# upload's settings.
find . -path ./proxmox-backup -prune -o -type f -print | while read -r f; do
  put "${f#./}" root:root 644
done
export DEBIAN_FRONTEND=noninteractive
apt-get update -q
apt-get install -qy qemu-guest-agent nfs-common
# For docker-admin: node-exporter (VictoriaMetrics scrapes it) and the journal's upload to vlagent;
# etc/systemd/ holds their settings. Not node-exporter's recommended extra collectors: their timers
# probe hardware a VM lacks.
apt-get install -qy --no-install-recommends prometheus-node-exporter systemd-journal-remote
apt-get full-upgrade -qy -o Dpkg::Options::=--force-confdef -o Dpkg::Options::=--force-confold
systemctl start qemu-guest-agent
systemctl daemon-reload
systemctl enable --now mnt-datastore-skynet.automount
# Restarted every run, so a changed drop-in applies. The package doesn't enable the upload.
systemctl enable systemd-journal-upload
systemctl restart prometheus-node-exporter systemd-journal-upload

# The datastore: new on an empty share, reused (as-is) on one that has it.
ls "$store" >/dev/null
if ! findmnt -t nfs,nfs4 "$store" >/dev/null; then
  echo "setup: $store is not Unraid's share" >&2
  exit 1
fi
if ! proxmox-backup-manager datastore show skynet >/dev/null 2>&1; then
  reuse=false
  [ -d "$store/.chunks" ] && reuse=true
  # Root makes a new datastore, then chowns it to `backup`: the export must not squash root.
  if [ "$reuse" = false ] && ! (touch "$store/.probe" && chown backup "$store/.probe"); then
    echo "setup: root can't chown on $store; Unraid's export needs no_root_squash" >&2
    exit 1
  fi
  rm -f "$store/.probe"
  proxmox-backup-manager datastore create skynet "$store" --reuse-datastore "$reuse"
fi
# Namespaces, through the API (JSON out: its text table panics on this call's result).
for ns in core network; do
  [ -d "$store/ns/$ns" ] || proxmox-backup-debug api create \
    /admin/datastore/skynet/namespace --name "$ns" --output-format json
done

# PBS's own config: jobs, users, ACLs. The tokens arrive without secrets; Ali regenerates them.
for f in proxmox-backup/*; do put "$f" root:backup 640; done
systemctl reload-or-restart proxmox-backup proxmox-backup-proxy

proxmox-backup-manager versions
# The upload waits ("activating") while docker-admin's vlagent is unreachable.
systemctl is-active prometheus-node-exporter systemd-journal-upload || true
proxmox-backup-manager datastore list
proxmox-backup-manager prune-job list
proxmox-backup-manager verify-job list
proxmox-backup-manager acl list
