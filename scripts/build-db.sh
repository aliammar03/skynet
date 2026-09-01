#!/usr/bin/env bash
# build-db.sh — load inventory/*.json into a REBUILDABLE SQLite cache (.cache/inventory.db) so the
#   renderer and the agent can JOIN over entity keys instead of hand-rolling fuzzy IP joins in
#   jq/awk (SKY-018 P3, ADR 0003). Git stays truth; this DB is a throwaway cache (gitignored),
#   rebuilt from scratch each run — losing it costs one render.
# TIER: T1 — reads inventory/ + lab.json + derives guest IPs via entity.sh. No network, no writes
#   outside .cache/.
# USAGE: build-db.sh            # (re)build .cache/inventory.db
#   Override the binary for testing:  SQLITE3="nix shell nixpkgs#sqlite -c sqlite3" build-db.sh
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_DIR}"
# shellcheck source=scripts/entity.sh
source "${REPO_DIR}/scripts/entity.sh"

SQLITE3="${SQLITE3:-sqlite3}"
command -v jq >/dev/null || { echo "build-db: jq is required" >&2; exit 2; }
${SQLITE3} --version >/dev/null 2>&1 || { echo "build-db: sqlite3 not available (nixos-rebuild adds it)" >&2; exit 3; }

inv="${REPO_DIR}/inventory"; lab="${REPO_DIR}/lab.json"
db="${REPO_DIR}/.cache/inventory.db"
mkdir -p "${REPO_DIR}/.cache"
rm -f "${db}"                                   # rebuilt from scratch — idempotent
has() { [ -s "$1" ]; }
sq() { ${SQLITE3} "${db}" "$@"; }

# ── schema — one table per collected fact, plus the authored lab.json tables ──────────────────────
sq <<'SQL'
CREATE TABLE guests(entity_id TEXT, vmid INTEGER, name TEXT, node TEXT, status TEXT, template INTEGER, pool TEXT, ip TEXT);
CREATE TABLE pools(node TEXT, pool TEXT);
CREATE TABLE reservations(ip TEXT, host TEXT, mac TEXT, descr TEXT);
CREATE TABLE aliases(name TEXT, type TEXT, ip TEXT, nmembers INTEGER, descr TEXT);
CREATE TABLE dns_a(name TEXT, ip TEXT);
CREATE TABLE containers(project TEXT, host_label TEXT, hosted_on TEXT, state TEXT, image TEXT);
CREATE TABLE front_doors(alias TEXT, ip TEXT, proxy TEXT);
CREATE TABLE vlans(vlan INTEGER, name TEXT, slug TEXT);
CREATE TABLE backup_jobs(entity_id TEXT, kind TEXT);
CREATE TABLE netgear(entity_id TEXT, type TEXT, name TEXT, model TEXT, mac TEXT, ip TEXT, firmware TEXT, needs_upgrade INTEGER, connected INTEGER, clients INTEGER, poe_support INTEGER, site TEXT);
CREATE TABLE netports(switch TEXT, port INTEGER, name TEXT, profile TEXT, link INTEGER, poe INTEGER);
CREATE TABLE arp(ip TEXT, mac TEXT, hostname TEXT, intf TEXT, manufacturer TEXT, permanent INTEGER);
SQL

# helper: stream TSV on stdin into a table (\t-separated, matches the column order)
load() { ${SQLITE3} "${db}" -cmd ".mode tabs" ".import /dev/stdin $1"; }

# ── guests (both nodes) — entity-keyed, IP derived from the VMID (ADR 0001 via entity.sh) ─────────
for jf in "${inv}"/proxmox-*.json; do
  has "${jf}" || continue
  node="$(jq -r '(.nodes[]? | select(.type=="node") | .node) // .node // ""' "${jf}")"
  while IFS=$'\t' read -r vmid name status tmpl pool; do
    [ -n "${vmid}" ] || continue
    ip="$(vmid_to_ip "${vmid}" 2>/dev/null || true)"
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
      "$(guest_id "${vmid}" "${name}")" "${vmid}" "${name}" "${node}" "${status}" "${tmpl}" "${pool}" "${ip}"
  done < <(jq -r '.resources[]? | select(.type=="qemu" or .type=="lxc")
              | [.vmid, .name, .status, (.template//0), (.pool//"")] | @tsv' "${jf}") | load guests
  jq -r '.pools[]? | [(env.NODE // "'"${node}"'"), .poolid] | @tsv' "${jf}" | load pools
done

# ── firewall: reservations + host aliases (split to member IPs, with per-alias member count) ──────
fw="${inv}/firewall/firewall.json"
if has "${fw}"; then
  jq -r '.reservations[]? | select((.ip//"")|startswith("10.10."))
          | [.ip, (.host//""), (.mac//.hwaddr//""), (.descr//"")] | @tsv' "${fw}" | load reservations
  jq -r '.aliases[]? | select(.type=="host") | . as $a
          | ([$a.content // "" | split("\n")[] | select(test("^10\\.10\\.[0-9]+\\.[0-9]+$"))]) as $ips
          | ($ips|length) as $n | $ips[]
          | [$a.name, $a.type, ., $n, ($a.description//"")] | @tsv' "${fw}" | load aliases
fi

# ── DNS A records (nested per zone) ──────────────────────────────────────────────────────────────
dns="${inv}/dns-zones.json"
if has "${dns}"; then
  jq -r '.records[]?.records[]? | select(.type=="A")
          | select((.rData.ipAddress//"")|startswith("10.10."))
          | [.name, .rData.ipAddress] | @tsv' "${dns}" | load dns_a
fi

# ── containers (compose projects) → hosted_on guest via the lab.json host-label map ──────────────
for df in "${inv}"/docker-*.json; do
  has "${df}" || continue
  label="$(jq -r '.host // ""' "${df}")"
  gvmid="$(jq -r --arg l "${label}" '.docker_hosts.hosts[]? | select(.label==$l) | .vmid' "${lab}" 2>/dev/null)"
  gname="$(jq -r --arg l "${label}" '.docker_hosts.hosts[]? | select(.label==$l) | .guest' "${lab}" 2>/dev/null)"
  hosted="host:${label}?"; [ -n "${gvmid}" ] && [ "${gvmid}" != null ] && hosted="$(guest_id "${gvmid}" "${gname}")"
  jq -r --arg h "${label}" --arg e "${hosted}" '
      [.containers[]?.Labels | capture("com\\.docker\\.compose\\.project=(?<p>[^,]+)").p] | unique | .[]
      as $p | [$p, $h, $e] | @tsv' "${df}" \
    | while IFS=$'\t' read -r proj hl ho; do
        st="$(jq -r --arg p "${proj}" 'first(.containers[]? | select(.Labels|test("project="+$p+"(,|$)")) ) | .State // ""' "${df}")"
        img="$(jq -r --arg p "${proj}" 'first(.containers[]? | select(.Labels|test("project="+$p+"(,|$)")) ) | .Image // ""' "${df}")"
        printf '%s\t%s\t%s\t%s\t%s\n' "${proj}" "${hl}" "${ho}" "${st}" "${img}"
      done | load containers
done

# ── authored lab.json tables: front doors + VLAN vocabulary ──────────────────────────────────────
if has "${lab}"; then
  jq -r '.front_doors.aliases[]? | [.alias, .ip, (.proxy//"")] | @tsv' "${lab}" | load front_doors
  jq -r '.vlans.list[]? | [.vlan, .name, .slug] | @tsv' "${lab}" | load vlans
fi

# ── network gear (Omada estate, SKY-018 P4) → one row per device + one per switch port ───────────
ng="${inv}/network-gear.json"
if has "${ng}"; then
  jq -r '.devices[]? | [.entity_id, .type, .name, .model, .mac, .ip, .firmware,
           (if .needs_upgrade then 1 else 0 end), (if .connected then 1 else 0 end),
           (.clients//0), (if .poe.support then 1 else 0 end), (.site//"")] | @tsv' "${ng}" | load netgear
  jq -r '.devices[]? | select(.ports!=null) | .entity_id as $e | .ports[]?
           | [$e, .port, (.name//""), (.profile//""), (.link//0), (.poe//0)] | @tsv' "${ng}" | load netports
fi

# ── live OPNsense ARP neighbours (SKY-020: the live read gives observed PRESENCE the mirror can't) ─
# A genuinely new observed-truth source: which IP↔MAC is actually up right now, per interface. Lets
# the agent join intent (firewall aliases) against reality (who answered ARP). Keyed on IP.
opn="${inv}/opnsense.json"
if has "${opn}"; then
  jq -r '.arp[]? | [.ip, .mac, (.hostname//""), (.intf//""), (.manufacturer//""), (if .permanent then 1 else 0 end)] | @tsv' "${opn}" | load arp
fi

# ── backup jobs (restic/PBS) if a collector recorded them — keyed to guest where resolvable ──────
bkp="${inv}/backup-jobs.json"
if has "${bkp}"; then
  jq -r '.[]? | [(.entity_id//""), (.kind//"")] | @tsv' "${bkp}" 2>/dev/null | load backup_jobs || true
fi

n_guests="$(sq 'SELECT COUNT(*) FROM guests;')"
n_hosts="$(sq "SELECT COUNT(DISTINCT ip) FROM (SELECT ip FROM guests WHERE ip<>'' UNION SELECT ip FROM reservations UNION SELECT ip FROM aliases UNION SELECT ip FROM dns_a);")"
echo "build-db: ${db} — ${n_guests} guests, ${n_hosts} distinct IPs, $(sq 'SELECT COUNT(*) FROM containers;') containers"
