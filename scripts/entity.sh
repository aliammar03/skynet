#!/usr/bin/env bash
# entity.sh — temporary source-compatible forwarder to the packaged Python entity functions.
# TIER: T1 — pure functions over authored conventions; no network, secrets, or writes.
# The remaining build-db caller sources this file during P8. Its shell logic is intentionally gone;
# P8B migrates that caller and P22 removes this compatibility entry.
_ENTITY_REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
_entity_python() {
  PYTHONPATH="${_ENTITY_REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}" \
    python3 -m skynet.entities "$@"
}

vmid_to_ip() { _entity_python vmid-to-ip "$1"; }
ip_to_vmid() { _entity_python ip-to-vmid "$1"; }
vlan_of_vmid() { _entity_python vlan-of-vmid "$1"; }
guest_id() { _entity_python guest-id "$1" "$2"; }
svc_id() { _entity_python svc-id "$1"; }
node_id() { _entity_python node-id "$1"; }
vhost_id() { _entity_python vhost-id "$1"; }
net_id() { _entity_python net-id "$1"; }

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  echo "entity.sh is a source-compatible forwarder to the packaged Python entity functions."
  echo "  vmid_to_ip 10015 = $(vmid_to_ip 10015)"
  echo "  guest_id 10015 vm-docker-dmz = $(guest_id 10015 vm-docker-dmz)"
  echo "  svc_id karakeep = $(svc_id karakeep)"
fi
