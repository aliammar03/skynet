---
date: __DATE__
time: __TIME__            # local HH:MM:SS; orders same-day episodes in the digest
kind: __KIND__          # session | incident | decision
title: __TITLE__
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: []                # SKY-###, PR #NNN, ADR NNNN, hosts — anything to cross-link
thread_status: none     # none | open | resolved | unknown; digest shows only explicit open
---

# __DATE__ · __KIND__ · __TITLE__

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (SKY-006 / journal/README.md). Distillation happens at READ time, never here. -->

## What happened
Intent, then the trajectory: what ran, on which hosts, what changed, what broke. Keep it raw
and specific — commands, VMIDs, error text, timestamps. A cold agent should be able to replay
your reasoning from this alone.

## Actions & outcomes
- <action> → <result>

## Graveyard — tried & abandoned
Negative results are memory too. Anything attempted that did NOT work — and *why* — so a future
cold agent doesn't re-walk the dead end. Leave a single "— nothing abandoned —" line only if the
episode genuinely tried no path it dropped.

- <approach> → abandoned because <reason>

## Follow-ups / open threads
- <thing left undone, or a question raised>

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
