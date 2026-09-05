#!/usr/bin/env bash
# gitops-rollback.sh — the L7 rollback executor for a Compose deploy (SKY-018 P6).
#
# The dumb executor ADR 0005 §3 requires: it reverts a deploy by `git revert`-ing the deploy commit
# and letting Arcane reconcile the service back from git. It needs no agent judgement — it re-applies
# a known-good git state — and works precisely when the agent's plan is the thing that failed. The
# DECISION to roll back is made by scripts/deploy-gate.sh (deterministic health probe); this script
# only performs the revert once told to.
#
# The default gate path only reports the deterministic failure. It must not mutate the checkout that
# deployed the service: even a local revert commit on a shared/main checkout is an unsafe surprise.
# An operator may explicitly request --prepare; that creates the revert in an isolated review branch
# using a temporary worktree. A human reviews/pushes/merges that branch, then Arcane reconciles.
#
# TIER: T2 — default is report-only; --prepare creates an isolated local review branch. Publication
# remains human-merged.
# USAGE:
#   gitops-rollback.sh <service> <deploy-commit> [--prepare]
#     <service>        directory under compose/ (matches the Arcane project name)
#     <deploy-commit>  the commit that deployed the bad change (its inverse is applied)
#     --prepare        explicitly create the revert in a temporary worktree on a review branch
set -euo pipefail
SVC="${1:?usage: gitops-rollback.sh <service> <deploy-commit> [--prepare]}"
COMMIT="${2:?need the deploy commit to revert}"
[ "${3:-}" = "" ] || [ "${3:-}" = "--prepare" ] || {
  echo "gitops-rollback: unknown option '$3' (only explicit --prepare is allowed)" >&2
  exit 2
}
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

git rev-parse --verify "${COMMIT}^{commit}" >/dev/null 2>&1 || { echo "gitops-rollback: '${COMMIT}' is not a commit" >&2; exit 1; }

if [ "${3:-}" != "--prepare" ]; then
  echo "==> gitops-rollback: ${SVC} unhealthy; no git mutation performed" >&2
  echo "==> operator action: run gitops-rollback.sh ${SVC} ${COMMIT} --prepare, review the branch, then open/merge its PR" >&2
  exit 3
fi

base_branch="$(git branch --show-current)"
[ -n "${base_branch}" ] || base_branch="main"
slug="$(printf '%s-%s' "${SVC}" "${COMMIT:0:12}" | tr -c 'A-Za-z0-9._/-' '-')"
branch="rollback/${slug}"
worktree="$(mktemp -d "${TMPDIR:-/tmp}/skynet-rollback.XXXXXX")"
rmdir "${worktree}"
cleanup() { git worktree remove --force "${worktree}" >/dev/null 2>&1 || true; }
trap cleanup EXIT
git show-ref --verify --quiet "refs/heads/${branch}" && {
  echo "gitops-rollback: review branch ${branch} already exists; inspect it instead of overwriting" >&2
  exit 4
}
git worktree add -b "${branch}" "${worktree}" "${base_branch}" >/dev/null
echo "==> gitops-rollback: preparing ${branch} in isolated worktree"
# --no-edit: deterministic message; -m 1 handles a merged deploy commit relative to main.
if git rev-parse -q --verify "${COMMIT}^2" >/dev/null 2>&1; then
  git -C "${worktree}" revert --no-edit -m 1 "${COMMIT}"
else
  git -C "${worktree}" revert --no-edit "${COMMIT}"
fi
echo "==> gitops-rollback: ${branch} prepared; review, push, and human-merge its PR before Arcane reconciles" >&2
