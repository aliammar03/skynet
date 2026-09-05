#!/usr/bin/env bash
# tofu-rollback-test.sh — the L7 tofu-apply rollback (SKY-018 P6) in its guard + failure cases.
#   The wrapper must: refuse a delete/destroy plan and an excluded-guest plan OUTRIGHT (no apply);
#   snapshot touched guests before applying; roll those snapshots back when apply OR verify fails;
#   prune them on success; fail closed if an update snapshot can't be taken; allow a supervised
#   guest create without pretending it has snapshot rollback; and state honestly that a non-guest
#   write has no automatic snapshot rollback. Every decision is an exit code from
#   deterministic tooling, never the agent — proven by injecting apply/verify/snapshot results and
#   asserting what the wrapper did. tofu + pve-snapshot are stubbed: nothing real is touched.
# TIER: T1 — stubs only.
set -uo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "${REPO_DIR}"
pass=0; fail=0
ok()  { printf '  \342\234\223 %s\n' "$1"; pass=$((pass+1)); }
bad() { printf '  \342\234\227 %s\n' "$1" >&2; fail=$((fail+1)); }

TMP="$(mktemp -d)"; trap 'rm -rf "${TMP}"' EXIT
mkdir -p "${TMP}/tdir"; : > "${TMP}/plan.tfplan"

# --- stub tofu: `show -json` prints the fixture; apply/plan return injected exit codes -------------
cat > "${TMP}/tofu" <<'EOF'
#!/usr/bin/env bash
echo "$1" >> "${TOFU_LOG}"
case "$1" in
  show) cat "${STUB_PLAN_JSON}" ;;
  apply) exit "${STUB_APPLY_RC:-0}" ;;
  plan)  exit "${STUB_VERIFY_RC:-0}" ;;
  *) exit 0 ;;
esac
EOF
chmod +x "${TMP}/tofu"

# --- stub pve-snapshot: log "<op> <vmid>"; create fails if FAIL_SNAPSHOT set ----------------------
cat > "${TMP}/pve-snapshot.sh" <<'EOF'
#!/usr/bin/env bash
echo "$1 $4" >> "${SNAP_LOG}"
[ "$1" = create ] && [ -n "${FAIL_SNAPSHOT:-}" ] && exit 1
exit 0
EOF
chmod +x "${TMP}/pve-snapshot.sh"

run() {  # run the wrapper with the common stub wiring; $1 = plan fixture json
  printf '%s' "$1" > "${TMP}/plan.json"
  SNAP_LOG="${TMP}/snap.log"; : > "${SNAP_LOG}"
  TOFU_LOG="${TMP}/tofu.log"; : > "${TOFU_LOG}"
  TOFU_APPLY_SKIP_ENV=1 TOFU_DIR="${TMP}/tdir" TOFU_BIN="${TMP}/tofu" \
    PVE_SNAPSHOT="${TMP}/pve-snapshot.sh" STUB_PLAN_JSON="${TMP}/plan.json" SNAP_LOG="${SNAP_LOG}" TOFU_LOG="${TOFU_LOG}" \
    STUB_APPLY_RC="${STUB_APPLY_RC:-0}" STUB_VERIFY_RC="${STUB_VERIFY_RC:-0}" FAIL_SNAPSHOT="${FAIL_SNAPSHOT:-}" \
    bash scripts/tofu-apply.sh "${TMP}/plan.tfplan" >"${TMP}/out" 2>&1
  echo $?
}
snaps() { cat "${TMP}/snap.log" 2>/dev/null; }
calls() { cat "${TMP}/tofu.log" 2>/dev/null; }

guest() { # $1=action $2=vmid  → a one-guest plan fixture
  printf '{"resource_changes":[{"address":"proxmox_virtual_environment_vm.g","type":"proxmox_virtual_environment_vm","change":{"actions":["%s"],"before":{"vm_id":%s,"node_name":"server-proxmox-core"},"after":{"vm_id":%s,"node_name":"server-proxmox-core"}}}]}' "$1" "$2" "$2"
}
new_guest() { # $1=vmid → a real create shape: before=null, after has the new envelope
  printf '{"resource_changes":[{"address":"proxmox_virtual_environment_container.g","type":"proxmox_virtual_environment_container","change":{"actions":["create"],"before":null,"after":{"vm_id":%s,"node_name":"server-proxmox-core"}}}]}' "$1"
}

# 1. destroy/delete refusal — no snapshot, no apply, exit 3
rc="$(STUB_APPLY_RC=0 STUB_VERIFY_RC=0 run "$(guest delete 10015)")"
[ "${rc}" = 3 ] && grep -q "REFUSED" "${TMP}/out" && ok "delete plan REFUSED outright (exit 3)" || bad "delete plan not refused (rc=${rc})"
[ -z "$(snaps)" ] && ok "refused delete → no snapshot taken" || bad "snapshot taken on a refused delete"
printf '%s\n' "$(calls)" | grep -q '^apply$' && bad "refused delete reached apply" || ok "refused delete → no apply"

# 2. excluded T3 guest (5001 OPNsense) refusal
rc="$(STUB_APPLY_RC=0 STUB_VERIFY_RC=0 run "$(guest update 5001)")"
[ "${rc}" = 3 ] && grep -q "excluded guest" "${TMP}/out" && ok "excluded-guest plan REFUSED (exit 3)" || bad "excluded guest not refused (rc=${rc})"

# 3. apply FAILS → snapshot rolled back
rc="$(STUB_APPLY_RC=1 STUB_VERIFY_RC=0 run "$(guest update 10015)")"
{ [ "${rc}" = 5 ] && printf '%s' "$(snaps)" | grep -q '^create 10015' && printf '%s' "$(snaps)" | grep -q '^rollback 10015'; } \
  && ok "apply failure → guest snapshotted then ROLLED BACK" || bad "apply-failure rollback wrong (rc=${rc}, snaps=[$(snaps | tr '\n' ';')])"
printf '%s' "$(snaps)" | grep -q '^delete 10015' && bad "pruned after a failed apply (should keep the restore point)" || ok "failed apply did not prune the snapshot"

# 4. verify FAILS (apply ok, post-apply plan dirty) → rollback
rc="$(STUB_APPLY_RC=0 STUB_VERIFY_RC=2 run "$(guest update 10015)")"
{ [ "${rc}" = 6 ] && printf '%s' "$(snaps)" | grep -q '^rollback 10015'; } \
  && ok "verify failure → ROLLED BACK (deterministic verdict, not the agent)" || bad "verify-failure rollback wrong (rc=${rc})"

# 5. success → snapshot then prune, no rollback
rc="$(STUB_APPLY_RC=0 STUB_VERIFY_RC=0 run "$(guest update 10015)")"
{ [ "${rc}" = 0 ] && printf '%s' "$(snaps)" | grep -q '^create 10015' && printf '%s' "$(snaps)" | grep -q '^delete 10015'; } \
  && ok "clean apply → snapshot pruned on success" || bad "success path wrong (rc=${rc}, snaps=[$(snaps | tr '\n' ';')])"
printf '%s' "$(snaps)" | grep -q '^rollback' && bad "rolled back a successful apply" || ok "successful apply did not roll back"

# 6. fail closed: snapshot cannot be taken → refuse to apply (exit 4), no apply
rc="$(STUB_APPLY_RC=0 STUB_VERIFY_RC=0 FAIL_SNAPSHOT=1 run "$(guest update 10015)")"
[ "${rc}" = 4 ] && ok "snapshot failure → FAIL CLOSED (no apply without a rollback point)" || bad "did not fail closed on snapshot failure (rc=${rc})"

# 7. guest create success → apply without a nonexistent pre-snapshot, with supervised warning
rc="$(STUB_APPLY_RC=0 STUB_VERIFY_RC=0 run "$(new_guest 9042)")"
{ [ "${rc}" = 0 ] && [ -z "$(snaps)" ] && grep -q "supervised guest create" "${TMP}/out"; } \
  && ok "guest create → allowed as supervised saved-plan action, no false snapshot" || bad "guest create path wrong (rc=${rc}, snaps=[$(snaps | tr '\n' ';')])"
printf '%s\n' "$(calls)" | grep -q '^apply$' && ok "supervised guest create reached saved-plan apply" || bad "guest create never reached apply"

# 8. guest create failure → no automatic delete; output requires operator recovery
rc="$(STUB_APPLY_RC=1 STUB_VERIFY_RC=0 run "$(new_guest 9042)")"
{ [ "${rc}" = 5 ] && [ -z "$(snaps)" ] && grep -q "created guests.*need operator recovery" "${TMP}/out"; } \
  && ok "failed guest create → explicit operator recovery, never auto-delete" || bad "failed guest create truth wrong (rc=${rc}, snaps=[$(snaps | tr '\n' ';')])"
printf '%s\n' "$(calls)" | grep -q '^apply$' && ok "failed guest create exercised apply" || bad "failed guest create never reached apply"

# 9. non-guest apply failure → no guest snapshot exists; output requires operator recovery
non_guest='{"resource_changes":[{"address":"cloudflare_dns_record.tunnel[\"x\"]","type":"cloudflare_dns_record","change":{"actions":["create"],"before":null,"after":{"name":"x.aliammar.net"}}}]}'
rc="$(STUB_APPLY_RC=1 STUB_VERIFY_RC=0 run "${non_guest}")"
{ [ "${rc}" = 5 ] && [ -z "$(snaps)" ] && grep -q "non-guest changes need operator recovery" "${TMP}/out"; } \
  && ok "non-guest failure → no false snapshot rollback claim" || bad "non-guest rollback truth wrong (rc=${rc}, snaps=[$(snaps | tr '\n' ';')])"

echo
echo "tofu-rollback-test: ${pass} passed, ${fail} failed"
[ "${fail}" -eq 0 ]
