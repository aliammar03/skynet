#!/usr/bin/env bash
# nightly-sequence-test.sh — mocked regression tests for the one-owner nightly sequence.
# TIER: T1 — copies the repo to a temp directory; stubs git, gh, collectors, and renderers. Run: bash tests/nightly-sequence-test.sh
set -uo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_DIR}"
pass=0; fail=0
ok()  { printf '  ✓ %s\n' "$1"; pass=$((pass + 1)); }
bad() { printf '  ✗ %s\n' "$1" >&2; fail=$((fail + 1)); }

TMP="$(mktemp -d)"; trap 'rm -rf "${TMP}"' EXIT

fixture() {
  local name="$1"
  cp -a "${REPO_DIR}" "${TMP}/${name}"
  mkdir -p "${TMP}/${name}/mock-bin" "${TMP}/${name}/mock-state"
  cat >"${TMP}/${name}/mock-bin/git" <<'EOF'
#!/usr/bin/env bash
printf 'git %s\n' "$*" >>"${NIGHTLY_LOG}"
case "${1:-}" in
  diff)
    if [[ " $* " == *" --cached --quiet "* ]]; then
      [ -e "${NIGHTLY_STATE}/staged" ] && exit 1 || exit 0
    fi
    [[ " $* " == *" --quiet "* ]] && exit 0
    printf 'mock diff stat\n'
    ;;
  add) touch "${NIGHTLY_STATE}/staged" ;;
esac
EOF
  cat >"${TMP}/${name}/mock-bin/gh" <<'EOF'
#!/usr/bin/env bash
printf 'gh %s\n' "$*" >>"${NIGHTLY_LOG}"
[ "${1:-}" = pr ] && [ "${2:-}" = create ] && printf 'https://example.invalid/pr/42\n'
EOF
  cat >"${TMP}/${name}/mock-bin/tofu" <<'EOF'
#!/usr/bin/env bash
printf 'tofu %s\n' "$*" >>"${NIGHTLY_LOG}"
printf 'No changes.\n'
EOF
  cat >"${TMP}/${name}/scripts/collect-all.sh" <<'EOF'
#!/usr/bin/env bash
printf 'collection\n' >>"${NIGHTLY_LOG}"
[ "${FAIL_COLLECTION:-0}" = 1 ] && exit 1
EOF
  cat >"${TMP}/${name}/scripts/envsync.sh" <<'EOF'
#!/usr/bin/env bash
printf 'envsync\n' >>"${NIGHTLY_LOG}"
EOF
  cat >"${TMP}/${name}/scripts/render-docs.sh" <<'EOF'
#!/usr/bin/env bash
printf 'render-docs\n' >>"${NIGHTLY_LOG}"
EOF
  cat >"${TMP}/${name}/scripts/render-digest.sh" <<'EOF'
#!/usr/bin/env bash
find journal -name '*session-nightly*' -print -quit | grep -q . || exit 1
printf 'render-digest\n' >>"${NIGHTLY_LOG}"
EOF
  cat >"${TMP}/${name}/scripts/render-context-map.sh" <<'EOF'
#!/usr/bin/env bash
find journal -name '*session-nightly*' -print -quit | grep -q . || exit 1
printf 'render-context-map\n' >>"${NIGHTLY_LOG}"
EOF
  cat >"${TMP}/${name}/scripts/tofu-env.sh" <<'EOF'
#!/usr/bin/env bash
:
EOF
  cat >"${TMP}/${name}/scripts/nightly-automerge.sh" <<'EOF'
#!/usr/bin/env bash
printf 'merge-gate %s\n' "$*" >>"${NIGHTLY_LOG}"
EOF
  chmod +x "${TMP}/${name}/mock-bin/"* "${TMP}/${name}/scripts/"{collect-all,envsync,render-docs,render-digest,render-context-map,tofu-env,nightly-automerge}.sh
}

run_sequence() {
  local name="$1" failure="${2:-0}" dir
  dir="${TMP}/${name}"
  : >"${dir}/log"; : >"${dir}/status"
  (
    cd "${dir}"
    NIGHTLY_LOG="${dir}/log" NIGHTLY_STATE="${dir}/mock-state" OPS_NIGHTLY_STATUS_FILE="${dir}/status" \
      OPS_NIGHTLY_BRANCH="inventory/nightly-sequence-test" PATH="${dir}/mock-bin:${PATH}" FAIL_COLLECTION="${failure}" \
      bash scripts/nightly.sh --prepare
    # This is the agent-failure fallback boundary: the finalizer must not re-run prepare work.
    NIGHTLY_LOG="${dir}/log" NIGHTLY_STATE="${dir}/mock-state" OPS_NIGHTLY_STATUS_FILE="${dir}/status" \
      OPS_NIGHTLY_BRANCH="inventory/nightly-sequence-test" PATH="${dir}/mock-bin:${PATH}" \
      bash scripts/nightly.sh --finalize
  ) >/dev/null 2>&1
}

fixture normal
run_sequence normal
log="${TMP}/normal/log"
for step in collection envsync render-docs render-digest render-context-map; do
  count="$(grep -c "^${step}$" "${log}")"
  [ "${count}" = 1 ] && ok "${step} runs exactly once" || bad "${step} ran ${count} times"
done
if [ "$(grep -n '^render-digest$' "${log}" | cut -d: -f1)" -gt "$(grep -n '^render-docs$' "${log}" | cut -d: -f1)" ]; then
  ok "final digest runs after prepared factual render"
else
  bad "digest did not follow factual render"
fi
grep -q '^gh pr create ' "${log}" && grep -q '^merge-gate ' "${log}" \
  && ok "deterministic finalizer owns PR preparation and merge gate" \
  || bad "finalizer did not prepare PR and invoke gate"
find "${TMP}/normal/journal" -name '*session-nightly*' -print -quit | grep -q . \
  && ok "journal entry exists before final renderers" || bad "journal entry missing"

fixture failing-collection
run_sequence failing-collection 1
flog="${TMP}/failing-collection/log"
[ "$(grep -c '^collection$' "${flog}")" = 1 ] && grep -q '^render-context-map$' "${flog}" \
  && ok "collection failure is recorded without repeating prepared work" \
  || bad "collection failure stopped or repeated the sequence"
fentry="$(find "${TMP}/failing-collection/journal" -name '*session-nightly*' | sort | tail -1)"
grep -q -- '- collection' "${fentry}" && ok "journal carries the non-fatal collector failure" \
  || bad "journal did not carry collector failure"

fixture bin-ops
: >"${TMP}/bin-ops/log"
(
  cd "${TMP}/bin-ops"
  NIGHTLY_LOG="${TMP}/bin-ops/log" NIGHTLY_STATE="${TMP}/bin-ops/mock-state" \
    OPS_NIGHTLY_MODE=script OPS_NIGHTLY_BRANCH="inventory/nightly-sequence-test" \
    PATH="${TMP}/bin-ops/mock-bin:${PATH}" bash bin/ops nightly
) >/dev/null 2>&1
blog="${TMP}/bin-ops/log"
[ "$(grep -c '^collection$' "${blog}")" = 1 ] && [ "$(grep -c '^render-docs$' "${blog}")" = 1 ] \
  && ok "bin/ops script mode prepares and finalizes once" \
  || bad "bin/ops script mode repeated or skipped deterministic work"

echo
echo "nightly-sequence-test: ${pass} passed, ${fail} failed"
[ "${fail}" -eq 0 ]
