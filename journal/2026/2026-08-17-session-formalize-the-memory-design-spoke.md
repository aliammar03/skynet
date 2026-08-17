---
date: 2026-08-17
kind: session
title: formalize the memory design spoke
tier_touched: [T1]
grants: []
refs: [SKY-006, docs/design/memory.md, "docs/memory-spoke"]
---

# 2026-08-17 · session · formalize the memory design spoke

## What happened
After shipping SKY-006 P1 (journal) + P2 (agent digest), Ali asked to explain how the memory
system works, then judged it "important enough to warrant a spoke." Elevated the memory
architecture from scattered mentions into a first-class constitution spoke.

- Wrote `docs/design/memory.md`: the four memory kinds (working/semantic/procedural/episodic) +
  where Skynet keeps each, the episodic gap, the journal (raw/append-only/graveyard), the
  write-raw/read-summarize rule, ADRs as decision memory, retrieval (06 digest live + P3 semantic
  index horizon), the three memory invariants, the feed/read loop, and the repo-memory vs
  engine-private-memory boundary.
- Registered it in the constitution: §7 spokes table row + a §6 growth-direction bullet.
- Enforced one-authoritative-home: moved the episodic-memory depth OUT of
  `docs/design/observability.md` (which now keeps only the *rendering* concern + a pointer) and
  INTO the new spoke. Repointed `journal/README.md`'s governance line at memory.md (architecture)
  while it stays the home for the record *format*. Added memory.md to the SKY-006 `related:` list.

## Actions & outcomes
- `bin/new journal session …` → this entry (dogfooding again).
- Split of concerns: architecture → memory.md; record format → journal/README.md; rendering →
  observability.md. Each rule now has exactly one home with pointers from the others.

## Graveyard — tried & abandoned
- **Leaving the memory design as a section inside observability.md** — abandoned. Memory outgrew a
  subsection and was competing with observability's actual concern (inventory→docs rendering).
  Splitting it into its own spoke is exactly the hub-shrinks/spoke-carries-depth pattern the
  conventions prescribe.

## Follow-ups / open threads
- P3 (semantic index) is the only SKY-006 phase left, still parked behind the "overkill line".
- If a future engine keeps its own private memory, keep the repo/engine boundary (spoke's last
  section) crisp so the in-repo layer stays the authoritative, portable one.
