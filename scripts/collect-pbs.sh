#!/usr/bin/env bash
# collect-pbs.sh — T1 read-only snapshot of Proxmox Backup Server → inventory/pbs.json
#
# Reports the datastores AND their backup CONTENT — per store: usage, and the backup groups
# (what guest is backed up, how many snapshots, when it last ran, whether it verified). That is
# the "are the backups actually there and sound?" signal; the old collector only listed that a
# datastore *existed*, which proved nothing.
#
# Reads /opt/skynet-ops/secrets/pbs.env (0600 root-owned; the agent reads it via the sops-nix
# symlink, or falls back to `sudo -n cat` on a NOPASSWD host):
#   PBS_HOST=10.10.20.40
#   PBS_TOKEN='svc-ops@pbs!readonly:<uuid>'    # DatastoreAudit token (read-only); PBS uses ':' (PVE '=')
#   PBS_FINGERPRINT='BA:C3:..:2C'  (optional)  # leaf-cert SHA256; defaults to the PVE-recorded pin below
#   PBS_CACERT=/opt/skynet-ops/certs/pbs.crt   # optional: pin by a cert FILE instead of the fingerprint
#
# TLS: PBS serves a self-signed cert, so we PIN it — never `-k`/insecure. Default is trust-by-
# fingerprint: capture the leaf, verify its SHA256 against PBS_FINGERPRINT (the exact value Proxmox
# already stores for the `pbs-unraid` storage — public material, not a secret), then verify the API
# call against that pinned leaf. A PBS_CACERT file, if set, wins. Re-pin if the cert is rotated.
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
secret_file="${PBS_ENV_FILE:-/opt/skynet-ops/secrets/pbs.env}"  # PBS_ENV_FILE: test seam only

# Default fingerprint = the pin Proxmox records for the pbs-unraid storage (collect-proxmox sees it
# at /storage). Overridable via PBS_FINGERPRINT in the secret; a PBS_CACERT file overrides both.
PBS_FINGERPRINT_DEFAULT="BA:C3:32:F3:92:6B:4D:8F:FB:39:0D:D9:C4:B5:27:1D:D1:28:8A:41:F6:49:11:D0:FF:BE:21:9E:77:53:53:2C"

if ! { test -e "${secret_file}" 2>/dev/null || sudo -n test -f "${secret_file}" 2>/dev/null; }; then
  echo "no creds yet (${secret_file}) — collector idle. Mint a read token: on PBS run" >&2
  echo "  proxmox-backup-manager user generate-token svc-ops@pbs readonly" >&2
  echo "  proxmox-backup-manager acl update /datastore/unraid DatastoreAudit --auth-id 'svc-ops@pbs!readonly'" >&2
  echo "then add PBS_HOST/PBS_TOKEN to ${secret_file} (sops). Idle is not a failure — exit 0." >&2
  exit 0
fi
# shellcheck disable=SC1090
eval "$(cat "${secret_file}" 2>/dev/null || sudo -n cat "${secret_file}")"
: "${PBS_HOST:?}" "${PBS_TOKEN:?}"
PBS_PORT="${PBS_PORT:-8007}"
PBS_FINGERPRINT="${PBS_FINGERPRINT:-${PBS_FINGERPRINT_DEFAULT}}"

if [ "${PBS_SKIP_REACHABILITY:-0}" != "1" ]; then  # PBS_SKIP_REACHABILITY: test seam only
  if ! timeout 5 bash -c "</dev/tcp/${PBS_HOST}/${PBS_PORT}" 2>/dev/null; then
    echo "PBS ${PBS_HOST}:${PBS_PORT} unreachable — not writing inventory" >&2
    exit 1
  fi
fi

# --- pin the TLS cert ---------------------------------------------------------
CADIR="$(mktemp -d)"; trap 'rm -rf "${CADIR}"' EXIT
if [ -n "${PBS_CACERT:-}" ]; then
  [ -r "${PBS_CACERT}" ] || { echo "PBS_CACERT ${PBS_CACERT} not readable" >&2; exit 1; }
  cacert="${PBS_CACERT}"
else
  leaf="$(timeout 6 openssl s_client -connect "${PBS_HOST}:${PBS_PORT}" -servername "${PBS_HOST}" \
            </dev/null 2>/dev/null | openssl x509 2>/dev/null)"
  [ -n "${leaf}" ] || { echo "could not capture PBS TLS cert for pinning" >&2; exit 1; }
  got="$(printf '%s' "${leaf}" | openssl x509 -noout -fingerprint -sha256 2>/dev/null | sed 's/.*=//')"
  if [ "${got}" != "${PBS_FINGERPRINT}" ]; then
    echo "PBS cert fingerprint mismatch — refusing (got ${got}, want ${PBS_FINGERPRINT})" >&2
    echo "  if the PBS cert was rotated, re-pin: set PBS_FINGERPRINT in ${secret_file} to the new value" >&2
    exit 1
  fi
  cacert="${CADIR}/pbs-pinned.crt"; printf '%s\n' "${leaf}" > "${cacert}"
fi

# PBS's self-signed cert has NO IP in its SAN (only the hostname), so verifying by the IP we dial
# fails "no alternative certificate subject name matches" even with the right CA. Connect with
# SNI = the cert's own hostname (via --resolve → the IP), so the SAN matches AND the pin holds.
# Auto-extract it from the pinned cert (prefer an FQDN SAN, else the CN); PBS_SNI overrides.
sni="${PBS_SNI:-}"
if [ -z "${sni}" ]; then
  sni="$(openssl x509 -in "${cacert}" -noout -ext subjectAltName 2>/dev/null \
          | grep -oE 'DNS:[A-Za-z0-9.-]+' | sed 's/DNS://' | grep '\.' | grep -vi '^localhost' | head -1)"
  [ -n "${sni}" ] || sni="$(openssl x509 -in "${cacert}" -noout -subject 2>/dev/null \
          | grep -oE 'CN *= *[^,/]+' | sed 's/CN *= *//' | head -1)"
fi
: "${sni:?could not determine PBS cert hostname (set PBS_SNI in ${secret_file})}"

# PBS wants the token as `PBSAPIToken=<tokenid>:<secret>` — a COLON, unlike PVE's `=`. Tolerate a
# PVE-style `=` separator (easy to write by muscle memory) by swapping the first `=` to `:`; the
# tokenid and the UUID secret contain neither, so this only ever hits the separator.
PBS_AUTH="${PBS_TOKEN/=/:}"
api() { curl -sSf --max-time 20 --cacert "${cacert}" --resolve "${sni}:${PBS_PORT}:${PBS_HOST}" \
        -H "Authorization: PBSAPIToken=${PBS_AUTH}" \
        "https://${sni}:${PBS_PORT}/api2/json/$1"; }

# --- datastores + their backup content ---------------------------------------
# For each datastore: usage (status) + the backup groups. A group is one guest's backup history;
# we project the stable, decision-carrying fields — count of snapshots, last-backup time, and the
# verification state — so the report can say "vm/10015: 7 snapshots, last 2026-09-03, verify ok".
# Every per-store call degrades to null (never []), so a missing Datastore.Audit grant on one store
# reads as "unknown", not a false "no backups".
stores_json="$(api admin/datastore | jq '[.data[]?.store]')"

store_block() { # <store>
  local s="$1" status groups
  status="$(api "admin/datastore/${s}/status" 2>/dev/null | jq '.data // null' || echo null)"
  groups="$(api "admin/datastore/${s}/groups" 2>/dev/null \
    | jq '[.data[]? | {
             backup_type: ."backup-type",
             backup_id:   ."backup-id",
             backup_count:(."backup-count" // 0),
             last_backup: (."last-backup" // null),
             owner:       (.owner // null),
             verify_state:(.["verification"].state // .last_verify_state // null)
           }]' 2>/dev/null || echo null)"
  jq -n --arg s "${s}" --argjson status "${status:-null}" --argjson groups "${groups:-null}" \
    '{store:$s, status:$status, groups:$groups,
      group_count:(if $groups==null then null else ($groups|length) end),
      snapshot_total:(if $groups==null then null else ([$groups[].backup_count]|add // 0) end)}'
}

datastores="$(printf '%s' "${stores_json}" | jq -r '.[]?' | while IFS= read -r s; do
                [ -n "${s}" ] || continue
                store_block "${s}"
              done | jq -s '.')"

out="${REPO_DIR}/inventory/pbs.json"
jq -n \
  --arg host "${PBS_HOST}" \
  --arg ts "$(date -Iseconds)" \
  --argjson datastores "${datastores:-[]}" \
  '{collected:$ts, host:$host, datastores:$datastores}' > "${out}"
echo "wrote ${out} ($(printf '%s' "${datastores}" | jq 'length') datastore(s), $(printf '%s' "${datastores}" | jq '[.[].snapshot_total // 0]|add // 0') snapshot(s))"
