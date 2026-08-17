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

# 2. envsync — re-encrypt any changed project.env → .env.sops and STAGE it (secrets never in
#    plaintext). envsync no longer commits; nightly owns the single commit below so an
#    env-only night can't strand an unpushed .env.sops on a discarded branch.
./scripts/envsync.sh || true

# 3. render the Obsidian docs from fresh inventory
./scripts/render-docs.sh || true

# 4. decide if there's anything to report. Stage inventory/docs; envsync already staged any
#    changed compose/*/.env.sops, and this check folds all of it into one commit.
git add -A inventory docs/generated 2>/dev/null || true
if git diff --cached --quiet; then
  echo "no inventory/doc/env changes tonight — nothing to report"
  git checkout "${DEFAULT_BRANCH}" --quiet 2>/dev/null || true
  exit 0
fi

# 5. episodic memory: append a RAW journal session entry for tonight (journal/README.md). The
#    deterministic path writes only concrete facts — the diff stat, no LLM narrative — which is
#    exactly right: raw episodes, summarized at read time, never at write time. Uniquify the
#    filename if a second run lands the same day (episodes are append-only, never overwritten).
JDIR="journal/${DATE%%-*}"; mkdir -p "${JDIR}"
JENTRY="${JDIR}/${DATE}-session-nightly.md"; n=2
while [ -e "${JENTRY}" ]; do JENTRY="${JDIR}/${DATE}-session-nightly-${n}.md"; n=$((n+1)); done
DIFFSTAT="$(git diff --cached --stat | tail -30)"
{
  printf -- '---\ndate: %s\nkind: session\ntitle: nightly %s (deterministic)\ntier_touched: [T1]\ngrants: []\nrefs: [runbooks/nightly.md, "%s"]\n---\n\n' \
    "${DATE}" "${DATE}" "${BRANCH}"
  printf '# %s · session · nightly (deterministic path)\n\n' "${DATE}"
  printf 'Report-only nightly ran the deterministic fallback (no LLM this run): `bin/ops collect`\n(T1 read-only), `envsync`, `render-docs`. Raw — no narrative, no `05-state-of-the-lab.md`,\nno grant audit (those need the agent path).\n\n'
  printf '## What changed (staged this run)\n\n```\n%s\n```\n\n' "${DIFFSTAT}"
  printf '## Graveyard — tried & abandoned\n\n— nothing abandoned (a clean deterministic pass) —\n\n'
  printf '## Follow-ups / open threads\n\n- Agent-path nightly would add the narrative + grant audit this raw entry omits.\n'
} > "${JENTRY}"
git add "${JENTRY}"

git commit -q -m "nightly ${DATE}: inventory + docs + encrypted env refresh + journal (report-only)"
git push -u origin "${BRANCH}" --quiet

# Summarise the diff for the PR body (inventory, docs, and any re-encrypted env layer).
summary="$(git diff --stat "origin/${DEFAULT_BRANCH}...${BRANCH}" -- inventory docs/generated compose | tail -25)"
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
