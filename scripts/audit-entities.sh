#!/usr/bin/env bash
# audit-entities.sh — the L0 audit (SKY-018 P1). Derives every entity's ID + address from the
#   convention, then classifies each against observed truth: matched / stale / running-unmapped /
#   exception. The point is the LAST bucket — a *running* thing that no view knows about is a hole.
# TIER: T1 — reads inventory/, invariants.json, lab.json, compose/. No network, no writes.
# USAGE:  bin/ops entities            (or: scripts/audit-entities.sh)
#   Exit 0 = every running entity is mapped or a declared exception.
#   Exit 1 = at least one RUNNING entity is neither mapped nor excepted (a real hole to resolve).
#   Exit 2 = a required input is missing.
# Proposals, not actions: the stale + undeclared lists are for a human/journal to triage. This
# script never destroys, stops, or edits anything (naming.md, SKY-018 §Phase 1).
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_DIR}"
# shellcheck source=scripts/entity.sh
source "${REPO_DIR}/scripts/entity.sh"

command -v jq >/dev/null || { echo "audit-entities: jq is required" >&2; exit 2; }
INV="invariants.json"; LAB="lab.json"
[ -r "${INV}" ] || { echo "audit-entities: ${INV} not found" >&2; exit 2; }

hole=0
sym_ok=$'\342\234\223'; sym_x=$'\342\234\227'; sym_warn=$'\342\232\240'
# $1 may lead with a 3-byte glyph (✓/✗/⚠) + space; pad the id column by DISPLAY width, not bytes,
# so glyph and plain rows line up. Second column is wide enough for a HOSTED_ON entity id.
row() {
  local id="$1" disp=${#1} pad
  case "${id}" in "${sym_ok} "*|"${sym_x} "*|"${sym_warn} "*) disp=$(( disp - 2 ));; esac
  pad=$(( 40 - disp )); [ "${pad}" -lt 1 ] && pad=1
  printf '  %s%*s %-22s %-11s %-16s %s\n' "${id}" "${pad}" "" "$2" "$3" "$4" "$5"
}

# ── observed truth: the set of IPs the firewall knows (host aliases + DHCP reservations) ─────────
# A guest is "mapped" when its derived address appears here — the same host-fact join the renderer
# does, but keyed on the entity, not guessed from an IP-priority ladder.
mapfile -t FW_IPS < <(
  { jq -r '.aliases[]? | select(.type=="host") | .content' inventory/firewall/firewall.json 2>/dev/null
    jq -r '.reservations[]? | (.ip // .address // empty)'  inventory/firewall/firewall.json 2>/dev/null
  } | tr ' \n' '\n\n' | grep -E '^10\.10\.' | sort -u
)
is_mapped() { local ip="$1"; [ -n "${ip}" ] || return 1; printf '%s\n' "${FW_IPS[@]}" | grep -qxF "${ip}"; }

# ── live PRESENCE: the OPNsense live read (SKY-020) gives who actually answered ARP right now —
# observed presence the mirror's config can't. Used as a LIVENESS ANNOTATION only (never a mapping
# source), so the 4th-law pass/fail semantics are unchanged. Silent when there's no ARP data.
mapfile -t ARP_IPS < <(jq -r '.arp[]? | .ip // empty' inventory/opnsense.json 2>/dev/null | grep -E '^10\.10\.' | sort -u)
HAVE_ARP=0; [ "${#ARP_IPS[@]}" -gt 0 ] && HAVE_ARP=1
is_present() { local ip="$1"; [ -n "${ip}" ] || return 1; printf '%s\n' "${ARP_IPS[@]}" | grep -qxF "${ip}"; }
# liveness marker for a mapped guest: live ✓ if answering ARP, ⚠ ARP-silent if not (possibly down).
live_mark() { [ "${HAVE_ARP}" = 1 ] || return 0
  if is_present "$1"; then printf '%s live (ARP)' "${sym_ok}"; else printf '%s ARP-silent' "${sym_warn}"; fi; }

# declared exceptions: excluded_guests today; entity_conventions.exceptions once P2 adds it
mapfile -t EXCEPTIONS < <(
  { jq -r '.excluded_guests.guests[]?.vmid' "${INV}" 2>/dev/null
    jq -r '.entity_conventions.exceptions[]?.vmid' "${INV}" 2>/dev/null
  } | grep -E '^[0-9]+$' | sort -un
)
is_exception() { local v="$1"; printf '%s\n' "${EXCEPTIONS[@]}" | grep -qxF "${v}"; }

# ── L0 audit: guests ────────────────────────────────────────────────────────────────────────────
echo "== entity audit :: guest (VMID -> IP, ADR 0001) =="
row "ENTITY ID" "ADDRESS" "STATUS" "BUCKET" "NOTE"
declare -i g_match=0 g_stale=0 g_hole=0 g_exc=0 g_tmpl=0
while IFS=$'\t' read -r vmid name status tmpl; do
  [ -n "${vmid}" ] || continue
  id="$(guest_id "${vmid}" "${name}")"

  # A template is stopped-by-design and has no firewall/DNS identity by design — never a hole,
  # never a stale-destroy proposal. It is a declared clone source (e.g. tofu/template-*.tf), so
  # classify it on its own before the mapped/stale/hole logic runs.
  if [ "${tmpl}" = "1" ]; then
    g_tmpl+=1
    row "${id}" "$(vmid_to_ip "${vmid}" 2>/dev/null || echo '—')" "template" "template" "clone source — keep; never destroy as stale"
    continue
  fi
  # derive address; resolve the one ambiguous prefix (10xx) via the fact set
  addr=""; note=""
  if ip="$(vmid_to_ip "${vmid}")"; then
    addr="${ip}"
  else
    rc=$?
    if [ "${rc}" -eq 2 ]; then
      # ambiguous: try both candidate IPs, keep whichever the firewall knows
      octet=$(( vmid % 100 )); p=$(( vmid / 100 ))
      for cand in "10.10.${p}.${octet}" "10.10.$(( p * 10 )).${octet}"; do
        if is_mapped "${cand}"; then addr="${cand}"; note="ambiguous VMID, resolved by firewall fact"; break; fi
      done
      [ -n "${addr}" ] || note="ambiguous VMID (10xx), no fact to resolve"
    else
      note="off-convention VMID"
    fi
  fi

  if is_exception "${vmid}"; then
    bucket="exception"; g_exc+=1
    row "${id}" "${addr:-—}" "${status}" "${bucket}" "declared T3 (invariants.json)"
  elif [ -n "${addr}" ] && is_mapped "${addr}" && [ "${status}" = running ]; then
    bucket="matched"; g_match+=1
    lv="$(live_mark "${addr}")"
    row "${sym_ok} ${id}" "${addr}" "${status}" "${bucket}" "${note:+${note}; }${lv}"
  elif [ "${status}" != running ]; then
    bucket="stale"; g_stale+=1
    # a stopped guest still holding a live firewall alias is a louder cleanup target
    is_mapped "${addr}" && note="${note:+${note}; }${sym_warn} still holds firewall alias ${addr}"
    row "${id}" "${addr:-—}" "${status}" "${bucket}" "${note:-cleanup proposal}"
  else
    bucket="running-unmapped"; g_hole+=1; hole=1
    pn=""; [ "${HAVE_ARP}" = 1 ] && is_present "${addr}" && pn="${sym_warn} present in ARP (live, unaliased); "
    row "${sym_x} ${id}" "${addr:-—}" "${status}" "${bucket}" "${note:+${note}; }${pn}no firewall/DNS host fact"
  fi
done < <(jq -r '.resources[]? | select(.type=="qemu" or .type=="lxc") | "\(.vmid)\t\(.name)\t\(.status)\t\(.template // 0)"' inventory/proxmox-*.json 2>/dev/null | sort -n)
echo "  ── guests: ${g_match} matched · ${g_stale} stale · ${g_hole} running-unmapped · ${g_exc} exception · ${g_tmpl} template"
echo

# ── L0 audit: services (compose project <-> compose/ dir), with the hosted_on edge ───────────────
echo "== entity audit :: svc (compose project name) =="
row "ENTITY ID" "HOSTED_ON" "STATUS" "BUCKET" "NOTE"
declare -i s_match=0 s_hole=0 s_stopped=0
# running projects observed on every docker host, with the host label carried alongside
running_tsv="$(
  for f in inventory/docker-*.json; do
    [ -e "${f}" ] || continue
    label="$(jq -r '.host // "?"' "${f}")"
    jq -r --arg h "${label}" '.containers[]?.Labels
      | capture("com\\.docker\\.compose\\.project=(?<p>[^,]+)") | "\(.p)\t\($h)"' "${f}"
  done | sort -u
)"
# resolve a docker host label -> guest id via lab.json (never string-munge the vm- prefix)
hosted_on() {
  local label="$1" vmid gname
  vmid="$(jq -r --arg l "${label}" '.docker_hosts.hosts[]? | select(.label==$l) | .vmid' "${LAB}" 2>/dev/null)"
  gname="$(jq -r --arg l "${label}" '.docker_hosts.hosts[]? | select(.label==$l) | .guest' "${LAB}" 2>/dev/null)"
  if [ -n "${vmid}" ] && [ "${vmid}" != null ]; then guest_id "${vmid}" "${gname}"; else echo "host:${label}?"; fi
}
mapfile -t COMPOSE_DIRS < <(find compose -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort)
has_dir() { local p="$1"; printf '%s\n' "${COMPOSE_DIRS[@]}" | grep -qxF "${p}"; }

declare -A SEEN_PROJECT
while IFS=$'\t' read -r proj label; do
  [ -n "${proj}" ] || continue
  SEEN_PROJECT["${proj}"]=1
  edge="$(hosted_on "${label}")"
  if has_dir "${proj}"; then
    bucket="matched"; s_match+=1
    row "${sym_ok} $(svc_id "${proj}")" "${edge}" "running" "${bucket}" ""
  else
    bucket="running-unmapped"; s_hole+=1; hole=1
    row "${sym_x} $(svc_id "${proj}")" "${edge}" "running" "${bucket}" "no compose/${proj}/ in git — deployed outside the GitOps loop"
  fi
done <<< "${running_tsv}"
# compose dirs with no running project: informational (intentionally stopped, not a hole)
for d in "${COMPOSE_DIRS[@]}"; do
  [ -n "${SEEN_PROJECT[$d]:-}" ] && continue
  s_stopped+=1
  row "$(svc_id "${d}")" "—" "not-running" "declared-idle" "compose/${d}/ in git, no running project"
done
echo "  ── services: ${s_match} matched · ${s_hole} running-unmapped · ${s_stopped} declared-idle"
echo

# ── other classes: nodes are collected; vhost/net await their collectors (P5/P4) ─────────────────
echo "== entity audit :: node =="
while IFS= read -r n; do [ -n "${n}" ] && row "$(node_id "${n}")" "—" "—" "matched" "Proxmox node"; done \
  < <(jq -r '.nodes[]? | select(.type=="node") | .node' inventory/proxmox-*.json 2>/dev/null | sort -u)
echo "  (vhost: awaits the Caddy route collector, SKY-018 P5)"
echo

# ── net class: the Omada switch/AP estate (SKY-018 P4). INFORMATIONAL — a device the firewall's
#    INFRASTRUCTURE aliases don't list is drift worth surfacing, but not a CI-failing hole: net
#    devices aren't guests, and the 4th law (check-invariants) governs guests + services only.
echo "== entity audit :: net (Omada estate) =="
if [ -r inventory/network-gear.json ] && [ "$(jq '.devices|length' inventory/network-gear.json 2>/dev/null || echo 0)" -gt 0 ]; then
  declare -i n_match=0 n_unlisted=0
  while IFS=$'\t' read -r nid ip typ conn; do
    [ -n "${nid}" ] || continue
    st="$([ "${conn}" = "true" ] && echo connected || echo offline)"
    if is_mapped "${ip}"; then
      row "${nid}" "${ip}" "${st}" "matched" "${typ} in firewall estate alias"; n_match+=1
    else
      row "${sym_warn} ${nid}" "${ip}" "${st}" "unlisted" "${typ} not in a firewall INFRASTRUCTURE alias — drift"; n_unlisted+=1
    fi
  done < <(jq -r '.devices[]? | [.entity_id, .ip, .type, .connected] | @tsv' inventory/network-gear.json)
  echo "  ── net: ${n_match} matched · ${n_unlisted} unlisted-in-firewall (informational, not a hole)"
else
  echo "  (no inventory/network-gear.json yet — run scripts/collect-network-gear.sh with Omada read creds)"
fi
echo

if [ "${hole}" -ne 0 ]; then
  echo "audit-entities: ${sym_x} running entities with no home — resolve each (bring into a view, or declare an exception with a why)." >&2
  exit 1
fi
echo "audit-entities: ${sym_ok} every running entity is mapped or a declared exception."
