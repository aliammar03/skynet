---
date: 2026-08-17
kind: session
title: SKY-006 P1 — stand up the journal
tier_touched: [T1]
grants: []
refs: [SKY-006, ADR 0002, "phase/sky-006-p1-journal", journal/README.md]
---

# 2026-08-17 · session · SKY-006 P1 — stand up the journal

## What happened
Executed SKY-006 Phase 1 (the directive was in `planning/ideas/`, not `projects/` — the execute
prompt's path was aspirational; promoted it to `projects/` as part of close-out). Goal: close the
lab's episodic-memory gap by standing up `journal/` and wiring the nightly to feed it.

Read the shape of the world first: `runbooks/nightly.md`, `bin/ops` (agent prompt + engine
fallback), `scripts/nightly.sh` (deterministic path), the conventions hub + `docs/conventions/`
spokes, `bin/new` / `bin/plan` scaffolders, and the research brief
`planning/scratchpad/research/2026-08-17-reactive-memory.md` (which supplied the one non-negotiable
rule: write raw, summarize at read time).

Built, all additive:
- `journal/README.md` — the format convention's one authoritative home (kinds, Graveyard, the two
  invariants: append-only + retrieval-is-a-cache).
- `templates/journal.md` + `bin/new journal <kind> <title>` (stamps `journal/<YYYY>/<date>-<kind>-<slug>.md`).
- Nightly wiring: `scripts/nightly.sh` now writes a raw session entry from the diff stat (no LLM);
  `bin/ops` agent prompt + `runbooks/nightly.md` step 6 tell the agent path to append one too.
- Doctrine pointers: `docs/conventions/docs.md` (journal subsection + hub row), `layout.md` (map +
  scaffold rows), `docs/design/observability.md` (episodic-memory section), one `AGENTS.md §4` bullet.
- ADR 0002 (decision memory, dogfooded via `bin/new adr`).
- This entry — dogfooding `bin/new journal`.

## Actions & outcomes
- `bin/new adr "Append-only episodic journal"` → `docs/decisions/0002-…md` (numbering worked).
- `bin/new journal session "SKY-006 P1 stand up the journal"` → this file (kind-guard + date-dir worked).
- Both scaffolders stamped clean skeletons on first try.

## Graveyard — tried & abandoned
- **One rolling append-only log file (`journal/<year>.md`) instead of one file per episode** —
  abandoned. A single growing file makes per-episode frontmatter/refs awkward and turns every
  nightly into a merge-prone edit of one hot file. One file per episode keeps entries immutable and
  the directory self-indexing by date; it's also what the P3 semantic index will want to chunk on.
- **Making the deterministic nightly write a *narrative* entry** — abandoned. The deterministic path
  has no LLM by definition, and narrative would be summarization-at-write-time — exactly the
  anti-pattern ADR 0002 forbids. It writes only the raw diff stat; the agent path adds prose.
- **A new convention *spoke* (`docs/conventions/journal.md`)** — abandoned in favor of
  `journal/README.md` as the authoritative home, matching how `runbooks/README.md` and
  `planning/README.md` already act as hubs for their dirs (docs.md's own hub table). Avoided a
  near-empty spoke duplicating the README.

## Follow-ups / open threads
- Phase 2: fold a rolling cold-boot digest ("state + recent decisions + open threads") into
  `docs/generated/05-state-of-the-lab.md` so a fresh session orients from one page.
- Phase 3: git-rebuildable local semantic index (sqlite-vec class) — deferred until markdown+grep
  visibly strains (research brief's "overkill line").
- SKY-005 isn't built yet, so "incident" entries have no automated writer today — the nightly
  (session) is the only live feeder until then. The convention is ready for SKY-005 to adopt.
- The raw-write rule is `[manual]` until the parked convention lint gate can assert it.
