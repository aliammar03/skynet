#!/usr/bin/env bash
# nightly-automerge.sh — the deterministic merge-gate carve-out (system-design §2b, ADR 0004).
# The ONE place the nightly's own PR may reach main without a human. Called by BOTH nightly paths:
#   - scripts/nightly.sh (the deterministic fallback), and
#   - bin/ops nightly (after the LLM engine opens the PR — the LLM never merges; this dumb gate does).
# Keeping it in one dumb executor is the safety: the merge decision is literal path + CI + head
# validation, never LLM judgement. It fails CLOSED — any doubt leaves the PR open.
#
# USAGE: nightly-automerge.sh <pr-number-or-url-or-branch>
#   The caller supplies the exact PR or branch it opened. OPS_NIGHTLY_BRANCH, when set by bin/ops,
#   must match that PR's head exactly. There is deliberately no "latest nightly PR" fallback.
#
# Merges (squash + delete branch) IFF all hold:
#   (a) the supplied open PR is an inventory/<date> nightly (and its head matches OPS_NIGHTLY_BRANCH),
#   (b) every changed path is generated-only — inventory/, docs/generated/, journal/, or
#       compose/*/.env.sops (encrypted env),
#   (c) CI has at least one passing check and no other state, and
#   (d) the head is unchanged from validation through merge.
# Off-switch: OPS_NIGHTLY_AUTOMERGE=0 (leave open); =dry rehearses the identity + allowlist only.
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_DIR}"

DATE="$(date +%Y-%m-%d)"
mode="${OPS_NIGHTLY_AUTOMERGE:-1}"
[ "${mode}" = 0 ] && { echo "automerge: disabled (OPS_NIGHTLY_AUTOMERGE=0) — PR left open"; exit 0; }

pr_ref="${1:-}"
[ -n "${pr_ref}" ] || { echo "automerge: exact PR number or URL is required — left open"; exit 0; }

# Resolve the explicit PR once. A fetch failure, incomplete JSON, a closed PR, or a branch outside
# today's nightly namespace is not safe enough to continue. The expected branch from bin/ops adds a
# stronger identity check for agent-path nightlies.
read_pr() {
  local meta
  meta="$(gh pr view "${pr_ref}" --json number,state,headRefName,headRefOid \
    --jq '[.number, .state, .headRefName, .headRefOid] | @tsv' 2>/dev/null)" || return 1
  IFS=$'\t' read -r pr_number pr_state pr_branch pr_head <<<"${meta}"
  [ -n "${pr_number:-}" ] && [ -n "${pr_state:-}" ] && [ -n "${pr_branch:-}" ] && [ -n "${pr_head:-}" ]
}

if ! read_pr; then
  echo "automerge: could not resolve complete PR identity — left open"
  exit 0
fi
if [ "${pr_state}" != OPEN ]; then
  echo "automerge: PR #${pr_number} is not open — left open"
  exit 0
fi
if [[ "${pr_branch}" != "inventory/${DATE}"* ]]; then
  echo "automerge: PR #${pr_number} is not today's nightly branch — left open"
  exit 0
fi
if [ -n "${OPS_NIGHTLY_BRANCH:-}" ] && [ "${pr_branch}" != "${OPS_NIGHTLY_BRANCH}" ]; then
  echo "automerge: PR #${pr_number} head is not the expected nightly branch — left open"
  exit 0
fi
expected_branch="${pr_branch}"
expected_head="${pr_head}"

# Ask GitHub for the PR's own file list so this works regardless of local checkout state. Retrieval
# and filtering are intentionally separate: an API failure and an empty response never mean "allowed".
files="$(mktemp)"
trap 'rm -f "${files}"' EXIT
if ! gh pr diff "${pr_number}" --name-only >"${files}" 2>/dev/null; then
  echo "automerge: could not retrieve changed files — left open"
  exit 0
fi
if [ ! -s "${files}" ]; then
  echo "automerge: changed-file list is empty or incomplete — left open"
  exit 0
fi
stray="$(grep -vE '(^inventory/|^docs/generated/|^journal/|^compose/[^/]+/\.env\.sops$)' "${files}" || :)"
if [ -n "${stray}" ]; then
  echo "automerge: PR #${pr_number} touches non-generated paths — left open for human review:"
  echo "${stray}"
  exit 0
fi

# Dry-run — prove identity + allowlist without touching CI or merging.
if [ "${mode}" = dry ]; then
  echo "automerge: DRY-RUN (OPS_NIGHTLY_AUTOMERGE=dry) — generated-only; would wait for CI then squash-merge #${pr_number}"
  exit 0
fi

# Green-gate — wait for completion, then demand a non-empty all-pass readback. A missing check set
# is not evidence of green CI. Both calls are against this exact PR and the head is checked again
# immediately afterward before merge.
echo "automerge: generated-only — waiting for CI on #${pr_number}…"
if ! gh pr checks "${pr_number}" --watch --interval 20 >/dev/null 2>&1; then
  echo "automerge: CI not green — #${pr_number} left open for review"
  exit 0
fi
if ! gh pr checks "${pr_number}" --json bucket --jq \
  'if length > 0 and all(.[]; .bucket == "pass") then "green" else empty end' 2>/dev/null \
  | grep -qx green; then
  echo "automerge: CI checks missing or not all green — #${pr_number} left open for review"
  exit 0
fi
if ! read_pr \
  || [ "${pr_state}" != OPEN ] \
  || [ "${pr_branch}" != "${expected_branch}" ] \
  || [ "${pr_head}" != "${expected_head}" ]; then
  echo "automerge: PR identity or head changed during validation — left open"
  exit 0
fi

# --match-head-commit binds the mutation to the head that passed both earlier gates. gh can report a
# nonzero local branch cleanup after the remote merge, so verify actual PR state rather than its exit.
gh pr merge "${pr_number}" --squash --delete-branch --match-head-commit "${expected_head}" >/dev/null 2>&1 || true
if [ "$(gh pr view "${pr_number}" --json state --jq .state 2>/dev/null)" = MERGED ]; then
  echo "automerge: merged #${pr_number} (generated-only, CI green, validated head)"
else
  echo "automerge: merge call failed — #${pr_number} left open"
fi
