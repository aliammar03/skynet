---
date: 2026-08-20
kind: decision          # session | incident | decision
title: Turn the merge-gate dial: nightly auto-merges its own generated-only PRs
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-005, "PR #88", "PR #89", "ADR 0004"]   # SKY-###, PR #NNN, ADR NNNN, hosts
---

# 2026-08-20 · decision · Turn the merge-gate dial: nightly auto-merges its own generated-only PRs

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (SKY-006 / journal/README.md). Distillation happens at READ time, never here. -->

## What happened
Came out of the nightly-failure investigation. While looking at the failed unit, Ali pointed out the
deterministic nightly is "pretty useless for automation if it just keeps filling a PR backlog" — the
nightly opens an `inventory/<date>` PR every night (latest was #89) and nobody drains them.

Checked the constitution before proposing anything: `docs/system-design.md` §2b already frames the
merge gate as a version-controlled dial and names its "foreseeable first loosening" as
"the agent auto-merging docs-only PRs"; `docs/design/gitops-loop.md` had it under "Planned expansion."
So this was a sanctioned dial-turn, not a new policy.

Scope was negotiated with Ali across a few messages:
- allowlist starts as inventory/ + docs/generated/ + journal/ → Ali said **fold sops in** too, so
  `compose/*/.env.sops` (exactly what `envsync.sh` stages — confirmed `out="compose/${svc}/.env.sops"`)
  joined the list. `.sops.yaml` (config) deliberately NOT matched (different suffix).
- branch protection: Ali asked how to set it. Tried `gh api -X PUT .../branches/main/protection` →
  `404`. Root cause: the ops `gh` is authed as `aliammar-skynet` with `admin:false` (push+triage only)
  — a non-admin collaborator can't set protection (GitHub returns 404, not 403). The agent literally
  can't reconfigure its own guardrails — correct posture.
- Ali tried the web UI as owner `aliammar03` → GitHub: "Your rulesets won't be enforced on this
  private repository until you move to a Team org." Free plan + private repo = no enforced protection.
  Upgrading / going public both rejected (repo carries topology + sops blobs, correctly private).
  → **decided: no branch protection; the green-gate in the nightly script IS the enforcement (option 4).**

## Actions & outcomes
- `scripts/nightly.sh` → added `automerge()`: (a) path-allowlist filter via
  `git diff --name-only origin/main...BRANCH | grep -vE '(^inventory/|^docs/generated/|^journal/|^compose/[^/]+/\.env\.sops$)'`
  — non-empty ⇒ leave open; (b) `gh pr checks <pr> --watch` green-gate ⇒ `gh pr merge --squash --delete-branch`.
  Guarded by `OPS_NIGHTLY_AUTOMERGE` (default on). Captured `PR_URL` from `gh pr create`; checkout main
  BEFORE automerge so `--delete-branch` can drop the local branch.
- `docs/system-design.md` §2b → dial moved from "human merge, today / foreseeable loosening" to
  "one carve-out taken: generated-only nightly PRs, CI-green only." Line ~112 publish-gate wording
  tightened to "never self-merges an *authored* PR."
- `AGENTS.md` → §3 auto-approve list gets its **first entry** (was empty); §0 and §6 parentheticals
  qualified to "authored" self-merge.
- `docs/design/gitops-loop.md` → "Docs-only auto-merge" moved from Planned → **shipped** (generated-only).
- `docs/decisions/0004-auto-merge-generated-only-nightly-prs.md` → this ADR.
- Off-switch documented in live `~/.config/skynet-ops/ops.env`; the tracked `ops.env.example` hint
  deferred to a follow-up because **PR #88 is still open and rewrites that same file** — editing it
  here would guarantee a conflict.

## Graveyard — tried & abandoned
- `gh api -X PUT .../branches/main/protection` as the ops account → 404, abandoned: non-admin token.
- GitHub rulesets/branch-protection → abandoned: not enforced on a private repo on the free plan.
- Requiring PR *approvals* in protection → abandoned in design: would lock the nightly out of its own
  merge (it can't and shouldn't approve itself). Required *checks* with **zero** approvals was the shape.
- Editing `scripts/systemd/ops.env.example` in this PR → deferred, not done: PR #88 rewrites it; avoid
  the conflict.

## Follow-ups / open threads
- After #88 merges: add the `OPS_NIGHTLY_AUTOMERGE=0` hint line to `ops.env.example` (own-line comment).
- First live proof pending: next timer run (Fri 2026-08-21 03:36 UTC) is LLM/engine-dependent; the
  clean test is a deterministic nightly opening a generated-only PR and watching `automerge()` merge it green.
- Considered but not done: a pre-commit lint (`grep -E '^[A-Z_]+=.*#' scripts/systemd/*.env*`) to kill
  the inline-comment class from #88 permanently — still parked until it recurs.
