---
date: 2026-09-13
time: 10:57:06            # local HH:MM:SS; orders same-day episodes in the digest
kind: decision          # session | incident | decision
title: SKY-025 repository test and GitHub CI embargo
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-025, "PR #255", "ADR 0004"] # SKY-###, PR #NNN, ADR NNNN, hosts — anything to cross-link
thread_status: open     # none | open | resolved | unknown; digest shows only explicit open
# resolves: [<episode-basename>, …]   # optional: close earlier episodes' open threads (append-only-safe)
---

# 2026-09-13 · decision · SKY-025 repository test and GitHub CI embargo

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (journal/README.md). Distillation happens at READ time, never here. -->

## What happened
During attempted accepted closeout for SKY-025 P8, `tests/test_agent_docs.py` failed two lifecycle
assertions because the accepted test tree hard-coded P7/P8-review-pending state. Ali directed that all
GitHub CI and repository tests be purged until SKY-025 finishes. His reason was that phase-by-phase
repair of colliding transitional assertions was producing cross-cutting test spaghetti; he will review
the repository and implement a coherent test architecture after the transition.

The change was applied to the existing P8 branch/PR #255. It is substantive and therefore invalidates
the earlier ACCEPT marker. No closeout or merge was attempted.

## Actions & outcomes
- Deleted both `.github/workflows/` definitions and every tracked file under `tests/`, including API
  fixtures → no GitHub CI workflow or repository test suite remains.
- Removed pytest configuration/dependency, packaged test inputs/check phase, pre-commit test calls, and
  hygiene test calls → deleted tests are not invoked by current build/operator paths.
- Retained local secret scanning, `invariants.json` enforcement, Ruff, mypy, package builds, deploy-rs
  schema validation, and focused smoke checks → hard safety controls and non-test inspection remain.
- Replaced the nightly auto-merge executor with a fail-closed compatibility stub and updated the
  constitution/operating contract → every PR is human-merged while CI evidence is absent.
- Updated current docs, runbook, directive, prompts, subsystem map, and agent memory → the embargo and
  post-transition replacement owner are explicit.
- Ran retained secret/invariant controls, Ruff, strict mypy, Nix package build, Bash syntax, diff, and
  repository-surface checks → all passed.
- Ran packaged doctor, entity audit, and cache query smoke commands → doctor succeeded; entity audit
  returned zero holes across 39 records; the cache reported 11 containers.
- Ran `bin/ops entities` through its normal freshness gate → it refused because this construction
  worktree has no matching current collection receipts, rather than consuming retained inventory as
  current evidence.
- Ran `scripts/hygiene.sh` → its retained repository-surface check passed, but the command exited 1 on
  the existing current-authority budget (220,996 estimated tokens against the configured 200,000).

## Graveyard — tried & abandoned
- Incrementally repairing the two lifecycle assertions for accepted closeout → abandoned on Ali's
  direction because repeated phase-specific repairs were making the transition suite incoherent.

## Follow-ups / open threads
- After SKY-025 finishes, Ali reviews the repository and authors one coherent replacement test/CI
  architecture.
- PR #255 requires a fresh external review because the pre-embargo ACCEPT marker is stale.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
