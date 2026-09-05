#!/usr/bin/env bash
# nightly-automerge-test.sh — mocked fail-closed regression tests for the nightly merge gate.
# TIER: T1 — PATH stubs gh; no network, PR, or repository mutation. Run: bash tests/nightly-automerge-test.sh
set -uo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_DIR}"
pass=0; fail=0
ok()  { printf '  ✓ %s\n' "$1"; pass=$((pass + 1)); }
bad() { printf '  ✗ %s\n' "$1" >&2; fail=$((fail + 1)); }

TMP="$(mktemp -d)"; trap 'rm -rf "${TMP}"' EXIT
mkdir -p "${TMP}/bin"
cat >"${TMP}/bin/gh" <<'EOF'
#!/usr/bin/env bash
set -u
printf '%s\n' "$*" >>"${GH_LOG}"
today="$(date +%Y-%m-%d)"
case "${1:-} ${2:-}" in
  "pr view")
    if [[ " $* " == *" --json number,state,headRefName,headRefOid "* ]]; then
      views_file="${GH_LOG}.views"; views=0; [ -e "${views_file}" ] && views="$(cat "${views_file}")"
      views=$((views + 1)); printf '%s' "${views}" >"${views_file}"
      head=abc123
      [ "${CASE}" = changed-head ] && [ "${views}" -ge 2 ] && head=def456
      printf '42\tOPEN\tinventory/%s-1200\t%s\n' "${today}" "${head}"
    elif [[ " $* " == *" --json state "* ]]; then
      [ -e "${MERGE_LOG}" ] && printf 'MERGED\n' || printf 'OPEN\n'
    fi
    ;;
  "pr diff")
    case "${CASE}" in
      files-fail) exit 1 ;;
      files-empty) exit 0 ;;
      disallowed) printf 'README.md\n' ;;
      *) printf 'inventory/proxmox-core.json\njournal/2026/fixture.md\n' ;;
    esac
    ;;
  "pr checks")
    if [[ " $* " == *" --watch "* ]]; then
      case "${CASE}" in checks-failed|checks-pending) exit 1;; *) exit 0;; esac
    fi
    case "${CASE}" in
      checks-missing) exit 0 ;;
      checks-pending) printf 'pending\n' ;;
      *) printf 'green\n' ;;
    esac
    ;;
  "pr merge")
    printf '%s\n' "$*" >"${MERGE_LOG}"
    ;;
  *) exit 97 ;;
esac
EOF
chmod +x "${TMP}/bin/gh"

run_case() {
  local name="$1" expect_merge="$2" out
  rm -f "${TMP}/merge" "${TMP}/gh.log" "${TMP}/gh.log.views"
  out="$(CASE="${name}" GH_LOG="${TMP}/gh.log" MERGE_LOG="${TMP}/merge" \
    OPS_NIGHTLY_BRANCH="inventory/$(date +%Y-%m-%d)-1200" PATH="${TMP}/bin:${PATH}" \
    bash scripts/nightly-automerge.sh 42 2>&1)"
  if [ "${expect_merge}" = yes ] && [ -e "${TMP}/merge" ]; then
    ok "${name} permits only the validated merge"
  elif [ "${expect_merge}" = no ] && [ ! -e "${TMP}/merge" ]; then
    ok "${name} leaves PR open"
  else
    bad "${name} merge decision wrong: ${out}"
  fi
}

echo "== nightly automerge: all uncertainty fails closed =="
run_case files-fail no
run_case files-empty no
run_case disallowed no
run_case checks-failed no
run_case checks-pending no
run_case checks-missing no
run_case changed-head no
run_case allowed yes

if [ -e "${TMP}/merge" ] && grep -q -- '--match-head-commit abc123' "${TMP}/merge"; then
  ok "allowed merge binds the expected head commit"
else
  bad "allowed merge did not bind the validated head"
fi

# An explicit PR number is not sufficient when the caller's exact branch differs.
rm -f "${TMP}/merge" "${TMP}/gh.log" "${TMP}/gh.log.views"
CASE=allowed GH_LOG="${TMP}/gh.log" MERGE_LOG="${TMP}/merge" \
  OPS_NIGHTLY_BRANCH="inventory/$(date +%Y-%m-%d)-other" PATH="${TMP}/bin:${PATH}" \
  bash scripts/nightly-automerge.sh 42 >/dev/null 2>&1
[ ! -e "${TMP}/merge" ] && ok "wrong PR identity leaves PR open" || bad "wrong identity reached merge"

echo
echo "nightly-automerge-test: ${pass} passed, ${fail} failed"
[ "${fail}" -eq 0 ]
