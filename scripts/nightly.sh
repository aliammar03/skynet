#!/usr/bin/env bash
# nightly.sh — deterministic report-only nightly pass (plan §9/§11, A5).
# Runs on vm-skynet-ops. Serves two roles:
#   1. the FALLBACK when the LLM engine can't run (see bin/ops nightly), and
#   2. a standalone report-only pass for anyone who prefers no-LLM.
# It is pure scripts: refresh inventory (T1), envsync, render docs, then open a PR with the
# diff. It NEVER makes a T2 write or granted-root change. It self-merges ONLY its own
# generated-only PR, and only when CI is green — the merge-gate carve-out (system-design §2b);
# it never self-merges an authored change. Off-switch: OPS_NIGHTLY_AUTOMERGE=0 (=dry to rehearse).
#
# What it deliberately can't do (needs an LLM or a root grant): the narrative PROSE of
# docs/generated/05-state-of-the-lab.md (LLM) and the root-grant audit harvest (root). Both
# are left to the agent-driven nightly; this pass leaves the existing 05 narrative prose in place
# but DOES regenerate the deterministic agent digest 06-agent-digest.md (scripts/render-digest.sh).
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

# 3b. regenerate the agent cold-boot digest 06-agent-digest.md (recent decisions / open threads /
#     recent episodes). Deterministic + read-only sources, so it runs even on this LLM-free path —
#     the digest POINTERS stay current even when the human 05 narrative goes stale.
./scripts/render-digest.sh || true

# 3c. regenerate the context map 07-context-map.md (what's loadable + what it costs). Deterministic
#     and read-only, so it stays fresh on this LLM-free path too — the default-lean routing index.
./scripts/render-context-map.sh || true

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

# 6. Auto-merge — the merge-gate carve-out (docs/system-design.md §2b, ADR 0004). The nightly may
#    self-merge its OWN PR, but ONLY when every changed path is generated/encrypted AND CI is green.
#    No branch protection backstops this (private repo on the free plan), so the green-gate below IS
#    the safety and is deliberately strict: one stray authored path, or a red/pending check, and the
#    PR is left open for a human — exactly the old behaviour. Off-switch: OPS_NIGHTLY_AUTOMERGE=0;
#    OPS_NIGHTLY_AUTOMERGE=dry rehearses the allowlist decision without CI or merging.
automerge() {
  # OPS_NIGHTLY_AUTOMERGE: 0 = off (PR left open), dry = rehearse the decision without merging,
  # anything else (incl. unset) = on.
  local mode="${OPS_NIGHTLY_AUTOMERGE:-1}"
  [ "${mode}" = 0 ] && { echo "automerge: disabled (OPS_NIGHTLY_AUTOMERGE=0) — PR left open"; return; }
  local pr="$1"
  # (a) path allowlist — generated inventory/docs, a journal episode, or a sops-encrypted env blob.
  #     Anything else means a human reasoned about it; hand it back to a human.
  local stray
  stray="$(git diff --name-only "origin/${DEFAULT_BRANCH}...${BRANCH}" \
    | grep -vE '(^inventory/|^docs/generated/|^journal/|^compose/[^/]+/\.env\.sops$)' || true)"
  if [ -n "${stray}" ]; then
    echo "automerge: PR touches non-generated paths — left open for human review:"; echo "${stray}"; return
  fi
  # Dry-run — prove the decision (allowlist passed ⇒ generated-only) without touching CI or merging.
  # `OPS_NIGHTLY_AUTOMERGE=dry` exercises the gate on a real PR without waiting for the 03:36 timer.
  if [ "${mode}" = dry ]; then
    echo "automerge: DRY-RUN (OPS_NIGHTLY_AUTOMERGE=dry) — generated-only; would wait for CI then squash-merge ${pr}"; return
  fi
  # (b) green-gate — `gh pr checks --watch` blocks until every check completes, then exits nonzero
  #     if any failed (verified: all-pass → exit 0). Merge only on a clean pass; else leave the PR open.
  echo "automerge: generated-only — waiting for CI on ${pr}…"
  if gh pr checks "${pr}" --watch --interval 20 >/dev/null 2>&1; then
    gh pr merge "${pr}" --squash --delete-branch \
      && echo "automerge: merged ${pr} (generated-only, CI green)" \
      || echo "automerge: merge call failed — ${pr} left open"
  else
    echo "automerge: CI not green — ${pr} left open for review"
  fi
}

# Summarise the diff for the PR body (inventory, docs, and any re-encrypted env layer).
summary="$(git diff --stat "origin/${DEFAULT_BRANCH}...${BRANCH}" -- inventory docs/generated compose | tail -25)"
PR_URL="$(gh pr create --base "${DEFAULT_BRANCH}" --head "${BRANCH}" \
  --title "nightly ${DATE}: inventory + docs (report-only)" \
  --body "Automated report-only nightly (deterministic path — no LLM this run).

Refreshed inventory (T1 collectors), envsync, and re-rendered \`docs/generated/\`.

\`\`\`
${summary}
\`\`\`

Generated-only, so this **auto-merges once CI is green** (merge-gate dial §2b; off-switch
\`OPS_NIGHTLY_AUTOMERGE=0\`). Not done by this path: the narrative \`05-state-of-the-lab.md\`
(agent-authored) and the root-grant audit (needs a grant). 🤖 nightly" \
  2>&1 | tail -1)" || PR_URL=""

# Back to the default branch before merge/cleanup so --delete-branch can drop the local branch too.
git checkout "${DEFAULT_BRANCH}" --quiet 2>/dev/null || true

case "${PR_URL}" in
  https://*) echo "opened ${PR_URL}"; automerge "${PR_URL}" ;;
  *)         echo "PR create skipped/failed (check gh auth): ${PR_URL}" ;;
esac

echo "nightly (deterministic) complete"
