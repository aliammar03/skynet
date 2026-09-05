---
date: 2026-09-06
time: 00:53:48            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: SKY-023 Phase 5 temporal-hygiene close-out
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-023]         # SKY-###, PR #NNN, ADR NNNN, hosts — anything to cross-link
thread_status: none     # none | open | resolved | unknown; digest shows only explicit open
---

# 2026-09-06 · session · SKY-023 Phase 5 temporal-hygiene close-out

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (SKY-006 / journal/README.md). Distillation happens at READ time, never here. -->

## What happened
Resumed SKY-023 on `main` with a clean worktree and read the cold-boot digest, context map,
planning contract, directive, construction/delegation guidance, documentation convention, and the
previous Phase 3/4 close-out. This was T1 repository work only: no infrastructure command,
credential access, T2 write, or root grant ran.

Created branch `docs/sky-023-p5-temporal-hygiene`, then wrote the required temporary crud matrix at
`/tmp/sky-023-p5-crud-matrix.QFY7rP.md`. The matrix classified provenance in the operations contract,
conventions, architecture/design docs, backup/DR guidance, runbooks, and service READMEs. It recorded
that OPNsense's unavailable write actuator, the unpooled-Unraid boundary, the secret hierarchy, and
the verified/unverified recovery distinction remained current facts; their directive IDs, dates, and
origin stories did not.

Removed numeric directive references from the scoped current-authority prose. Rewrote the OPNsense
status as a current capability absence, the alternate VMID form as a supported format, and the
per-CT identity design as a current constraint. Removed completed migration narration from the nightly
and service-deployment paths, including the ordinary legacy-cutover section. Simplified cloudflared
credential recovery and Arcane bootstrap notes to current operating instructions. Replaced dated
backup and DR proof anecdotes with current recovery confidence: targeted archive recovery is verified;
full core-loss recovery remains unverified.

## Actions & outcomes
- Ran `bash .githooks/pre-commit` → all invariant, entity, digest, rollback, provisioning,
  collection, construction, agent, hygiene, nightly, and documentation-drift checks passed.
- Ran `git diff --check` → no whitespace errors.
- Ran the Phase 5 scoped numeric-directive and archaeology-pattern search → no directive provenance
  remained; the only `used` result was the ordinary `caddy fmt --overwrite` instruction.
- Ran `bin/new journal session 'SKY-023 Phase 5 temporal-hygiene close-out'` → created this raw
  close-out entry.

## Graveyard — tried & abandoned
Negative results are memory too. Anything attempted that did NOT work — and *why* — so a future
cold agent doesn't re-walk the dead end. Leave a single "— nothing abandoned —" line only if the
episode genuinely tried no path it dropped.

- Broad deletion of recovery facts → abandoned because verification status remains load-bearing for
  restore and DR decisions; the prose now states current verified/unverified status without its event
  history.
- Keeping `envsync.sh` in the nightly or deployment runbook as a compatibility explanation →
  abandoned because it made a finished migration appear to be routine operation; its actual callers
  and recovery role are deferred to Phase 7's behavior audit.

## Follow-ups / open threads
- Continue SKY-023 at Phase 6; read [[SKY-023-progress]], verify reality, and execute only that phase.
- Phase 6 owns the code/config comment sweep. Phase 7 must adjudicate `scripts/envsync.sh` and other
  retained compatibility helpers before any deletion.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
