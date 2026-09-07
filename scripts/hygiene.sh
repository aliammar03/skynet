#!/usr/bin/env bash
# hygiene.sh — report current-authority drift, review candidates, and configured context budgets.
# TIER: T1 — reads the local repository only; never uses the network or changes repository/live state.
# USAGE: scripts/hygiene.sh [comparison-ref] (or HYGIENE_BASE_REF=<git-ref>); invoked by bin/ops hygiene.
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_DIR}"
source scripts/repo-surface.sh

BASE_REF="${1:-${HYGIENE_BASE_REF:-}}"
[ "$#" -le 1 ] || { echo "usage: bin/ops hygiene [baseline-ref]" >&2; exit 2; }
MAX_ALWAYS_LOADED_TOKENS="${MAX_ALWAYS_LOADED_TOKENS:-6500}"
MAX_CURRENT_AUTHORITY_TOKENS="${MAX_CURRENT_AUTHORITY_TOKENS:-200000}"

always_loaded_path() {
  case "$1" in AGENTS.md|README.md|CLAUDE.md) return 0;; *) return 1;; esac
}

current_surface_files() {
  repo_surface_files current
}

baseline_surface_files() {
  git ls-tree -r --name-only "${BASE_REF}" | while IFS= read -r path; do
    git show "${BASE_REF}:${path}" 2>/dev/null | LC_ALL=C grep -Iq '' || continue
    repo_surface_classify_path "${path}" | grep -qx current && printf '%s\n' "${path}"
  done
}

files_bytes() {
  while IFS= read -r path; do wc -c < "${path}"; done | awk '{sum += $1} END {print sum + 0}'
}

files_words() {
  while IFS= read -r path; do wc -w < "${path}"; done | awk '{sum += $1} END {print sum + 0}'
}

baseline_bytes() {
  baseline_surface_files | while IFS= read -r path; do git cat-file -s "${BASE_REF}:${path}"; done | awk '{sum += $1} END {print sum + 0}'
}

baseline_words() {
  baseline_surface_files | while IFS= read -r path; do git show "${BASE_REF}:${path}" | wc -w; done | awk '{sum += $1} END {print sum + 0}'
}

delta() {
  local before="$1" after="$2" sign=""
  [ "${after}" -gt "${before}" ] && sign="+"
  printf '%s%s' "${sign}" "$((after - before))"
}

report_gate() {
  local label="$1" command="$2"
  local output status
  output="$(mktemp)"
  if bash "${command}" >"${output}" 2>&1; then
    status=pass
  else
    status=fail
  fi
  printf '\n== %s: %s ==\n' "${label}" "${status}"
  sed 's/^/  /' "${output}"
  rm -f "${output}"
  [ "${status}" = pass ]
}

orphan_candidates() {
  local path references
  while IFS= read -r path; do
    references="$(grep -rlF -- "${path}" AGENTS.md README.md CLAUDE.md .githooks .github docs runbooks scripts bin tofu nix hosts compose tests templates 2>/dev/null | grep -Fxv "${path}" || true)"
    [ -n "${references}" ] || printf '%s\n' "${path}"
  done < <(find scripts bin -type f \( -name '*.sh' -o -path 'bin/*' \) | sort)
}

echo "== Skynet hygiene (T1, local-only) =="
failures=0
repo_surface_check || failures=$((failures + 1))
report_gate "temporal-hygiene" tests/temporal-hygiene-test.sh || failures=$((failures + 1))
report_gate "documentation-drift" tests/documentation-drift-test.sh || failures=$((failures + 1))

echo
echo "== advisory review candidates =="
candidates="$(orphan_candidates)"
if [ -n "${candidates}" ]; then
  printf '%s\n' "${candidates}" | sed 's/^/  /'
  echo "  Review only: an unreferenced path may be intentionally manual or break-glass; this command never deletes it."
else
  echo "  none"
fi

echo
echo "== context budget =="
current_always_bytes="$(current_surface_files | while IFS= read -r path; do if always_loaded_path "${path}"; then printf '%s\n' "${path}"; fi; done | files_bytes)"
current_always_words="$(current_surface_files | while IFS= read -r path; do if always_loaded_path "${path}"; then printf '%s\n' "${path}"; fi; done | files_words)"
current_bytes="$(current_surface_files | files_bytes)"
current_words="$(current_surface_files | files_words)"
always_tokens="$((current_always_bytes / 4))"
authority_tokens="$((current_bytes / 4))"
printf '  configured limits: always-loaded <= %s tokens; current-authority <= %s tokens\n' "${MAX_ALWAYS_LOADED_TOKENS}" "${MAX_CURRENT_AUTHORITY_TOKENS}"
printf '  always-loaded: %s words, %s bytes, approx. %s tokens\n' "${current_always_words}" "${current_always_bytes}" "${always_tokens}"
printf '  current-authority: %s words, %s bytes, approx. %s tokens\n' "${current_words}" "${current_bytes}" "${authority_tokens}"
[ "${always_tokens}" -le "${MAX_ALWAYS_LOADED_TOKENS}" ] || failures=$((failures + 1))
[ "${authority_tokens}" -le "${MAX_CURRENT_AUTHORITY_TOKENS}" ] || failures=$((failures + 1))
if [ -n "${BASE_REF}" ] && git rev-parse --verify --quiet "${BASE_REF}^{commit}" >/dev/null; then
  base_always_bytes="$(baseline_surface_files | while IFS= read -r path; do if always_loaded_path "${path}"; then printf '%s\n' "${path}"; fi; done | while IFS= read -r path; do git cat-file -s "${BASE_REF}:${path}"; done | awk '{sum += $1} END {print sum + 0}')"
  base_always_words="$(baseline_surface_files | while IFS= read -r path; do if always_loaded_path "${path}"; then printf '%s\n' "${path}"; fi; done | while IFS= read -r path; do git show "${BASE_REF}:${path}" | wc -w; done | awk '{sum += $1} END {print sum + 0}')"
  base_bytes="$(baseline_bytes)"
  base_words="$(baseline_words)"
  echo "  comparison: ${BASE_REF}"
  printf '  always-loaded delta: %s words, %s bytes\n' \
    "${current_always_words}" "$(delta "${base_always_words}" "${current_always_words}")" \
    "${current_always_bytes}" "$(delta "${base_always_bytes}" "${current_always_bytes}")"
  printf '  current-authority delta: %s words, %s bytes\n' \
    "${current_words}" "$(delta "${base_words}" "${current_words}")" \
    "${current_bytes}" "$(delta "${base_bytes}" "${current_bytes}")"
elif [ -n "${BASE_REF}" ]; then
  echo "  comparison: ${BASE_REF} unavailable locally"
fi

echo
if [ "${failures}" -eq 0 ]; then
  echo "hygiene: clean"
else
  echo "hygiene: ${failures} deterministic gate(s) failed" >&2
fi
exit "${failures}"
