---
date: 2026-09-13
time: 11:46:39            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: SKY-025 P8 embargo documentation reconciliation
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-025, "PR #255", "ADR 0004"] # SKY-###, PR #NNN, ADR NNNN, hosts — anything to cross-link
thread_status: none     # none | open | resolved | unknown; digest shows only explicit open
# resolves: [<episode-basename>, …]   # optional: close earlier episodes' open threads (append-only-safe)
---

# 2026-09-13 · session · SKY-025 P8 embargo documentation reconciliation

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (journal/README.md). Distillation happens at READ time, never here. -->

## What happened
The independent review of PR #255 at head `046a901b14fd2c318d840bb36f06c462033da2f6`
found that the test/CI embargo was functionally implemented but several current-authority documents
still described deleted tests or active CI/auto-merge in present tense. The review identified the
SKY-025 map, ADR 0004, and Nix README directly and required a scan of the other current surfaces.

No runtime/package behavior, test asset, workflow, or nightly executor behavior changed in this fix.

## Actions & outcomes
- Removed deleted shell/collection/query tests from the SKY-025 current caller map → current callers
  now name installed/manual and renderer/query contracts only.
- Rewrote ADR 0004 around the current suspended Decision and Consequences → all PRs require human
  merge now; historical rationale and strict restoration prerequisites remain.
- Replaced the Nix README's deterministic-CI phrase with manual retained-snapshot inspection → absent
  CI is no longer described as a consumer.
- Scanned the current repository surface → found and repaired the same stale self-merge/CI claims in
  README, Git conventions, review/execute prompts, capability/layout doctrine, related ADRs, and active
  directive ownership notes.
- Left journal/history statements about prior tests and CI unchanged when they described past events.
- Confirmed `tests/` and `.github/workflows/` remain absent → the documentation repair did not restore
  embargoed assets.
- Scanned current authority for the rejected present-tense phrases and inspected the required
  constitution/doctrine/runbook/directive/map/Nix/memory set → no deleted test is named as a live
  caller/gate, absent CI is not described as running, and every PR remains human-merged.
- Inspected and invoked `scripts/nightly-automerge.sh` → seven-line fail-closed stub, no merge path,
  and explicit human-merge output.
- Ran `git diff --check`, repository-surface classification, secret scan, and hard invariants → all
  passed.

## Graveyard — tried & abandoned
- — nothing abandoned —

## Follow-ups / open threads
- Publish the documentation repair to PR #255 and stop for Ali to start a fresh review.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
