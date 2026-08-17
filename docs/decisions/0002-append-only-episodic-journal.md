# ADR 0002 — Append-only episodic journal

- **Status:** accepted
- **Date:** 2026-08-17

## Context

Skynet is stateless by design: every session is a fresh mind that rebuilds the world from git. That
makes memory *infrastructure*, not a nicety. Scored honestly, three of the four memory kinds are
already strong — **semantic** (design docs, `MEMORY.md`, `inventory/`, `docs/generated/`),
**procedural** (`runbooks/`, `scripts/`, `bin/`), and **working** (the context window). The weak
one is **episodic**: *how did the lab get here, what was tried, what failed.* Git history technically
holds every event, but it is not shaped for recall — a cold agent will not `git log` six months to
reconstruct a decision or rediscover a dead end. The problem was never storage; it is **retrieval**,
and before retrieval, **not losing episodes in the first place**.

The known failure mode (research: `planning/scratchpad/research/2026-08-17-reactive-memory.md`) is
summarizing at write time, which "collapses distinct episodes into semantic generalizations,
destroying the episodic signal before it can be used." A record that pre-digests is a record that
has already thrown away what episodic memory is for.

## Decision

Adopt an **append-only episodic journal** at [`journal/`](../../journal/README.md): raw, dated
**session / incident / decision** episodes at `journal/<YYYY>/<YYYY-MM-DD>-<kind>-<slug>.md`, each
including a **Graveyard** of tried-and-abandoned approaches (negative results are memory too).

Two rules are load-bearing:

1. **Write raw; summarize only at read time.** Entries record concrete facts — commands, VMIDs,
   error text, what broke. Distillation happens when something is retrieved, never as it is written.
2. **Append-only.** An episode is never rewritten; a correction is a new entry that references the
   old one, the way git never edits a past commit. `journal/` is therefore authored/appended, not
   generated — the "never hand-edit generated dirs" rule does not apply to it.

The nightly feeds the journal (a raw session entry per run, on both the agent and deterministic
paths); SKY-005 diagnoses will feed incidents. Retrieval layers built on top — the rolling digest
(SKY-006 P2) and a local git-rebuildable semantic index (P3) — are **caches, never sources of
truth**: regenerable from the raw entries, so statelessness holds.

Explicit non-goal: any external or hosted memory service. It would add a second source of truth and
break the "rebuild from git" invariant.

## Consequences

- A cold agent can reconstruct *how the lab got here* and, crucially, what was already tried and
  abandoned — without re-walking dead ends. Episodic memory stops being the weak spot.
- Every run now writes one more file; the journal grows monotonically. Accepted: dated files
  self-index, and the P2 digest / P3 index exist precisely to keep growth navigable.
- The raw-write discipline is a *manual* rule until the parked convention lint gate can assert it;
  it holds by review and by the `journal/README.md` + template embedding it.
- Statelessness is preserved: delete any downstream digest or index and rebuild from `journal/` +
  git. The raw entries are the only truth this system adds.

<!-- ADRs are amended IN PLACE, never superseded (docs/conventions/docs.md). When this decision
     changes — a correction or a full reversal — edit THIS file to state what's true now and add a
     dated line under a `## History` section; the git log holds the prior wording. -->
