---
date: 2026-09-07
time: 18:54:24            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: SKY-025 P3a context budget approval
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-025, "PR #215"]
thread_status: open
---

# 2026-09-07 · session · SKY-025 P3a context budget approval

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (journal/README.md). Distillation happens at READ time, never here. -->

## What happened
Ali said “up the limit to 200,000” after the P3a draft PR recorded a current-authority
budget failure at 171,518/170,000 estimated tokens. This authorizes the scoped policy change
in `scripts/hygiene.sh` on `phase/sky-025-p3a`. The earlier
[P3a episode](2026-09-07-session-sky-025-p3a-isolated-core-collector.md) remains append-only;
its budget blocker is resolved by this instruction and implementation.

## Actions & outcomes
- Changed default `MAX_CURRENT_AUTHORITY_TOKENS` from 170000 to 200000.
  `MAX_ALWAYS_LOADED_TOKENS` remains 6500; no environment override was used.
- Staged `scripts/hygiene.sh`; `.githooks/pre-commit` exited 0, including the previously
  failing hygiene command. No Python code changed; the prior 61 passing tests,
  Ruff/mypy and packaged checks remain applicable.
- Updated the directive/map to implementation-complete/review-pending and PR #215 for
  human review. Accepted progress remains 2/24. No production, credentials, live callers,
  service/timers or host profiles changed; no authored merge performed.

## Graveyard — tried & abandoned
- No new failed approach. The earlier budget failure and draft-publication bypass remain
  recorded in the preceding episode; this follow-up uses the normal commit hook.

## Follow-ups / open threads
- After Ali merges PR #215, start a fresh Astra Medium session: Read planning/prompts/review.md
  and review SKY-025 implementation PR https://github.com/aliammar03/skynet/pull/215.
  P3b remains unreleased. The earlier budget-pruning follow-up is satisfied by Ali's approval.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
