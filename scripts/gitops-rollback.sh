#!/usr/bin/env bash
# gitops-rollback.sh — the L7 rollback executor for a Compose deploy (SKY-018 P6).
#
# The dumb executor ADR 0005 §3 requires: it reverts a deploy by `git revert`-ing the deploy commit
# and letting Arcane reconcile the service back from git. It needs no agent judgement — it re-applies
# a known-good git state — and works precisely when the agent's plan is the thing that failed. The
# DECISION to roll back is made by scripts/deploy-gate.sh (deterministic health probe); this script
# only performs the revert once told to.
#
# git revert → Arcane's Git Sync pulls the reverted compose → the service returns to its prior spec.
# That reconciler is dumb and separate (§3), so this is a real rollback, not "ask the agent to fix it".
#
# TIER: T2 — a git push + an Arcane re-sync (svc-ops, standing). No new capability.
# USAGE:
#   gitops-rollback.sh <service> <deploy-commit> [--no-push]
#     <service>        directory under compose/ (matches the Arcane project name)
#     <deploy-commit>  the commit that deployed the bad change (its inverse is applied)
#     --no-push        revert locally only (don't push) — for a branch the caller pushes itself
set -euo pipefail
SVC="${1:?usage: gitops-rollback.sh <service> <deploy-commit> [--no-push]}"
COMMIT="${2:?need the deploy commit to revert}"
PUSH=1; [ "${3:-}" = "--no-push" ] && PUSH=0
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

git rev-parse --verify "${COMMIT}^{commit}" >/dev/null 2>&1 || { echo "gitops-rollback: '${COMMIT}' is not a commit" >&2; exit 1; }

echo "==> gitops-rollback: reverting deploy commit ${COMMIT} for ${SVC}"
# --no-edit: deterministic message, no editor; -m 1 harmlessly ignored for a non-merge commit but
# lets a merged deploy commit be reverted too (revert relative to first parent = main line).
if git rev-parse -q --verify "${COMMIT}^2" >/dev/null 2>&1; then
  git revert --no-edit -m 1 "${COMMIT}"
else
  git revert --no-edit "${COMMIT}"
fi

if [ "${PUSH}" = 1 ]; then
  echo "==> pushing the revert so Arcane reconciles"
  git push
fi

# Best-effort immediate reconcile: nudge Arcane's Git Sync for this service so it pulls the revert
# now instead of on its next poll. If Arcane is unreachable the git push still converges on the poll,
# so this is a nudge, not a dependency — the rollback does not hinge on the agent or the API.
ARC_ENV="/opt/skynet-ops/secrets/arcane.env"
if [ "${GITOPS_ROLLBACK_NO_RECONCILE:-0}" != 1 ] && { [ -r "${ARC_ENV}" ] || sudo -n test -r "${ARC_ENV}" 2>/dev/null; }; then
  set -a; source <(cat "${ARC_ENV}" 2>/dev/null || sudo -n cat "${ARC_ENV}"); set +a
  ENVID="${ARCANE_ENV_ID:-0}"
  arc() { local m="$1" p="$2"; shift 2; curl -fsS -X "${m}" -H "X-API-Key: ${ARCANE_TOKEN}" "${ARCANE_URL}/api${p}" "$@"; }
  SID="$(arc GET "/environments/${ENVID}/gitops-syncs" 2>/dev/null \
        | jq -r --arg n "${SVC}" '.data[] | select(.name==$n or .projectName==$n) | .id' | head -1 || true)"
  if [ -n "${SID:-}" ]; then
    arc POST "/environments/${ENVID}/gitops-syncs/${SID}/sync" >/dev/null 2>&1 \
      && echo "==> nudged Arcane sync ${SID} for ${SVC}" \
      || echo "==> Arcane nudge failed (git push will reconcile on the next poll)" >&2
  fi
fi
echo "==> gitops-rollback: ${SVC} reverted to pre-${COMMIT} state"
