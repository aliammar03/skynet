#!/usr/bin/env bash
# tofu-rollback-test.sh — the L7 tofu-apply rollback (SKY-018 P6) in its guard + failure cases.
#   The wrapper must: refuse a delete/destroy plan and an excluded-guest plan OUTRIGHT (no apply);
#   snapshot touched guests before applying; restore snapshot + pre-apply state when apply fails;
#   retain snapshots for operator recovery when post-apply verification cannot pass; prune them on
#   success; fail closed if an update snapshot can't be taken; allow a supervised
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
mkdir -p "${TMP}/tdir" "${TMP}/secrets"; : > "${TMP}/plan.tfplan"
printf 'state-passphrase\n' > "${TMP}/secrets/tofu-passphrase"
cat > "${TMP}/secrets/proxmox-core.env" <<'EOF'
PVE_HOST=core.example
PVE_TOKEN_OPERATE=svc-ops@pve!operate=stub
EOF

# --- stub tofu: `show -json` prints the fixture; apply/plan/state return injected results ----------
cat > "${TMP}/tofu" <<'EOF'
#!/usr/bin/env bash
echo "$1" >> "${TOFU_LOG}"
case "$1" in
  show) cat "${STUB_PLAN_JSON}" ;;
  apply) exit "${STUB_APPLY_RC:-0}" ;;
  plan)  exit "${STUB_VERIFY_RC:-0}" ;;
  state) case "$2" in pull) printf '{"version":4}\n' ;; push|-force) exit "${STUB_STATE_PUSH_RC:-0}" ;; esac ;;
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
  TOFU_APPLY_SKIP_ENV="${TEST_SKIP_ENV:-1}" TOFU_APPLY_SCOPE="${TEST_SCOPE:-proxmox-core}" TOFU_DIR="${TMP}/tdir" TOFU_BIN="${TMP}/tofu" SECRETS_DIR="${TMP}/secrets" \
    PVE_SNAPSHOT="${TMP}/pve-snapshot.sh" STUB_PLAN_JSON="${TMP}/plan.json" SNAP_LOG="${SNAP_LOG}" TOFU_LOG="${TOFU_LOG}" \
    STUB_APPLY_RC="${STUB_APPLY_RC:-0}" STUB_VERIFY_RC="${STUB_VERIFY_RC:-0}" STUB_STATE_PUSH_RC="${STUB_STATE_PUSH_RC:-0}" FAIL_SNAPSHOT="${FAIL_SNAPSHOT:-}" \
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

# 3. apply FAILS → snapshot and pre-apply state restored
rc="$(STUB_APPLY_RC=1 STUB_VERIFY_RC=0 run "$(guest update 10015)")"
{ [ "${rc}" = 5 ] && printf '%s' "$(snaps)" | grep -q '^create 10015' && printf '%s' "$(snaps)" | grep -q '^rollback 10015'; } \
  && ok "apply failure → guest snapshotted then ROLLED BACK" || bad "apply-failure rollback wrong (rc=${rc}, snaps=[$(snaps | tr '\n' ';')])"
printf '%s' "$(snaps)" | grep -q '^delete 10015' && bad "pruned after a failed apply (should keep the restore point)" || ok "failed apply did not prune the snapshot"
printf '%s\n' "$(calls)" | grep -q '^state$' && ok "apply failure → pre-apply OpenTofu state restored" || bad "apply failure did not restore OpenTofu state"

# 4. a state-restore failure is distinct and escalates after the guest snapshot rollback
rc="$(STUB_APPLY_RC=1 STUB_VERIFY_RC=0 STUB_STATE_PUSH_RC=1 run "$(guest update 10015)")"
{ [ "${rc}" = 7 ] && printf '%s' "$(snaps)" | grep -q '^rollback 10015' && grep -q 'recovery FAILED' "${TMP}/out"; } \
  && ok "state restore failure → distinct hard checkpoint" || bad "state restore failure was not escalated (rc=${rc})"

# 5. a dirty post-apply plan retains the snapshot for explicit operator recovery; it does not auto-rollback
rc="$(STUB_APPLY_RC=0 STUB_VERIFY_RC=2 run "$(guest update 10015)")"
{ [ "${rc}" = 6 ] && ! printf '%s' "$(snaps)" | grep -q '^rollback 10015' && grep -q 'snapshots retained' "${TMP}/out"; } \
  && ok "dirty verification → snapshots retained for operator recovery" || bad "verify-failure safety path wrong (rc=${rc})"

# 6. a verifier/provider error is unknown state, never an automatic data-reverting rollback
rc="$(STUB_APPLY_RC=0 STUB_VERIFY_RC=1 run "$(guest update 10015)")"
{ [ "${rc}" = 7 ] && ! printf '%s' "$(snaps)" | grep -q '^rollback 10015' && grep -q 'verification unavailable' "${TMP}/out"; } \
  && ok "verification error → no automatic rollback on unknown state" || bad "verification-error safety path wrong (rc=${rc})"

# 7. success → snapshot then prune, no rollback
rc="$(STUB_APPLY_RC=0 STUB_VERIFY_RC=0 run "$(guest update 10015)")"
{ [ "${rc}" = 0 ] && printf '%s' "$(snaps)" | grep -q '^create 10015' && printf '%s' "$(snaps)" | grep -q '^delete 10015'; } \
  && ok "clean apply → snapshot pruned on success" || bad "success path wrong (rc=${rc}, snaps=[$(snaps | tr '\n' ';')])"
printf '%s' "$(snaps)" | grep -q '^rollback' && bad "rolled back a successful apply" || ok "successful apply did not roll back"

# 8. fail closed: snapshot cannot be taken → refuse to apply (exit 4), no apply
rc="$(STUB_APPLY_RC=0 STUB_VERIFY_RC=0 FAIL_SNAPSHOT=1 run "$(guest update 10015)")"
[ "${rc}" = 4 ] && ok "snapshot failure → FAIL CLOSED (no apply without a rollback point)" || bad "did not fail closed on snapshot failure (rc=${rc})"
printf '%s\n' "$(calls)" | grep -q '^apply$' && bad "snapshot failure reached apply" || ok "snapshot failure → no apply"

# 9. guest create success → apply without a nonexistent pre-snapshot, with supervised warning
rc="$(STUB_APPLY_RC=0 STUB_VERIFY_RC=0 run "$(new_guest 9042)")"
{ [ "${rc}" = 0 ] && [ -z "$(snaps)" ] && grep -q "supervised guest create" "${TMP}/out"; } \
  && ok "guest create → allowed as supervised saved-plan action, no false snapshot" || bad "guest create path wrong (rc=${rc}, snaps=[$(snaps | tr '\n' ';')])"
printf '%s\n' "$(calls)" | grep -q '^apply$' && ok "supervised guest create reached saved-plan apply" || bad "guest create never reached apply"

# 10. guest create failure → no automatic delete; output requires operator recovery
rc="$(STUB_APPLY_RC=1 STUB_VERIFY_RC=0 run "$(new_guest 9042)")"
{ [ "${rc}" = 5 ] && [ -z "$(snaps)" ] && grep -q "created guests.*need operator recovery" "${TMP}/out"; } \
  && ok "failed guest create → explicit operator recovery, never auto-delete" || bad "failed guest create truth wrong (rc=${rc}, snaps=[$(snaps | tr '\n' ';')])"
printf '%s\n' "$(calls)" | grep -q '^apply$' && ok "failed guest create exercised apply" || bad "failed guest create never reached apply"

# 11. non-guest apply failure → no guest snapshot exists; output requires operator recovery
non_guest='{"resource_changes":[{"address":"cloudflare_dns_record.tunnel[\"x\"]","type":"cloudflare_dns_record","change":{"actions":["create"],"before":null,"after":{"name":"x.aliammar.net"}}}]}'
rc="$(TEST_SCOPE=cloudflare-dns STUB_APPLY_RC=1 STUB_VERIFY_RC=0 run "${non_guest}")"
{ [ "${rc}" = 5 ] && [ -z "$(snaps)" ] && grep -q "non-guest changes need operator recovery" "${TMP}/out"; } \
  && ok "non-guest failure → no false snapshot rollback claim" || bad "non-guest rollback truth wrong (rc=${rc}, snaps=[$(snaps | tr '\n' ';')])"

# 12. a mixed saved plan cannot apply under a single declared actuator scope
mixed="$(jq -cn --argjson a "$(new_guest 9042)" --argjson b "${non_guest}" '{resource_changes: ($a.resource_changes + $b.resource_changes)}')"
rc="$(STUB_APPLY_RC=0 STUB_VERIFY_RC=0 run "${mixed}")"
{ [ "${rc}" = 2 ] && grep -q 'scope' "${TMP}/out"; } \
  && ok "mixed actuator plan → REFUSED before apply" || bad "mixed scope plan was not refused (rc=${rc})"
printf '%s\n' "$(calls)" | grep -q '^apply$' && bad "mixed scope plan reached apply" || ok "mixed scope plan → no apply"

# 13. Saved-plan apply loads only the selected actuator secret, not unrelated DNS/node credentials.
rc="$(TEST_SKIP_ENV=0 STUB_APPLY_RC=0 STUB_VERIFY_RC=0 run "$(guest update 10015)")"
[ "${rc}" = 0 ] && ok "core saved-plan apply works without unrelated DNS/network secret files" \
  || bad "scoped credential loading failed (rc=${rc})"

echo
echo "tofu-rollback-test: ${pass} passed, ${fail} failed"
[ "${fail}" -eq 0 ]
