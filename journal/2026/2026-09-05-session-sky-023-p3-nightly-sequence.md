---
date: 2026-09-05
time: 20:42:07
kind: session
title: SKY-023 P3 nightly sequence consolidation
tier_touched: [T1]
grants: []
refs: [SKY-023]
thread_status: none
---

# 2026-09-05 · session · SKY-023 P3 nightly sequence consolidation

## What happened

Continued Phase 3 after PR #193 merged. This was T1 repository work only: no live nightly pass,
collector, credential read, infrastructure write, root grant, or production PR was run.

Made the deterministic maintenance sequence the sole owner of branch preparation, collection,
envsync, factual rendering, raw journal evidence, final digest/context-map renders, commit, PR
creation, and the existing merge gate. `bin/ops nightly` now prepares first, offers primary then
fallback engines only an optional narrative/grant-audit stage, and finalizes the already-prepared
branch whether those engines succeed or fail. The fallback can no longer reset the branch or repeat
completed deterministic mutation steps.

Extracted collection into a T1-only aggregate with no rendering. The finalizer writes the journal
before rendering the digest and context map, so both include the current run. Mocked regression
tests cover exact-once ordering, a collector failure carried to the journal while later steps run,
the journal-before-digest relation, finalizer-owned PR/gate work, and script-mode `bin/ops` routing.

## Actions & outcomes

- Updated the nightly runbook, observability spoke, timer example, and merge-gate ADR → current
  operational instructions name one deterministic sequence with an optional agent stage.
- Ran syntax checks, the new nightly-sequence tests, merge-gate tests, and the complete shell test
  suite → all passed.

## Graveyard — tried & abandoned

- Separate agent and deterministic nightly workflows → removed because their duplicate collection,
  rendering, and PR ownership allowed stale ordering and unsafe fallback resets.

## Follow-ups / open threads

- Continue SKY-023 Phase 3 with the Obsidian artifact cleanup and substantive runbook/policy corpus
  reduction. The Phase exit targets remain open.
