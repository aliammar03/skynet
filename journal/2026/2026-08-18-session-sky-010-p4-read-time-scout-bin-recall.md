---
date: 2026-08-18
kind: session
title: SKY-010 P4 — read-time scout (bin/recall)
tier_touched: [T1]
grants: []
refs: [SKY-010, SKY-006, ADR-0002, "PR #52", "PR #53", "PR #54"]
---

# 2026-08-18 · session · SKY-010 P4 — read-time scout (bin/recall)

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (SKY-006 / journal/README.md). Distillation happens at READ time, never here. -->

## What happened
Ran SKY-010 Phase 4 — the last phase. Built `bin/recall`, the vendor-neutral read-time scout, and
documented the scout pattern in `docs/design/memory.md`. This closes SKY-010 (P1 audit+doctrine, P2
budget frontmatter, P3 context map, P4 scout).

`bin/recall <topic>` is T1/read-only: OR-joins its args into one case-insensitive regex, `grep -rilIE`
over `journal docs runbooks planning AGENTS.md README.md` (excludes `docs/generated` — derivative —
and `.git`), then per matching file prints hit-count · ~tokens (reads P2 `tokens:` frontmatter, else
bytes/4) · `summary:` (else `title:`, else first heading) · the first matching line trimmed to 96
chars. Ranked hits-desc then tokens-asc, capped at 20. Footer restates the ADR-0002 guardrail: never
persist the scout's summary.

**Demonstration — a real "what did we try with X?"** Asked the scout whether the local semantic
index was already decided, so I wouldn't relitigate it:

```
$ bin/recall "semantic index" "sqlite-vec"
recall "semantic index|sqlite-vec" — 11 file(s) mention it (ranked; ...):
   4 hit · ~2697 tok · planning/scratchpad/research/2026-08-17-reactive-memory.md
   3 hit · ~1798 tok · planning/projects/SKY-006-agent-episodic-memory-journal-retrieval.md
   3 hit · ~3829 tok · planning/projects/SKY-010-default-lean-context-load-on-demand.md
   1 hit · ~ 879 tok · docs/decisions/0002-append-only-episodic-journal.md
   ...
```

Opened the top three + ADR 0002 (≈9K tok, in a throwaway pass — not the main window). **Conclusion
distilled and NOT persisted:** the `sqlite-vec` semantic index is SKY-006 P3, deliberately parked
behind the research "overkill line" (don't add a vector DB until markdown+grep visibly strain for a
single operator); every layer over the journal stays a cache, never truth (ADR 0002). So: leave it
parked; SKY-010's map+recall may push the overkill line out far enough it's never needed. That
answer cost one query and left nothing behind — the point of the scout.

## Actions & outcomes
- wrote `bin/recall` (+`chmod +x`) → ran clean on "semantic index", "context rot|default-lean", and a
  no-match term (all three paths OK; ranking + cost + snippet render as intended).
- extended `docs/design/memory.md` working-memory section: the read-time-scout bullet is now live
  (concrete `bin/recall` usage) instead of a "(P4)" forward-reference; guardrail kept verbatim.
- this journal entry seeded via `bin/new journal session` per SKY-006.

## Graveyard — tried & abandoned
- **Listing every journal episode as its own row in the context map (P3 idea)** → abandoned: it would
  grow unbounded and re-duplicate the digest. The journal is retrieved by *topic* (this scout), so the
  map points at `bin/recall` instead of enumerating episodes.
- **Having `bin/recall` search `docs/generated/`** → dropped: those are derivative caches; matching
  them just echoes the authored sources. Excluded via `--exclude-dir=generated`.

## Follow-ups / open threads
- SKY-010 is done (4/4). A Claude subagent scout should call `bin/recall` internally, then read only
  the top hits — same capability, engine-specific wrapper.
- Sibling idea still unclaimed: promoting deterministic runbooks to executable capabilities (its own
  SKY-###) — would cut procedural read cost the way this cut retrieval cost.
- Once a lint/pre-commit gate runs `budget-frontmatter.sh --check`, editing a doc without refreshing
  `tokens:` fails CI (bit me on `nightly.md` in P3) — wire the refresh into the gate or a pre-commit.
