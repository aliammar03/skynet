---
date: 2026-09-15
time: 09:40:48            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: SKY-025 P11 source-sync retry review fix
tier_touched: []        # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-025, PR #259, Arcane]                # SKY-###, PR #NNN, ADR NNNN, hosts — anything to cross-link
thread_status: none     # none | open | resolved | unknown; digest shows only explicit open
# resolves: [<episode-basename>, …]   # optional: close earlier episodes' open threads (append-only-safe)
---

# 2026-09-15 · session · SKY-025 P11 source-sync retry review fix

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (journal/README.md). Distillation happens at READ time, never here. -->

## What happened
Resumed P11 PR #259 after independent review found that `_pull()` could issue another manual Git Sync
POST following an ambiguous request or a completion poll that never reached terminal state. The prior
repair had already recorded that Arcane exposes the last completed sync fields but no operation
identity or in-flight lease, so an unchanged reread could not prove whether the POST was admitted or
still running.

The final state machine captures the completion marker before a normally returned POST. An ambiguous
request/response performs no retry and returns unresolved inspect-before-retry evidence. A normal
response whose completion remains non-terminal through the bound also stops after one POST. Only a
changed, nonempty `lastSyncAt` paired with terminal `failed`/`error` permits another bounded attempt.
The recovery finalizer now checks `source-synced` before `environment-replaced`.

No production I/O, credential change, root grant, T2 write, T3 action, merge, or acceptance review ran.

## Actions & outcomes
- Ambiguous admitted source-sync reproduction → exactly one POST, prior completed observation was
  not mistaken for completion, and the outcome required inspection before retry.
- Non-terminal completion reproduction → exactly one POST through the deadline and unresolved
  recovery; no overlapping activation was requested.
- Terminal failure reproductions → retry occurred only with a changed, nonempty completion marker;
  an empty marker did not authorize retry.
- Post-success project-ID mismatch → `source-synced` remained in completed steps and recovery stated
  that source activation occurred.
- Retained P11 and manual controls → sequencing/no-deploy/auto-sync refusal and the affected exact-
  revision, environment, timeout, runtime, gate, cloudflared, rollback, forwarder, package, lint,
  compile, shell, secret, invariant, and diff checks passed under the embargo.

## Graveyard — tried & abandoned
Negative results are memory too. Anything attempted that did NOT work — and *why* — so a future
cold agent doesn't re-walk the dead end. Leave a single "— nothing abandoned —" line only if the
episode genuinely tried no path it dropped.

- Treat an unchanged last-success commit as reconciliation of an ambiguous POST → abandoned because
  it may be the previous completed operation while the new activation remains admitted or in flight.
- Retry after a non-terminal deadline → abandoned because absence of a terminal observation is not
  evidence that the activation was rejected or finished.

## Follow-ups / open threads
- PR #259 remains open for a fresh independent review. The implementation session did not self-accept.
- Arcane still exposes no in-flight sync identity; indeterminate activation requires operator
  inspection rather than automated retry.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
