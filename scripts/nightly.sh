#!/usr/bin/env bash
# nightly.sh — deterministic report-only nightly pass (plan §9/§11, A5).
# Runs on vm-skynet-ops. Serves two roles:
#   1. the FALLBACK when the LLM engine can't run (see bin/ops nightly), and
#   2. a standalone report-only pass for anyone who prefers no-LLM.
# It is pure scripts: refresh inventory (T1), envsync, render docs, then open a PR with the
# diff. It NEVER makes a T2 write or granted-root change, and it never merges.
#
# What it deliberately can't do (needs an LLM or a root grant): the narrative
# docs/generated/05-state-of-the-lab.md (LLM) and the root-grant audit harvest (root). Both
# are left to the agent-driven nightly; this pass leaves any existing narrative in place.
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_DIR}"

DATE="$(date +%Y-%m-%d)"
BRANCH="inventory/${DATE}"
DEFAULT_BRANCH="${OPS_DEFAULT_BRANCH:-main}"

echo "== nightly (deterministic) ${DATE} =="

# Stay on a fresh branch off the latest main so nightlies don't pile on each other.
git fetch origin "${DEFAULT_BRANCH}" --quiet || true
git checkout -B "${BRANCH}" "origin/${DEFAULT_BRANCH}" 2>/dev/null || git checkout -B "${BRANCH}"

# 1. refresh inventory (each collector is idempotent + read-only; no creds = exit 0)
./bin/ops collect || true

# 2. envsync — re-encrypt any changed project.env → .env.sops (secrets never in plaintext)
./scripts/envsync.sh || true

# 3. render the Obsidian docs from fresh inventory
./scripts/render-docs.sh || true

# 4. commit + PR if anything changed
git add -A inventory docs/generated 2>/dev/null || true
if git diff --cached --quiet; then
  echo "no inventory/doc changes tonight — nothing to report"
  git checkout "${DEFAULT_BRANCH}" --quiet 2>/dev/null || true
  exit 0
fi

git commit -q -m "nightly ${DATE}: inventory refresh + rendered docs (report-only)"
git push -u origin "${BRANCH}" --quiet

# Summarise the diff for the PR body.
summary="$(git diff --stat "origin/${DEFAULT_BRANCH}...${BRANCH}" -- inventory docs/generated | tail -25)"
gh pr create --base "${DEFAULT_BRANCH}" --head "${BRANCH}" \
  --title "nightly ${DATE}: inventory + docs (report-only)" \
  --body "Automated report-only nightly (deterministic path — no LLM this run).

Refreshed inventory (T1 collectors), envsync, and re-rendered \`docs/generated/\`.

\`\`\`
${summary}
\`\`\`

Not done by this path: the narrative \`05-state-of-the-lab.md\` (agent-authored) and the
root-grant audit (needs a grant). Review the diff; merge if it looks right. 🤖 nightly" \
  2>&1 | tail -1 || echo "PR create skipped/failed (check gh auth)"

git checkout "${DEFAULT_BRANCH}" --quiet 2>/dev/null || true
echo "nightly (deterministic) complete"
