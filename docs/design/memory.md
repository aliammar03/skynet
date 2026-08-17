# Spoke · Agent memory

> How a stateless agent remembers: the four kinds of memory, where Skynet keeps each, and the
> episodic layer (journal → digest) that SKY-006 added. Governed by
> [`../system-design.md`](../system-design.md); the record *format* lives in
> [`../../journal/README.md`](../../journal/README.md), the design lives here. Sourced from
> [SKY-006](../../planning/projects/SKY-006-agent-episodic-memory-journal-retrieval.md).

Skynet is **stateless by design** — every session is a fresh mind that rebuilds the world from git
(§2 of the constitution). That turns memory from a nicety into *infrastructure*: if the agent can't
reconstruct what it needs from the repo, it can't operate. This spoke is the map of what the agent
remembers and how.

## The four kinds of memory

The 2025–26 consensus splits agent memory four ways. Skynet was strong in three and blind in one:

| Kind | Holds | Where it lives | State |
|---|---|---|---|
| **Working** | the current task | the context window | fine — but scarce; retrieve *sparingly* |
| **Semantic** | facts / current state | `docs/`, `inventory/`, `docs/generated/` | strong |
| **Procedural** | how to do things | `runbooks/`, `scripts/`, `bin/` | strong |
| **Episodic** | *what actually happened* | `journal/` + the digest (this spoke) | **added by SKY-006** |

The context window is the real bottleneck — everything competes for it — which is *why* retrieval
matters: pull the few relevant episodes, not the whole history.

## The gap was episodic

A cold agent could describe the lab perfectly but couldn't answer *how did we get here, what was
tried, what failed*. Git history technically holds every event, but it isn't **shaped for recall** —
no agent `git log`s six months to reconstruct a decision. The problem was never storage; it was
**retrieval**, and before retrieval, **not losing episodes** in the first place. SKY-006 fixed the
shape, in three parts.

## 1. The episodic store — the journal

[`journal/`](../../journal/README.md) is an **append-only** log of dated episodes —
`journal/<YYYY>/<YYYY-MM-DD>-<kind>-<slug>.md`, kind ∈ `session` / `incident` / `decision`. Each
entry carries a **Graveyard** of tried-and-abandoned approaches, because negative results are the
memory that stops a future agent re-walking a dead end. The record anatomy is specified once in
[`journal/README.md`](../../journal/README.md); `bin/new journal` stamps a conforming skeleton.

The load-bearing design rule:

> **Write raw episodes; summarize at *read* time — never at write time.**

Summarizing as you write "collapses distinct episodes into semantic generalizations, destroying the
episodic signal before it can be used." So entries stay concrete (commands, VMIDs, errors, what
broke); distillation waits until something is actually retrieved. This is recorded as a decision in
[ADR 0002](../decisions/0002-append-only-episodic-journal.md).

## 2. Decision memory — ADRs

[`docs/decisions/`](../decisions/) holds one record per non-trivial choice, **amended in place,
never superseded** (see [conventions/docs](../conventions/docs.md)), so the agent never relitigates
a settled question. ADRs are the durable, curated counterpart to the journal's raw stream: the
journal holds the messy *how we got there*, the ADR holds the settled *what's true now*.

## 3. Retrieval — read-time, a cache never a truth

Two layers read *over* the raw store. Both are **regenerable from git**, so statelessness holds —
delete them and rebuild, nothing is lost.

- **The agent cold-boot digest** (SKY-006 P2, **live**) — `scripts/render-digest.sh` generates the
  standalone machine page [`../generated/06-agent-digest.md`](../generated/06-agent-digest.md):
  *recent decisions* (ADRs), *open threads* (open `SKY-###` directives + the journal's own
  follow-up bullets), *recent episodes*. It **points, never re-summarizes** (honoring the write-raw
  rule), runs on both nightly paths (fresh even LLM-free), and is content-stable (diffs only on real
  change). This is the agent's **cold-boot front door** — `AGENTS.md` sends a fresh session here
  first. Its human counterpart, [`05-state-of-the-lab.md`](../generated/05-state-of-the-lab.md),
  is a prose narrative kept deliberately separate (and surfaced in the top-level `README`).
- **A git-rebuildable semantic index** (SKY-006 P3, **horizon**) — a local `sqlite-vec`-class
  embedding index over repo + journal for retrieval-*by-similarity*. Deferred on purpose: the
  research "overkill line" says don't add a vector DB until markdown + `grep` visibly fail for a
  single operator. When the journal grows past what grep surfaces, that's the signal to build it —
  and it stays a **cache, rebuilt from git**, never a source of truth.

## The memory invariants

Three rules keep the system honest; they don't get an "unless":

1. **Raw at write, summarized at read.** Never pre-digest an episode.
2. **The journal is append-only.** An episode is never rewritten; a correction is a *new* entry
   referencing the old one — the way git never edits a past commit. (This is why `journal/` is
   authored/appended, **not** a generated dir — the "never hand-edit generated dirs" rule doesn't
   apply to it.)
3. **Retrieval is a cache, never a source of truth.** Every derived layer (digest, future index)
   rebuilds from the raw journal + git. This is what lets the agent stay stateless.

## The loop — how memory is fed and read

```
                   WRITE (raw, append-only)              READ (summarize on demand)
 nightly run ─┐
 incident   ──┼──►  journal/<date>-<kind>.md ──┐
 decision   ─┘         (+ ADRs, roadmap)       ├─►  render-digest.sh ─►  06-agent-digest.md
                                               │                              │
                                               └──────────────────────────────┴─► cold agent
                                                                                   reads first
```

- **Fed** automatically by the nightly on **both** engine paths — the LLM writes a rich raw entry,
  the deterministic fallback writes a factual one from the diff. Either way an episode lands.
  (Runbook: [`../../runbooks/nightly.md`](../../runbooks/nightly.md).)
- **Read** on cold boot via the digest, or directly with `grep -ri "<topic>" journal/`.

## Boundary — the repo's memory vs. an engine's own

Everything here is the **repo's** memory: in git, agent-agnostic, part of the contract, used by any
engine that operates Skynet. It is distinct from whatever *private* cross-session memory a specific
engine keeps outside the repo (e.g. a Claude Code session's own `MEMORY.md` scratchpad). The two may
mirror each other, but only the in-repo layer is authoritative and portable across engines.
