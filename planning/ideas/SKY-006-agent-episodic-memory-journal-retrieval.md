---
id: SKY-006
title: Agent episodic memory: journal + retrieval
status: draft
horizon: short
created: 2026-08-17
updated: 2026-08-17
phases: 3
current_phase: 0
tier_touched: [T1]   # repo files + a local, git-rebuildable index on the ops VM. No blast radius.
related:
  - docs/design/observability.md
  - docs/decisions
  - planning/scratchpad/2026-08-17-declarative-future-and-agent-cognition.md
  - "[[SKY-004-progress]]"
  - "[[SKY-005-progress]]"
  - "[[SKY-006-progress]]"
---

# SKY-006 · Agent episodic memory: journal + retrieval

> Close Skynet's memory gap. The agent has strong *semantic* and *procedural* memory but weak
> *episodic* memory — it can't cheaply reconstruct how the lab got here or what was already tried.
> Git stores everything; the missing piece is **retrieval**.

## 1. Problem / motivation
Skynet is stateless by design — every session is a fresh mind that rebuilds the world from git. That
makes memory *infrastructure*, not a nicety. Score it honestly:

| Kind | What | Today |
|---|---|---|
| **Working** | context window | fine |
| **Semantic** | facts / current state | **strong** — MEMORY.md, docs/, inventory/, generated/ |
| **Procedural** | how-to | **strong** — runbooks/, scripts/, bin/ |
| **Episodic** | what *happened*, the trajectory | **weak** — only raw git history + progress memories |

**The gap is episodic.** A cold agent can't efficiently answer *how did the lab get here, what was
tried, what failed.* Git history technically holds it, but it isn't shaped for recall — the problem
isn't storage, it's **retrieval**. (Scratchpad thesis §4.)

## 2. Brainstorm — options considered

**The episodic store**
- **Option A — lean on git history + commit messages.** Zero new files, but un-queryable; a cold
  agent won't `git log` six months to reconstruct a decision.
- **Option B — an append-only `journal/`.** Dated session / incident / decision records — intent,
  actions, grants used, outcome, and crucially a **graveyard of tried-and-abandoned approaches**
  (negative results are memory too). The immutable episodic log git history only *implies*.
- **Decision:** **Option B (CHOSEN).** Fed automatically by the nightly and by SKY-005 diagnoses.
  **Key rule (research brief): write RAW episodes, summarize at *read* time — never at write time**,
  or the episodic signal is destroyed before it's ever used.

**Cold-boot retrieval**
- **Option A — grep only.** Status quo; doesn't scale past a few months.
- **Option B — a rolling digest.** Extend `05-state-of-the-lab.md` into a maintained "state + recent
  decisions + open threads" page the agent reads first. Cheap, high-leverage, no new infra.
- **Option C — a local semantic index.** A lightweight, **git-rebuildable** embedding index (e.g.
  sqlite-vec class) over repo + journal so a cold agent retrieves by similarity. Must be a **cache,
  never a source of truth** — regenerable from git, so statelessness holds.
- **Decision:** **B now, C as a later phase (both CHOSEN, staged).** Digest is the 80/20; the index
  is the bigger swing, pending the research brief.

**Decision memory**
- **Decision (CHOSEN):** enforce ADRs in `docs/decisions/` for every non-trivial choice, so the agent
  never re-litigates a settled question — the same discipline `[[SKY-###-progress]]` memories apply
  lightly today.

## 3. The plan
- **Scope / non-goals:** journal, rolling digest, ADR discipline, and a git-rebuildable semantic
  index. **Non-goal:** any external/hosted memory service (would break statelessness + add a truth
  source).
- **Hosts & tiers touched:** ops VM only, repo files + a local index. **T1**, no blast radius.
- **Rollback posture:** additive; `git revert`. The index is disposable (rebuildable from git).
- **Grants / human actions:** none.

### Phase 1 — the journal  (~1–2h)   `[ ]` not started
Create `journal/` + a convention (session / incident / decision records, incl. a graveyard section);
have the nightly append to it. Exit: nightly runs and SKY-005 diagnoses land dated journal entries.

### Phase 2 — rolling digest  (~1–2h)   `[ ]` not started
Extend the generated `05-state-of-the-lab.md` into a cold-boot "state + recent decisions + open
threads" digest. Exit: a fresh session can orient from one page.

### Phase 3 — git-rebuildable semantic index  (~1–2h)   `[ ]` not started
Evaluate + stand up a local embedding index (per research brief) that rebuilds from git. Exit: the
agent can retrieve relevant past journal/doc context by similarity; wiping + rebuilding the index
changes nothing.

## 4. ▶ Execute prompt
```
Read planning/projects/SKY-006-agent-episodic-memory-journal-retrieval.md and execute Phase <N>.
Follow AGENTS.md: plan loudly then run quietly, never merge your own PRs, request the
narrowest host / shortest grant the phase needs, and checkpoint at the listed human/grant
steps. When the phase's exit criteria are met, do the "Phase close-out" at the bottom.
```

## 5. Phase close-out (resume material)
- [ ] Land the work via **PR** (agent never merges its own).
- [ ] Write/refresh a memory `SKY-006-progress` (what shipped, what's next, gotchas) + a MEMORY.md pointer.
- [ ] Bump this file's frontmatter (`current_phase`, `status`, `updated`) and flip the phase box to `[x]`.
- [ ] `bin/plan list` to refresh the roadmap index.
- [ ] Paste the **Continue prompt** below to resume in a fresh session:
```
Continue planning/projects/SKY-006-agent-episodic-memory-journal-retrieval.md at Phase <N+1>.
Prereqs carried from the last phase: <…>. Resume context from memory [[SKY-006-progress]].
Follow AGENTS.md as above.
```

## 6. Status log
- 2026-08-17 — created (draft) from the declarative-future brainstorm §4. Memory gap is episodic; fix
  is journal + retrieval, not more storage. Research feeding this: `planning/scratchpad/research/2026-08-17-reactive-memory.md`.
