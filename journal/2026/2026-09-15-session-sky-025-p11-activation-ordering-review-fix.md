---
date: 2026-09-15
time: 01:20:49            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: SKY-025 P11 activation ordering review fix
tier_touched: []        # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-025, PR #259, Arcane]                # SKY-###, PR #NNN, ADR NNNN, hosts — anything to cross-link
thread_status: none     # none | open | resolved | unknown; digest shows only explicit open
# resolves: [<episode-basename>, …]   # optional: close earlier episodes' open threads (append-only-safe)
---

# 2026-09-15 · session · SKY-025 P11 activation ordering review fix

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (journal/README.md). Distillation happens at READ time, never here. -->

## What happened
Resumed the original P11 implementation session after the external review found that
`deploy_service()` called Arcane source sync before replacing `.env`. Arcane's manual and scheduled
sync paths both redeploy an already-running project after changed source is promoted, so the live
`librespeed` proof did not cover a source revision that required changed environment data.

The first repair draft changed `autoSync` to false inside the post-merge deploy command. Independent
verification rejected it because Arcane unregisters future scheduler fires but cannot cancel a sync
already admitted past the auto-sync check; the sync status API exposes only the last completed result,
not the in-flight lease. The final repair instead requires the existing unique sync to already have
`autoSync=false` and fails before any remote write otherwise. Legacy records must be disabled and
drained while old source and old environment still agree, before the coupled revision is exposed.

No production write, credential change, root grant, or T3 action ran in this fix session. All Arcane
activation exercises were disposable.

## Actions & outcomes
- Reordered packaged deployment → selected environment is atomically installed before branch
  repoint or manual source sync; normal deployment then always requests an explicit bounded redeploy.
- Changed `--no-deploy` → it prepares environment only and never repoints, syncs, redeploys, or
  claims source/runtime verification.
- Removed initial-sync creation → a missing sync/project fails closed because Arcane creation
  performs an immediate source sync that this command cannot sequence ahead of environment materialization.
- Ran disposable OLD source + OLD env to NEW source + NEW env cases → NEW source was observed only
  with NEW env at Arcane's implicit activation and the explicit redeploy; enabled auto-sync refused
  before writes; failed and ambiguous sync outcomes retained truthful completed steps and recovery.
- Re-ran affected verification and retained controls → exact revision, atomic `0600` env and
  redaction, timeout/process tree, runtime health, gate, cloudflared, rollback, forwarders, package
  closure, Ruff, strict mypy, Python compilation, shell syntax, offline Nix build, secret scan, hard
  invariants, and diff checks passed under the embargo.

## Graveyard — tried & abandoned
Negative results are memory too. Anything attempted that did NOT work — and *why* — so a future
cold agent doesn't re-walk the dead end. Leave a single "— nothing abandoned —" line only if the
episode genuinely tried no path it dropped.

- Disable auto-sync inside the post-merge deploy invocation → abandoned because it cannot cancel
  a scheduler run already admitted against the newly exposed branch.
- Infer Arcane redeploy from a changed commit → abandoned because an environment-only change may
  be filtered from Arcane's source-content comparison; the package always explicitly redeploys.

## Follow-ups / open threads
- PR #259 remains open for a fresh external review. Do not reuse the earlier FIX review as acceptance.
- Legacy `autoSync=true` records still need the documented one-time T2 pre-merge migration and drain.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
