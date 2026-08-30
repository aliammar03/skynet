---
date: 2026-08-30
kind: decision          # session | incident | decision
title: CT 240 PBS topology: network-node instance was a remnant, now gone
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [PR #122, PR #125] # the nightlies that kept flagging this
---

# 2026-08-30 · decision · CT 240 PBS topology: network-node instance was a remnant, now gone

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (SKY-006 / journal/README.md). Distillation happens at READ time, never here. -->

## What happened
Several 2026-08-30 nightly passes flagged a CT 240 anomaly: the **network-node** Proxmox host
had a CT 240 (PBS) that disappeared from inventory while the **core-node** CT 240 (PBS) came back
running — the nightly narrative repeatedly asked whether this was a deliberate migration/
consolidation. Ali confirmed: the network-node CT 240 was an **old remnant** and is now **gone**.
There is no missing/failed instance to chase — core-node CT 240 is the intended PBS. Not a
consolidation, not a migration: just a leftover that got cleaned up.

## Actions & outcomes
- Ali clarified network-node CT 240 = old remnant, all gone → the recurring nightly "CT 240
  topology" open-thread is RESOLVED. No action needed on either node.

## Graveyard — tried & abandoned
— nothing abandoned (a clarification, not an investigation) —

## Follow-ups / open threads
- None from this thread. (Backup *freshness* — verifying recent PBS snapshots + the L5 gdrive
  mirror via the credentialed procedure — remains its own separate open item, unrelated to this.)

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
