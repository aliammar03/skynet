#!/usr/bin/env bash
# entity-test.sh — unit tests for the L0 derivation (SKY-018 P1). Asserts scripts/entity.sh against
#   the known-good set, so the convention has a CHECKER, not just a writer (SKY-018 thesis).
# TIER: T1 — sources the helper, runs assertions. No network, no writes. Run: bash tests/entity-test.sh
set -uo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_DIR}"
# shellcheck source=scripts/entity.sh
source "${REPO_DIR}/scripts/entity.sh"

pass=0; fail=0
ok()   { printf '  \342\234\223 %s\n' "$1"; pass=$(( pass + 1 )); }
bad()  { printf '  \342\234\227 %s\n' "$1" >&2; fail=$(( fail + 1 )); }
eq()   { if [ "$2" = "$3" ]; then ok "$1"; else bad "$1 — expected [$3], got [$2]"; fi; }
# rc <label> <expected-rc> <fn> <args...> : assert a function's exit code
rc()   { local l="$1" want="$2"; shift 2; "$@" >/dev/null 2>&1; local got=$?; eq "${l}" "${got}" "${want}"; }

echo "== vmid_to_ip: canonical form (VLAN in full) =="
eq "10015 -> 10.10.100.15 (docker-dmz)" "$(vmid_to_ip 10015)" "10.10.100.15"
eq "9090  -> 10.10.90.90  (skynet-ops)" "$(vmid_to_ip 9090)"  "10.10.90.90"
eq "2020  -> 10.10.20.20  (unraid)"     "$(vmid_to_ip 2020)"  "10.10.20.20"
eq "5001  -> 10.10.50.1   (opnsense)"   "$(vmid_to_ip 5001)"  "10.10.50.1"

echo "== vmid_to_ip: legacy form (trailing zero dropped) =="
eq "240 -> 10.10.20.40 (HOST_PBS)"          "$(vmid_to_ip 240)" "10.10.20.40"
eq "635 -> 10.10.60.35 (HOST_PROXY_ADMIN)"  "$(vmid_to_ip 635)" "10.10.60.35"
eq "751 -> 10.10.70.51 (tdns-core)"         "$(vmid_to_ip 751)" "10.10.70.51"
eq "837 -> 10.10.80.37 (HOST_AUTHENTIK)"    "$(vmid_to_ip 837)" "10.10.80.37"
eq "525 -> 10.10.50.25 (HOST_OMADA)"        "$(vmid_to_ip 525)" "10.10.50.25"

echo "== vmid_to_ip: the edge cases =="
# 999 predates the convention but still PARSES as legacy VLAN 90 (9 -> 90), octet 99. It is not
# off-convention — it derives cleanly to an address the firewall simply does not know, which is why
# the audit flags it running-unmapped rather than off-convention.
eq  "999 -> 10.10.90.99 (legacy VLAN 90, valid but unmapped)" "$(vmid_to_ip 999)" "10.10.90.99"
rc  "4001 is off-convention (rc1, VLAN 40 hosts no guest)"    1 vmid_to_ip 4001
rc  "1035 is ambiguous 10xx (rc2, VLAN10 vs VLAN100)"        2 vmid_to_ip 1035

echo "== ip_to_vmid: inverse toward the canonical form =="
eq "10.10.100.15 -> 10015" "$(ip_to_vmid 10.10.100.15)" "10015"
eq "10.10.90.90  -> 9090"  "$(ip_to_vmid 10.10.90.90)"  "9090"

echo "== guest_id: <role>-<vlan>-<vmid>, slug omitted when the role already ends with it =="
eq "docker-dmz: no -dmz-dmz stutter"        "$(guest_id 10015 vm-docker-dmz)"        "guest/docker-dmz-10015"
eq "skynet-ops: no -ops-ops stutter"        "$(guest_id 9090 vm-skynet-ops)"         "guest/skynet-ops-9090"
eq "authentik: slug appended (identity)"    "$(guest_id 837 lxc-authentik)"          "guest/authentik-identity-837"
eq "technitium-core: -core is node, kept"   "$(guest_id 751 lxc-technitium-core)"    "guest/technitium-core-netsvc-751"
eq "999 legacy VLAN 90: role ends -ops, omit"  "$(guest_id 999 vm-skynet-ops)"       "guest/skynet-ops-999"
eq "off-convention 4001: no slug to append"    "$(guest_id 4001 vm-mystery)"         "guest/mystery-4001"
eq "no vm-/lxc- prefix (debian)"            "$(guest_id 101 debian)"                 "guest/debian-lan-101"

echo "== svc_id / node_id / vhost_id / net_id: key passthrough =="
eq "svc"   "$(svc_id karakeep)"                "svc/karakeep"
eq "node"  "$(node_id server-proxmox-core)"    "node/server-proxmox-core"
eq "vhost" "$(vhost_id pbs.aliammar.net)"      "vhost/pbs.aliammar.net"
eq "net"   "$(net_id ap-omada-downstairs)"     "net/ap-omada-downstairs"

echo "== service audit: every running compose project has a compose/ dir in git =="
# arcane-manager was the one undeclared project (running outside the GitOps loop); it is now captured
# as a bootstrap component (compose/arcane-manager/, relocation pending SKY-019), so the hole is closed.
mapfile -t dirs < <(find compose -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort)
running="$(jq -r '.containers[]?.Labels | capture("com\\.docker\\.compose\\.project=(?<p>[^,]+)") | .p' \
             inventory/docker-*.json 2>/dev/null | sort -u)"
undeclared=0; undeclared_names=""
while IFS= read -r p; do
  [ -n "${p}" ] || continue
  if ! printf '%s\n' "${dirs[@]}" | grep -qxF "${p}"; then
    undeclared=$(( undeclared + 1 )); undeclared_names="${undeclared_names} ${p}"
  fi
done <<< "${running}"
eq "no running project lacks a compose/ dir" "${undeclared}" "0"
[ "${undeclared}" -ne 0 ] && echo "     undeclared:${undeclared_names}" >&2
if printf '%s\n' "${dirs[@]}" | grep -qxF arcane-manager; then
  ok "arcane-manager is now declared (compose/arcane-manager/ exists)"
else
  bad "compose/arcane-manager/ should exist (bootstrap capture, SKY-019)"
fi

echo "== guest audit: the OpenTofu template (VMID 9000) is flagged template, never stale =="
tmpl9000="$(jq -r '.resources[]? | select(.vmid==9000) | .template' inventory/proxmox-*.json 2>/dev/null | head -1)"
eq "VMID 9000 carries template=1 in inventory" "${tmpl9000}" "1"
# capture first: the audit legitimately exits non-zero while holes exist, and pipefail would
# otherwise mask grep's result with the audit's exit code.
audit_out="$(bin/ops entities 2>/dev/null || true)"
if printf '%s\n' "${audit_out}" | grep -qE 'ubuntu-2404-base.*template'; then
  ok "audit buckets the 9000 template as 'template', not 'stale'"
else
  bad "audit did not classify VMID 9000 as a template (it must never read as a stale-destroy proposal)"
fi

echo "== P2: authored judgment data lives in lab.json / invariants.json, not in the renderer =="
eq "lab.json vlans.list has 9 entries"        "$(jq '.vlans.list | length' lab.json)" "9"
eq "VLAN 10 name is 'Trusted LAN' (not swapped)" "$(jq -r '.vlans.list[]|select(.vlan==10)|.name' lab.json)" "Trusted LAN"
eq "VLAN 10 slug is 'lan'"                     "$(jq -r '.vlans.list[]|select(.vlan==10)|.slug' lab.json)" "lan"
eq "lab.json declares the front-door alias set" "$(jq '.front_doors.aliases | length' lab.json)" "2"
eq "invariants.json declares the VLAN set (10..100)" "$(jq '.entity_conventions.declared_vlans | length' invariants.json)" "9"
if grep -q 'vlans.list' scripts/render-docs.sh && ! grep -q 'Trusted LAN' scripts/render-docs.sh; then
  ok "render-docs.sh reads VLAN names from lab.json, holds no hardcoded name map"
else
  bad "render-docs.sh should read lab.json (grep vlans.list) and NOT hardcode VLAN names (grep 'Trusted LAN')"
fi
# The 4th invariant law (check-invariants.sh) rejects a running off-convention guest by reusing the
# classifier below: an undeclared-VLAN VMID gets no valid address and cannot be "mapped", so it lands
# in running-unmapped and fails the gate. Assert the classifier's rejection here (the full end-to-end
# gate failure is exercised by check-invariants against inventory, not re-driven from this unit test).
rc "classifier rejects 4242 (VLAN 42 undeclared) as off-convention" 1 vmid_to_ip 4242

echo "== P4: network-gear collector (Omada, SKY-018 P4) =="
# graceful degradation — a missing credential must exit 0, never error, like every collector
( unset OMADA_HOST OMADA_USER OMADA_PASS OMADA_CACERT OMADA_PORT OMADA_SNI
  OMADA_SECRET_FILE=/nonexistent/omada.env ./scripts/collect-network-gear.sh >/dev/null 2>&1 )
eq "collect-network-gear degrades to exit 0 without creds" "$?" "0"
if [ -s inventory/network-gear.json ]; then
  eq "every net device carries a net/ entity id" \
     "$(jq '[.devices[]?|select((.entity_id//"")|startswith("net/")|not)]|length' inventory/network-gear.json)" "0"
  eq "controller version is recorded" \
     "$(jq -r '.controller.version|type' inventory/network-gear.json)" "string"
else
  ok "inventory/network-gear.json absent — estate assertions skipped (collector idle)"
fi

echo "== P3: the SQLite join cache (skipped where sqlite3 isn't installed yet — pre nixos-rebuild) =="
if command -v sqlite3 >/dev/null 2>&1; then
  if ./scripts/build-db.sh >/dev/null 2>&1; then
    db=".cache/inventory.db"
    q() { sqlite3 "${db}" "$1"; }
    eq "guests table row count == proxmox guest count" \
       "$(q 'SELECT COUNT(*) FROM guests;')" \
       "$(jq -s '[.[].resources[]?|select(.type=="qemu" or .type=="lxc")]|length' inventory/proxmox-*.json)"
    eq "every running guest has a derived IP in the DB" "$(q "SELECT COUNT(*) FROM guests WHERE status='running' AND ip='';")" "0"
    # the host-map join produces rows and keys guests to their entity id
    rows="$(sqlite3 "${db}" -cmd '.mode tabs' ".read scripts/sql/host-map.sql" | wc -l)"
    [ "${rows}" -gt 0 ] && ok "host-map.sql returns ${rows} rows" || bad "host-map.sql returned no rows"
    eq "docker-dmz guest is entity-keyed in the host map" \
       "$(sqlite3 "${db}" -cmd '.mode tabs' ".read scripts/sql/host-map.sql" | awk -F'\t' '$1=="10.10.100.15"{print $4}')" \
       "guest/docker-dmz-10015"
    # vhosts resolve to a front door (SKY-015 fix); the wildcard must be one of them
    eq "vhosts.sql flags *.aliammar.net as a front-door vhost" \
       "$(sqlite3 "${db}" -cmd '.mode tabs' ".read scripts/sql/vhosts.sql" | awk -F'\t' '$1=="*.aliammar.net"{print $3}')" \
       "caddy-apps"
    # P4: the Omada estate loads into the cache, one netgear row per collected device
    if [ -s inventory/network-gear.json ]; then
      eq "netgear rows == devices collected" \
         "$(q 'SELECT COUNT(*) FROM netgear;')" \
         "$(jq '.devices|length' inventory/network-gear.json)"
    fi
    rm -f "${db}"
  else
    bad "build-db.sh failed with sqlite3 present"
  fi
else
  ok "sqlite3 not installed — P3 DB tests skipped (they run in CI + post nixos-rebuild)"
fi

echo
echo "entity-test: ${pass} passed, ${fail} failed"
[ "${fail}" -eq 0 ]
