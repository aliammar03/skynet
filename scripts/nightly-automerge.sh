#!/usr/bin/env bash
# nightly-automerge.sh — the deterministic merge-gate carve-out (system-design §2b, ADR 0004).
# The ONE place the nightly's own PR may reach main without a human. Called by BOTH nightly paths:
#   - scripts/nightly.sh (the deterministic fallback), and
#   - bin/ops nightly (after the LLM engine opens the PR — the LLM never merges; this dumb gate does).
# Keeping it in one dumb executor is the safety: the merge decision is a literal path filter plus
# `gh pr checks`' own exit status, never LLM judgement. It fails CLOSED — any doubt leaves the PR open.
#
# USAGE: nightly-automerge.sh [<pr-number-or-url>]
#   No arg → derive the PR from the branch inventory/$(date +%F) (the agent-path convention).
#
# Merges (squash + delete branch) IFF both hold:
#   (a) every changed path is generated-only — inventory/, docs/generated/, journal/, or
#       compose/*/.env.sops (encrypted env). One path outside → left open for a human.
#   (b) CI is green — `gh pr checks --watch` blocks to completion, nonzero on any failure.
# Off-switch: OPS_NIGHTLY_AUTOMERGE=0 (leave open); =dry rehearses the allowlist without CI/merge.
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_DIR}"

DATE="$(date +%Y-%m-%d)"

mode="${OPS_NIGHTLY_AUTOMERGE:-1}"
[ "${mode}" = 0 ] && { echo "automerge: disabled (OPS_NIGHTLY_AUTOMERGE=0) — PR left open"; exit 0; }

# Resolve the PR. An explicit ref wins; otherwise find the open PR for tonight's branch.
pr="${1:-}"
if [ -z "${pr}" ]; then
  pr="$(gh pr list --head "inventory/${DATE}" --state open --json number --jq '.[0].number' 2>/dev/null || true)"
fi
[ -z "${pr}" ] && { echo "automerge: no PR found for inventory/${DATE} — nothing to merge"; exit 0; }

# (a) path allowlist — generated inventory/docs, a journal episode, or a sops-encrypted env blob.
#     Ask GitHub for the PR's own file list so this works regardless of local checkout state.
stray="$(gh pr diff "${pr}" --name-only 2>/dev/null \
  | grep -vE '(^inventory/|^docs/generated/|^journal/|^compose/[^/]+/\.env\.sops$)' || true)"
if [ -n "${stray}" ]; then
  echo "automerge: PR #${pr} touches non-generated paths — left open for human review:"; echo "${stray}"; exit 0
fi

# Dry-run — prove the decision (allowlist passed ⇒ generated-only) without touching CI or merging.
if [ "${mode}" = dry ]; then
  echo "automerge: DRY-RUN (OPS_NIGHTLY_AUTOMERGE=dry) — generated-only; would wait for CI then squash-merge #${pr}"; exit 0
fi

# (b) green-gate — blocks until every check completes, then exits nonzero if any failed.
echo "automerge: generated-only — waiting for CI on #${pr}…"
if gh pr checks "${pr}" --watch --interval 20 >/dev/null 2>&1; then
  gh pr merge "${pr}" --squash --delete-branch \
    && echo "automerge: merged #${pr} (generated-only, CI green)" \
    || echo "automerge: merge call failed — #${pr} left open"
else
  echo "automerge: CI not green — #${pr} left open for review"
fi
