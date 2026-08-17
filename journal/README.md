# journal — Skynet's episodic memory

> The append-only log of **what happened**: session runs, incidents, and decisions, as raw dated
> episodes. This is the memory git history only *implies*. The memory *architecture* is designed in
> the [`../docs/design/memory.md`](../docs/design/memory.md) spoke; the record *format* is doctrine
> and this README is its one authoritative home. Born of
> [SKY-006](../planning/projects/SKY-006-agent-episodic-memory-journal-retrieval.md).

Skynet is stateless by design — every session is a fresh mind that rebuilds the world from git.
That makes memory *infrastructure*. The lab already has strong **semantic** memory (docs, MEMORY.md,
inventory) and **procedural** memory (runbooks, scripts). The weak spot is **episodic**: *how did
the lab get here, what was tried, what failed.* Git technically holds it, but it isn't shaped for
recall. The journal is that shape.

## The one rule that matters

**Write RAW episodes; summarize at *read* time, never at write time.** An agent that summarizes as
it writes "collapses distinct episodes into semantic generalizations, destroying the episodic signal
before it can be used." So every entry is concrete and specific — commands, VMIDs, error text,
what broke — and distillation happens later, when something is actually retrieved. Do not pre-digest.

## Record kinds

| Kind | Written when | Written by |
|---|---|---|
| **session** | a run happened — nightly, a directive phase, an ad-hoc job | the nightly; the agent at a phase close-out |
| **incident** | something broke or was diagnosed | SKY-005 diagnoses; the agent when it firefights |
| **decision** | a non-trivial choice was made | the agent — **paired with an ADR** in [`../docs/decisions/`](../docs/decisions/); the journal holds the messy *how we got there*, the ADR holds the settled *what's true now* |

## Anatomy

- **Filename:** `journal/<YYYY>/<YYYY-MM-DD>-<kind>-<slug>.md` — dated, so the directory
  self-indexes chronologically; multiple episodes may share a date.
- **Frontmatter:** `date`, `kind`, `title`, `tier_touched`, `grants` (root grants actually used —
  host + KeyID), `refs` (SKY-###, PR, ADR, hosts). See [`../templates/journal.md`](../templates/journal.md).
- **Body:** `## What happened` (raw), `## Actions & outcomes`, `## Graveyard — tried & abandoned`,
  `## Follow-ups / open threads`.
- **The Graveyard is load-bearing.** Negative results are memory: the approaches that *failed* are
  exactly what a cold agent needs so it doesn't re-walk the dead end. Never drop them to "keep it clean."

## Two invariants

- **Append-only.** An episode, once written, is not rewritten — a correction is a *new* entry that
  references the old one, the way git never edits a past commit. The git log is the audit trail;
  the journal is the narrative one. (This is why `journal/` is **not** a generated dir — it is
  authored/appended, never re-rendered, so the "never hand-edit generated dirs" rule does not apply.)
- **Retrieval is a cache, never a source of truth.** Everything the journal enables downstream — the
  rolling digest (SKY-006 P2) and a git-rebuildable semantic index (P3) — is regenerable from these
  files. Delete the digest or the index and rebuild; nothing is lost. The raw entries are the truth.

## Writing one

Stamp a doctrine-conforming skeleton, then fill the `TODO`s:

```
bin/new journal session  "nightly 2026-08-17"
bin/new journal incident "ct-240 restic backup failing"
bin/new journal decision "adopt an append-only episodic journal"
```

It writes `journal/<YYYY>/<YYYY-MM-DD>-<kind>-<slug>.md` from [`../templates/journal.md`](../templates/journal.md).

## Reading (today)

Grep + read the dated files; the nightly's rolling digest (P2) will become the cold-boot front door,
and a local semantic index (P3) adds retrieval-by-similarity once markdown + grep visibly strain.
Until then: `grep -ri "<topic>" journal/` and read the episodes it surfaces.
