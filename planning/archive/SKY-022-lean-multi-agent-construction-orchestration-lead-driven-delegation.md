---
id: SKY-022
title: "Lean multi-agent construction orchestration: lead-driven delegation"
status: done
horizon: long
created: 2026-09-04
updated: 2026-09-05
phases: 6
current_phase: 6
tier_touched: [T1]
related:
  - docs/system-design.md
  - AGENTS.md
  - docs/conventions/construction.md
  - planning/ideas/SKY-017-the-road-to-full-agent-control-verification-proving-ground-and-an-evidence-earned-ratchet.md
  - "[[SKY-022-progress]]"
---

# SKY-022 · Lean multi-agent construction orchestration: lead-driven delegation

> One accountable Codex lead owns the task, proactively offloads bounded work to cheaper helpers,
> integrates the result, verifies it, and remains the sole owner of the PR.

## 1. Goal

Skynet should get the leverage of multi-agent construction without becoming an orchestration
platform. The target is deliberately small:

```text
Ali states intent
    ↓
lead agent
    ├── Scout    → Luna, read-only investigation
    ├── Mechanic → Luna, deterministic/repetitive edits
    └── Builder  → Terra, bounded implementation
    ↓
lead integrates + verifies
    ↓
PR
    ↓
Ali merges
```

The lead is the foreman. Helpers are temporary workers, never peers, reviewers, or production
operators.

## 2. Decisions

### A · One lead owns the task

One lead owns intent, decomposition, architecture, integration, verification, and the PR. A helper
may report only that its delegated subtask is complete.

### B · Delegation depth = one

Allowed:

```text
Ali → lead → helper
```

Never:

```text
Ali → lead → helper → helper
```

Maximum active helpers: **2**. Raise only after real work proves this is constraining.

### C · Roles are stable; models are replaceable

| Role | Owns | Tier · effort | Writes? |
|---|---|---|---:|
| **Lead** | intent, architecture, decomposition, integration, verification | current interactive lead model; Sol for hard/cross-cutting work | yes |
| **Builder** | bounded implementation behind a clear interface | Terra · high | yes |
| **Mechanic** | repetitive, low-judgement edits | Luna · high | yes |
| **Scout** | bounded search / compare / investigate | Luna · medium | no |

Route by uncertainty and consequence, not prompt length. Model IDs live in `.codex/agents/*.toml`,
`bin/agent`, or the invoking configuration, not in architecture prose.

### D · BIV is the delegation gate

A subtask is delegatable only when it is:

1. **Bounded** — success can be stated in one sentence;
2. **Independent** — it does not need continuous lead interaction;
3. **Verifiable** — the lead can cheaply inspect or test the result.

Ambiguity stays with the lead or goes back to Ali.

### E · Proactive cost-aware delegation is the desired steady state

For a **substantial** task, the lead should actively look for BIV work to offload **without waiting
for Ali to request delegation**.

The decision rule is:

```text
Can this chunk pass BIV?
    ├── no  → lead keeps it
    └── yes → use the cheapest reliable role
               ├── investigation/search       → Scout / Luna
               ├── repetitive/objective edit → Mechanic / Luna
               └── bounded coding judgement  → Builder / Terra
```

The lead should use up to two helpers concurrently when independent work exists. It should still do a
tiny task itself when spawn/coordination cost obviously exceeds the work. The target is **automatic
economic delegation, not maximum fan-out**.

### F · Native tooling first

Use Codex native subagent support when it expresses the job cleanly. `bin/agent` remains the thin
standalone mirror and dry-run/debug path. Do not build a scheduler, queue, DAG engine, worker service,
or custom agent protocol around functionality Codex already provides.

### G · Worktrees only for concurrent writers

Read-only Scouts need none. A single writer in a lead-managed session usually needs none. Use plain
`git worktree` only when two independent writers genuinely require separate filesystem state.
Helpers write; the lead commits and integrates.

### H · Continuity stays tiny

For work likely to cross a session boundary, the lead may keep gitignored `.agent/CHECKPOINT.md`
with only:

```text
Goal
Done
Current
Decisions
Dead ends
Verified
Next
```

Delete it when done. Durable truth remains in git, directives, docs, ADRs, and the journal.

### I · Review stays outside the helper family

A helper never reviews the lead that instructed it. Normal changes use deterministic gates + human
merge. Consequential work may use a fresh cold Sol or cross-provider review. Deterministic checks
outrank model opinion.

### J · Construction never gains production authority

Helpers receive no production credentials or T2/T3 authority. Construction parallelism does not
create a second production-control path. Authored work remains PR-based and never self-merged.

## 3. Non-goals

SKY-022 does **not** build:

- a queue or scheduler;
- a workflow database or durable task ledger;
- a custom DAG engine;
- worker leases, heartbeats, or retry infrastructure;
- automatic merge machinery;
- a second production-control plane;
- Codex App Server integration merely for orchestration aesthetics.

If later dogfooding exposes a concrete transport/control failure that native delegation cannot solve,
that can be minted separately with evidence. It is no longer part of SKY-022.

## 4. Plan

### Phase 1 · Role contract + tiny launcher  `[x]` done 2026-09-04

Shipped Lead / Builder / Mechanic / Scout, BIV, one-level depth, max-two helpers, role/model routing,
`.codex/agents/*.toml`, `.codex/config.toml`, and `bin/agent` with dry-run.

### Phase 2 · Native lead-driven delegation  `[x]` done 2026-09-04

Proved one real lead+helper task with Scout + Builder, lead integration, machine-enforced helper
constraints, and final verification owned by the lead.

### Phase 3 · Lightweight continuity  `[x]` done 2026-09-04

Proved cold-session continuation from only canonical repo context + disposable
`.agent/CHECKPOINT.md` + git state.

### Phase 4 · Parallel writers only where they pay  `[x]` done 2026-09-04

Proved two concurrent writers using plain git worktrees. Helpers write; the lead commits, resolves
conflicts, integrates, and tears worktrees down.

### Phase 5 · Dogfood the foreman model  `[x]` done 2026-09-04

Covered the routing matrix across real work: single lead, Luna Mechanic, Luna Scout, hard lead + Terra
Builder, and parallel writers. Native shallow delegation, plain Git, and the disposable checkpoint
were sufficient. No queue, scheduler, ledger, worktree manager, retry layer, or wider fan-out was
earned.

**P5 conclusion:** the remaining issue is not transport. It is **policy bias**. The existing doctrine
still tells the lead that the default is to avoid delegation, which underuses the cheaper workers and
requires Ali to think about orchestration. The desired user experience is instead: **Ali states the
job; the lead automatically decides what should be delegated and routes BIV chunks downward.**

### Phase 6 · Flip to proactive cost-aware delegation  `[x]` done 2026-09-04

Goal: make automatic delegation the normal behavior for substantial construction tasks while keeping
BIV, one-level depth, the two-helper cap, lead accountability, and production isolation unchanged.

Steps:
1. Update `docs/conventions/construction.md` so the doctrine no longer says "default: don't delegate."
   Replace it with: **for substantial work, proactively search for BIV subtasks and offload them to
   the cheapest reliable role without waiting for Ali to request delegation.**
2. Keep the anti-overengineering rule: tiny tasks stay with the lead when coordination would cost
   more than execution. The goal is cost-aware delegation, not fan-out for its own sake.
3. Make the routing rule explicit and compact:
   - Scout / Luna for bounded investigation and search;
   - Mechanic / Luna for deterministic repetitive edits;
   - Builder / Terra for bounded implementation requiring coding judgement;
   - lead retains ambiguity, architecture, cross-cutting decisions, integration, and final verification.
4. Update the quick-reference/runbook wording so a fresh Codex lead sees the proactive rule during
   normal construction work without Ali having to say "spawn workers".
5. Remove stale App Server language from SKY-022 and any construction docs that imply App Server is
   the next step. Do **not** add an App Server adapter, scheduler, or new orchestration component.
6. Dogfood the flipped policy on at least three real tasks:
   - one substantial task where the lead autonomously spawns a Luna helper;
   - one substantial task where the lead autonomously spawns a Terra Builder;
   - one small task where the lead correctly chooses **not** to delegate.
   Ali must give only the task intent, not an instruction to delegate.
7. Record whether the lead actually delegates without prompting, whether routing is economical, and
   whether any delegated chunk causes expensive rework. Adjust wording only if the evidence warrants
   it.
8. Run the existing construction/helper/invariant tests and full repo gates. No authority boundary or
   helper sandbox may widen.

Exit criteria:
- on substantial work, a fresh lead proactively identifies and delegates BIV subtasks without Ali
  asking it to spawn workers;
- Luna receives cheap search/mechanical work and Terra receives bounded coding judgement;
- a tiny task remains single-agent when delegation would be wasteful;
- one-level depth and max-two-helper cap still hold;
- helper sandboxes and production isolation are unchanged;
- no App Server or new orchestration service is introduced;
- Ali's normal interface is simply: **state the task and let the lead orchestrate.**

**P6 conclusion:** a plain task-intent prompt caused the lead to route one bounded read-only audit
to a Luna Scout and one bounded doctrine implementation to a Terra Builder, without an instruction
from Ali to spawn helpers. Both returned usable work without a corrective helper round. The lead
kept the small directive/journal/roadmap close-out because delegating it would cost more than doing
it. Native shallow delegation remains sufficient; no wider fan-out or orchestration component was
earned.

## 5. Operating doctrine after completion

Normal substantial task:

```text
Ali: "Do the task"
        ↓
lead understands + decomposes
        │
        ├── proactively offloads cheap BIV work
        │      ├── Luna Scout
        │      ├── Luna Mechanic
        │      └── Terra Builder
        │
        ├── keeps ambiguity / architecture / integration
        ↓
lead verifies everything
        ↓
PR
        ↓
Ali merges
```

Tiny task:

```text
Ali → lead → done
```

The lead decides. Ali does not micromanage worker spawning.

## 6. ▶ Execute prompt

```text
Read planning/archive/SKY-022-lean-multi-agent-construction-orchestration-lead-driven-delegation.md
and execute Phase 6 only.

Follow AGENTS.md and docs/system-design.md. Flip construction doctrine to proactive cost-aware
BIV delegation: on substantial work, the lead should autonomously offload bounded, independent,
verifiable chunks to the cheapest reliable helper without waiting for Ali to ask. Preserve one lead,
one delegation level, max two active helpers, helper sandboxes, production isolation, lead-owned
integration/verification, and human merge. Remove the App Server phase rather than implementing it.
Dogfood the new behavior and perform phase close-out when the exit criteria pass.
```

## 7. Phase close-out

- Land one reviewable PR; the agent never self-merges it.
- Refresh `[[SKY-022-progress]]` with what shipped and the observed delegation behavior.
- Flip P6 to `[x]`, set `current_phase: 6`, and mark SKY-022 done if exit criteria pass.
- Run `bin/plan list`.
- Put raw run evidence in `journal/`, not durable doctrine.

## 8. Status log

- 2026-09-04 — SKY-022 minted: one accountable lead, shallow native helpers, tiny checkpoint,
  worktrees by exception, dogfood before automation.
- 2026-09-04 — P1–P5 completed and dogfooded across the full routing matrix.
- 2026-09-04 — P6 **replaced before execution**: the planned thin Codex App Server experiment was
  removed. Evidence from P1–P5 showed native delegation was sufficient; the actual mismatch was the
  doctrine's conservative "default: don't delegate" bias. New P6 flips the steady state to proactive,
  cost-aware BIV delegation so Ali can state intent and let the lead automatically route cheap work
  to Luna/Terra helpers.
- 2026-09-04 — P6 completed: proactive routing is now the construction default for substantial
  work; one lead, BIV, one-level depth, the two-helper cap, helper sandboxes, production isolation,
  lead-owned verification, and human merge are unchanged. SKY-022 is done.
