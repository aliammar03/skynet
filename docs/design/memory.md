---
summary: "How a stateless agent remembers: the four memory kinds, the episodic journal→digest, and the default-lean working-memory discipline."
tokens: 2884
---

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

Two disciplines keep that infrastructure honest, and they are **peers**. One guards the **write**
path — *don't lose what happened* (the episodic layer SKY-006 added: write raw, append-only). The
other guards the **read** path — *don't drown the mind that reads* (the default-lean working-memory
discipline SKY-010 added: load the smallest high-signal set, pull the rest just-in-time). This spoke
was authored episodic-first; the working-memory section below makes the second discipline
first-class beside it.

## The four kinds of memory

The 2025–26 consensus splits agent memory four ways. Skynet was strong in three and blind in one:

| Kind | Holds | Where it lives | State |
|---|---|---|---|
| **Working** | the current task | the context window | scarce — the one kind you *can't* grow by writing to git; governed by the default-lean discipline below |
| **Semantic** | facts / current state | `docs/`, `inventory/`, `docs/generated/` | strong |
| **Procedural** | how to do things | `runbooks/`, `scripts/`, `bin/` | strong |
| **Episodic** | *what actually happened* | `journal/` + the digest (this spoke) | **added by SKY-006** |

The context window is the real bottleneck — everything competes for it — which is *why* retrieval
matters: pull the few relevant episodes, not the whole history.

## Working memory — the default-lean discipline  `[manual]`

Working memory is the context window, and it is the memory that discipline has to *protect* rather
than fill: the other three kinds grow safely by writing more to git, but every token that enters the
window competes with every other for a finite attention budget. So the governing rule runs the
opposite direction from "store more."

> **Default-lean.** Nothing enters context until a task actually needs it. The always-loaded baseline
> is audited down to the smallest high-signal set — the safety-and-execution contract, nothing more —
> and everything else is reachable *only* on demand, behind a **trigger + a reliable retrieval path**.

This is not only economy. The context-rot research (SKY-010's motivation) is blunt: irrelevant tokens
**actively degrade accuracy** — every one draws down the attention budget and buries the
decision-critical evidence, and all 18 top models tested got *worse* as input grew. **Unnecessary
context is a correctness bug, not just a cost.** That is why "retrieve *sparingly*" is an invariant,
not a nicety, and why moving something off the baseline is safe *only once it has a retrieval path* —
a block with no way back is not lean, it's lost.

**The audited baseline.** What auto-loads today, and where each block belongs (SKY-010 P1). The
classification is stable; the live token weights come from the budget script + context map (P2–P3),
never hand-maintained here — they drift.

| Auto-loads by default | Kind | Verdict |
|---|---|---|
| `CLAUDE.md` → imports `AGENTS.md` | the engine-neutral contract | **always** |
| `AGENTS.md` §0–3, §6, §7 — identity, trust tiers, execution policy, auto-approve state, Judgement Day invariants, when-in-doubt | contract | **always** — the minimal safety+execution spine |
| `AGENTS.md` §4 deploy-loop *mechanism detail* (Arcane specifics, env layering, `project.env`) | reference | **movable** → [gitops-loop](gitops-loop.md) + [conventions](../conventions.md); keep a one-line pointer |
| `AGENTS.md` §5 planning *lifecycle detail* (stages, `bin/plan`, phase sizing) | reference | **movable** → [`planning/README.md`](../../planning/README.md); keep a one-line pointer |
| `06-agent-digest.md` — the mandated cold-boot read | generated orientation | **always** on cold boot; already lean & regenerable |

*Movable* means marked now, **relocated only in SKY-010 P3** — once the context map gives the block a
trigger + a way back. Mark first, move later, so nothing goes dark. The Judgement Day invariants stay
always-loaded, always: lean ≠ unsafe.

**The mechanism is progressive disclosure**, and it has two coming halves, both under SKY-010:

- **The context map** (P2–P3) — one generated manifest listing every loadable artifact with its
  one-line abstract, tier, trigger, and ~token cost. The agent reads *that* (~2–3K for the whole lab)
  and opens only the exact file it needs, instead of loading a whole prose catalog to route. It's the
  digest doctrine extended from "what happened" to "what can I load and what does it cost."
- **The read-time scout** (P4) — for a *wide* question, a throwaway window (a subagent where
  available, else `bin/recall` + targeted reads) greps and distills, and returns only the
  ~500-token conclusion; the raw stays on disk. This is read-time summarization relocated *off* the
  critical window — and it honors the same guardrail as everything else here: **the scout's summary
  is never persisted** (ADR 0002). The corpus stays the source; the summary lives for one query.

Read this section beside [§3 Retrieval](#3-retrieval--read-time-a-cache-never-a-truth): they are the
same idea from two directions — retrieval decides *what to pull in*, default-lean decides *what to
keep out by default*. Together they hold the window to conclusions, not the corpus.

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
