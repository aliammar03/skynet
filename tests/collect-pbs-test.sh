#!/usr/bin/env bash
# collect-pbs-test.sh — checker for collect-pbs.sh (the PBS writer). Proves the two behaviours we
# can't exercise against live PBS without a read token: graceful idle when no creds exist, and the
# datastore/group projection (usage + per-guest snapshot counts + verification state) when they do.
# TIER: T1 — stubs `curl` on PATH; no network, no real creds. Run: bash tests/collect-pbs-test.sh
set -uo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_DIR}"
SCRIPT="${REPO_DIR}/scripts/collect-pbs.sh"
OUT="${REPO_DIR}/inventory/pbs.json"

pass=0; fail=0
ok()  { printf '  \342\234\223 %s\n' "$1"; pass=$(( pass + 1 )); }
bad() { printf '  \342\234\227 %s\n' "$1" >&2; fail=$(( fail + 1 )); }
eq()  { if [ "$2" = "$3" ]; then ok "$1"; else bad "$1 — expected [$3], got [$2]"; fi; }

TMP="$(mktemp -d)"
# Don't clobber a real inventory/pbs.json if one somehow exists.
[ -e "${OUT}" ] && cp "${OUT}" "${TMP}/pbs.json.bak"
cleanup() {
  rm -f "${OUT}"
  [ -e "${TMP}/pbs.json.bak" ] && mv "${TMP}/pbs.json.bak" "${OUT}"
  rm -rf "${TMP}"
}
trap cleanup EXIT

echo "== idle path: no creds → exit 0, no inventory written =="
rm -f "${OUT}"
PBS_ENV_FILE="${TMP}/nonexistent.env" bash "${SCRIPT}" >/dev/null 2>&1
eq "no-creds collector exits 0 (idle is not a failure)" "$?" "0"
[ -e "${OUT}" ] && bad "idle collector wrote inventory (it must not)" || ok "idle collector wrote no inventory"

echo "== collection: stubbed PBS API → datastore + group projection =="
# stub curl: answer each PBS endpoint by its URL (the last argument)
cat > "${TMP}/curl" <<'STUB'
#!/usr/bin/env bash
url="${@: -1}"
case "${url}" in
  # backups live in namespaces; snapshots (not groups) carry the verify state. Match ns queries first.
  */admin/datastore/unraid/snapshots\?ns=core) echo '{"data":[
      {"backup-type":"vm","backup-id":"10015","backup-time":100,"owner":"svc-ops@pbs","verification":{"state":"ok"}},
      {"backup-type":"vm","backup-id":"10015","backup-time":200,"owner":"svc-ops@pbs","verification":null},
      {"backup-type":"ct","backup-id":"101","backup-time":150,"owner":"svc-ops@pbs","verification":{"state":"ok"}}
    ]}' ;;
  */admin/datastore/unraid/snapshots)  echo '{"data":[]}' ;;      # root namespace: empty
  */admin/datastore/unraid/namespace)  echo '{"data":[{"ns":""},{"ns":"core"}]}' ;;
  */admin/datastore/unraid/status)     echo '{"data":{"total":1000,"used":400,"avail":600}}' ;;
  */admin/datastore)                   echo '{"data":[{"store":"unraid"}]}' ;;
  *) echo '{"data":[]}' ;;
esac
exit 0
STUB
chmod +x "${TMP}/curl"
# a dummy cacert file so the collector skips fingerprint capture (openssl untouched)
: > "${TMP}/pbs.crt"
# PBS_SNI set so the stub path skips cert-hostname extraction (no real cert to read here)
printf 'PBS_HOST=10.10.20.40\nPBS_TOKEN=svc-ops@pbs!readonly=deadbeef\nPBS_CACERT=%s\nPBS_SNI=pbs.test\n' "${TMP}/pbs.crt" > "${TMP}/pbs.env"

rm -f "${OUT}"
PATH="${TMP}:${PATH}" PBS_ENV_FILE="${TMP}/pbs.env" PBS_SKIP_REACHABILITY=1 bash "${SCRIPT}" >/dev/null 2>&1
eq "collector exits 0 with stubbed creds" "$?" "0"
if [ -s "${OUT}" ]; then
  eq "one datastore recorded"                 "$(jq '.datastores|length' "${OUT}")"                                  "1"
  eq "host recorded"                          "$(jq -r '.host' "${OUT}")"                                            "10.10.20.40"
  eq "group_count = 2 (root ns empty, both guests in core)" "$(jq '.datastores[0].group_count' "${OUT}")"           "2"
  eq "snapshot_total counts snapshots (2+1)"  "$(jq '.datastores[0].snapshot_total' "${OUT}")"                       "3"
  eq "vm/10015 backup_count = 2"              "$(jq '.datastores[0].groups[]|select(.backup_id=="10015").backup_count' "${OUT}")" "2"
  eq "vm/10015 last_backup = latest (200)"    "$(jq '.datastores[0].groups[]|select(.backup_id=="10015").last_backup' "${OUT}")" "200"
  eq "vm/10015 verify_state = null (latest unverified — surfaced)" "$(jq '.datastores[0].groups[]|select(.backup_id=="10015").verify_state' "${OUT}")" "null"
  eq "ct/101 verify_state = ok"               "$(jq -r '.datastores[0].groups[]|select(.backup_id=="101").verify_state' "${OUT}")" "ok"
  eq "groups carry their namespace"           "$(jq -r '.datastores[0].groups[0].ns' "${OUT}")"                      "core"
  eq "unverified count = 1"                   "$(jq '.datastores[0].unverified' "${OUT}")"                           "1"
  eq "datastore usage carried through"        "$(jq '.datastores[0].status.used' "${OUT}")"                         "400"
else
  bad "collector wrote no inventory with stubbed creds"
fi

echo
echo "collect-pbs-test: ${pass} passed, ${fail} failed"
[ "${fail}" -eq 0 ]
