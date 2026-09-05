#!/usr/bin/env bash
# repo-surface.sh — classify tracked repository text into one authority surface for local gates.
# TIER: T1 — reads the local Git worktree only; never uses the network or changes repository/live state.
# USAGE: source scripts/repo-surface.sh; repo_surface_files <class>; or scripts/repo-surface.sh check.
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

repo_surface_is_text() {
  [ -f "$1" ] && LC_ALL=C grep -Iq '' "$1"
}

repo_surface_classify_path() {
  local path="$1" matches=() class
  case "${path}" in
    planning/*) matches+=(planning) ;;
    journal/*|docs/history/*|docs/decisions/*) matches+=(history-evidence) ;;
    docs/generated/*|inventory/*) matches+=(generated) ;;
    tests/*|fixtures/*) matches+=(fixture-test-data) ;;
    *.sops|*.age|*.gpg|*.asc) matches+=(opaque) ;;
    *) matches+=(current) ;;
  esac

  # Test-only fault injection proves the classifier fails closed for missing/overlapping rules.
  if [ "${REPO_SURFACE_TEST_FORCE_UNCLASSIFIED:-}" = "${path}" ]; then matches=(); fi
  if [ -n "${REPO_SURFACE_TEST_EXTRA_CLASS:-}" ] && [ "${REPO_SURFACE_TEST_EXTRA_CLASS%%:*}" = "${path}" ]; then
    class="${REPO_SURFACE_TEST_EXTRA_CLASS#*:}"
    matches+=("${class}")
  fi

  if [ "${#matches[@]}" -ne 1 ]; then
    printf 'repo-surface: %s has %s classifications (%s)\n' "${path}" "${#matches[@]}" "${matches[*]:-none}" >&2
    return 1
  fi
  printf '%s\n' "${matches[0]}"
}

repo_surface_files() {
  local wanted="$1" path class
  cd "${REPO_DIR}"
  while IFS= read -r path; do
    repo_surface_is_text "${path}" || continue
    class="$(repo_surface_classify_path "${path}")" || return 1
    [ "${class}" = "${wanted}" ] && printf '%s\n' "${path}"
  done < <(git ls-files | sort)
}

repo_surface_check() {
  local path
  cd "${REPO_DIR}"
  while IFS= read -r path; do
    repo_surface_is_text "${path}" || continue
    repo_surface_classify_path "${path}" >/dev/null || return 1
  done < <(git ls-files | sort)
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  case "${1:-check}" in
    check) repo_surface_check ;;
    list) repo_surface_files "${2:?usage: scripts/repo-surface.sh list <class>}" ;;
    classify) repo_surface_classify_path "${2:?usage: scripts/repo-surface.sh classify <path>}" ;;
    *) echo "usage: scripts/repo-surface.sh [check|list <class>|classify <path>]" >&2; exit 2 ;;
  esac
fi
