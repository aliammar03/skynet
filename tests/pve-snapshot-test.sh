#!/usr/bin/env bash
# pve-snapshot-test.sh — prove the snapshot helper's excluded-guest guard and VM-state default.
# TIER: T1 — temp secrets, certificate, and curl stub only; no network or Proxmox write.
set -uo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "${REPO_DIR}"
pass=0; fail=0
ok()  { printf '  \342\234\223 %s\n' "$1"; pass=$((pass+1)); }
bad() { printf '  \342\234\227 %s\n' "$1" >&2; fail=$((fail+1)); }

TMP="$(mktemp -d)"; trap 'rm -rf "${TMP}"' EXIT
mkdir -p "${TMP}/secrets" "${TMP}/bin"
: > "${TMP}/core.crt"
cat > "${TMP}/secrets/proxmox-core.env" <<EOF
PVE_HOST=stub.example
PVE_CACERT=${TMP}/core.crt
PVE_TOKEN_OPERATE=svc-ops@pve!operate=stub
EOF
cat > "${TMP}/bin/curl" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "${CURL_LOG}"
case "$*" in
  *'/tasks/'*) printf '%s\n' '{"data":{"status":"stopped","exitstatus":"OK"}}' ;;
  *) printf '%s\n' '{"data":"UPID:stub"}' ;;
esac
EOF
chmod +x "${TMP}/bin/curl"
: > "${TMP}/curl.log"

PVE_SECRET_DIR="${TMP}/secrets" CURL_LOG="${TMP}/curl.log" PATH="${TMP}/bin:${PATH}" \
  scripts/pve-snapshot.sh create server-proxmox-core vm 10015 test-snap >/dev/null 2>&1
grep -q 'vmstate=1' "${TMP}/curl.log" && ok "VM snapshots include vmstate by default" || bad "VM snapshot omitted vmstate=1"

before="$(wc -l < "${TMP}/curl.log")"
PVE_SECRET_DIR="${TMP}/secrets" CURL_LOG="${TMP}/curl.log" PATH="${TMP}/bin:${PATH}" \
  scripts/pve-snapshot.sh create server-proxmox-core vm 2020 test-snap >/dev/null 2>&1
rc=$?
after="$(wc -l < "${TMP}/curl.log")"
[ "${rc}" = 3 ] && [ "${before}" = "${after}" ] \
  && ok "excluded Unraid VM is refused before any API call" \
  || bad "excluded VM was not safely refused (rc=${rc}, curl ${before}->${after})"

echo
echo "pve-snapshot-test: ${pass} passed, ${fail} failed"
[ "${fail}" -eq 0 ]
