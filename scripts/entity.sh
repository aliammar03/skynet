#!/usr/bin/env bash
# entity.sh — the L0 identity helper (SKY-018 P1). Sourceable: gives every thing the agent reasons
#   about a stable `<class>/<key>` ID, and derives a guest's IP from its VMID (ADR 0001) and back.
# TIER: T1 — pure functions over conventions + repo data. No network, no secrets, no writes.
# USAGE:  source scripts/entity.sh   then call the functions below. Nothing runs on source.
#   guest:  vmid_to_ip 10015        -> 10.10.100.15      ip_to_vmid 10.10.100.15 -> 10015 (canonical)
#           guest_id 10015 vm-docker-dmz -> guest/docker-dmz-10015
#   svc:    svc_id karakeep         -> svc/karakeep
#   others: node_id server-proxmox-core / vhost_id pbs.aliammar.net / net_id ap-omada-downstairs
# The one grammar lives in docs/conventions/naming.md; this script is its executable form.
# shellcheck shell=bash

# The declared VLAN set + slugs (docs/conventions/naming.md). The slug is decoration in an entity
# ID; the VMID is identity. VLAN 40 exists in firewall nets but hosts no guest and has no slug.
_ENTITY_VLANS="10 20 30 50 60 70 80 90 100"
_entity_vlan_slug() {
  case "$1" in
    10) echo lan;;   20) echo servers;; 30) echo iot;;      50) echo mgmt;;
    60) echo admin;; 70) echo netsvc;;  80) echo identity;; 90) echo ops;;  100) echo dmz;;
    *)  echo "vlan${1}";;   # unknown VLAN: legible placeholder, never silently blank
  esac
}
_entity_is_declared_vlan() { case " ${_ENTITY_VLANS} " in *" $1 "*) return 0;; *) return 1;; esac; }

# vmid_to_ip <vmid> -> 10.10.<vlan>.<octet>   (ADR 0001: VMID = VLAN + 2-digit last octet)
#   Parsing rule (naming.md): octet = last two digits; the remaining prefix must match the declared
#   VLAN set in EXACTLY ONE of two forms — canonical (VLAN written in full: 10015=VLAN100) or legacy
#   (trailing zero dropped: 240=VLAN20). Return codes: 0 ok (prints IP) · 1 off-convention (no match)
#   · 2 ambiguous (both forms declared — only the `10xx` prefix, VLAN 10 vs VLAN 100; prints nothing).
vmid_to_ip() {
  local vmid="$1" octet prefix cands=() vlan
  [[ "${vmid}" =~ ^[0-9]+$ ]] || return 1
  octet=$(( vmid % 100 ))
  prefix=$(( vmid / 100 ))
  _entity_is_declared_vlan "${prefix}"        && cands+=("${prefix}")       # canonical: prefix IS the VLAN
  _entity_is_declared_vlan "$(( prefix * 10 ))" && cands+=("$(( prefix * 10 ))") # legacy: prefix*10 is the VLAN
  case "${#cands[@]}" in
    1) vlan="${cands[0]}"; echo "10.10.${vlan}.${octet}"; return 0;;
    0) return 1;;
    *) return 2;;
  esac
}

# ip_to_vmid <10.10.vlan.octet> -> canonical VMID (the recommended form). The inverse is only
#   well-defined toward canonical; a legacy guest keeps its own number and is not re-derived here.
ip_to_vmid() {
  local ip="$1" vlan octet
  [[ "${ip}" =~ ^10\.10\.([0-9]+)\.([0-9]+)$ ]] || return 1
  vlan="${BASH_REMATCH[1]}"; octet="${BASH_REMATCH[2]}"
  _entity_is_declared_vlan "${vlan}" || return 1
  echo $(( vlan * 100 + octet ))
}

# vlan_of_vmid <vmid> -> the VLAN number (or empty + rc1 off-convention, rc2 ambiguous). Handy when
#   the caller wants the VLAN/slug without the address.
vlan_of_vmid() {
  local vmid="$1" prefix cands=()
  [[ "${vmid}" =~ ^[0-9]+$ ]] || return 1
  prefix=$(( vmid / 100 ))
  _entity_is_declared_vlan "${prefix}"          && cands+=("${prefix}")
  _entity_is_declared_vlan "$(( prefix * 10 ))" && cands+=("$(( prefix * 10 ))")
  case "${#cands[@]}" in 1) echo "${cands[0]}"; return 0;; 0) return 1;; *) return 2;; esac
}

# guest_id <vmid> <guest-name> -> guest/<role>-<vlan-slug>-<vmid>
#   role = name minus vm-/lxc- prefix; the VLAN slug is appended ONLY if the role does not already
#   end with it (no docker-dmz-dmz). The VMID is last and authoritative. Off-convention/ambiguous
#   VMIDs still get an ID — with the slug omitted — because identity is the number, not the slug.
guest_id() {
  local vmid="$1" name="$2" role slug vlan
  role="${name#vm-}"; role="${role#lxc-}"
  if vlan="$(vlan_of_vmid "${vmid}")"; then
    slug="$(_entity_vlan_slug "${vlan}")"
    if [[ "${role}" == *"-${slug}" || "${role}" == "${slug}" ]]; then
      echo "guest/${role}-${vmid}"
    else
      echo "guest/${role}-${slug}-${vmid}"
    fi
  else
    echo "guest/${role}-${vmid}"   # off-convention or ambiguous: no trustworthy slug to append
  fi
}

svc_id()   { echo "svc/$1"; }
node_id()  { echo "node/$1"; }
vhost_id() { echo "vhost/$1"; }
net_id()   { echo "net/$1"; }

# If executed rather than sourced, print a tiny self-check so `bash scripts/entity.sh` is not silent.
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  echo "entity.sh is a sourceable library — source it, don't run it. Quick check:"
  echo "  vmid_to_ip 10015 = $(vmid_to_ip 10015)"
  echo "  guest_id 10015 vm-docker-dmz = $(guest_id 10015 vm-docker-dmz)"
  echo "  svc_id karakeep = $(svc_id karakeep)"
fi
