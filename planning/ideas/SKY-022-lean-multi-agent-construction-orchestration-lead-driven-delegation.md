---
id: SKY-022
title: "Lean multi-agent construction orchestration: lead-driven delegation"
status: in-progress
horizon: long
created: 2026-09-04
updated: 2026-09-04
phases: 6
current_phase: 2
tier_touched: [T1]
related:
  - docs/system-design.md
  - AGENTS.md
  - docs/design/memory.md
  - docs/design/observability.md
  - planning/ideas/SKY-017-the-road-to-full-agent-control-verification-proving-ground-and-an-evidence-earned-ratchet.md
  - "[[SKY-022-progress]]"
---

# SKY-022 · Lean multi-agent construction orchestration: lead-driven delegation

> Give one capable Codex lead a small bench of helpers. The lead owns the task, delegates only bounded work to smaller agents, integrates the result, and stays understandable enough that Ali can reason about the whole system from memory.

## 1. Problem / motivation

Skynet does not need an enterprise workflow platform to build a homelab. It does need a little more leverage than a single monolithic coding session.

The useful target is deliberately small:

```text
Ali
  ↓
lead agent
  ├── scout: inspect / research, read-only
  ├── mechanic: repetitive edits
  └── builder: bounded implementation chunk
  ↓
lead integrates
  ↓
tests / gates
  ↓
PR
  ↓
Ali merges
```

The lead remains the one accountable operator. Subagents are temporary helpers, not peers competing for control of the task.

This directive exists to make that pattern explicit, repeatable and pleasant without building a queue, scheduler, workflow database, daemon, task ledger, custom DAG engine, or home-grown CI platform before one is actually needed.

### The problem to solve

Today a large construction task can force one agent to spend context on everything at once:

- architecture and implementation;
- searching the repo for affected call sites;
- mechanical fixture or documentation updates;
- independent investigation of APIs or prior art;
- final integration and verification.

Some of those subtasks are naturally independent and cheap to delegate. A lead should be able to hand them to a smaller model, keep its own context focused on the hard part, then verify and integrate the returned work.

### The non-problem

We are **not** trying to maximize the number of simultaneous agents.

The default remains:

```text
one task → one lead → done
```

Delegation is used only when it reduces cognitive load or elapsed time without creating more coordination cost than it saves.

## 2. Decisions

### A · One lead owns the task

Options:

- **Peer swarm:** several equal agents coordinate among themselves. Powerful, but ownership becomes fuzzy and integration becomes a second project.
- **Central orchestrator service:** software assigns tasks, tracks state, retries workers and merges results. Reliable at scale, but far beyond the demonstrated need.
- **Lead + bounded helpers:** one agent owns intent, scope, integration and final verification; helpers receive narrow jobs and report back.

**Decision: lead + bounded helpers (CHOSEN).**

The lead is accountable for the whole result. A helper can say only "my delegated subtask is complete," never "the phase is complete."

### B · Delegation depth = one

Allowed:

```text
Ali → lead → helper
```

Not allowed:

```text
Ali → lead → helper → helper → ...
```

**Decision: one delegation level (CHOSEN).** It keeps context ownership and failure diagnosis obvious.

Initial maximum active helpers: **2**. Raise only after real work demonstrates that two is constraining rather than comfortably sufficient.

### C · Roles are stable; models are replaceable

Canonical roles:

| Role | Purpose | Tier · effort | Writes? |
|---|---|---|---:|
| **Lead** | Owns intent, architecture, decomposition, integration, verification | Terra `xhigh` (→ Sol for hard/cross-cutting; Sol-only `max` for a brutal task) | yes |
| **Builder** | Implements one bounded component with a clear interface | Terra `high` | yes |
| **Mechanic** | Repetitive edits, fixtures, renames, formatting, routine docs | Luna `high` | yes |
| **Scout** | Searches, compares, investigates, returns a concise report | Luna `medium` | **no** |

Tier · effort are benchmark-backed (P1), routed by uncertainty and consequence. The Terra↔Luna
choice *is* the Builder↔Mechanic split: **Builder → Terra** because novel bounded logic is where
correctness margin matters (Terra wins every coding benchmark, and a wrong builder costs a rework
loop paid in expensive lead tokens — dwarfing Luna's small per-token saving); **Mechanic → Luna**
because high-volume deterministic edits with airtight checks are where Luna's economics dominate. The
lead reasons hardest (effort, not tool access, buys first-try reliability). Model IDs live in
configuration or the invoking tool (`bin/agent`, `.codex/agents/*.toml`), not in the architecture —
a future model swap should not change the role contract. Details + the full evidence:
[`docs/conventions/construction.md`](../../docs/conventions/construction.md).

### D · Delegation must pass the BIV test

A subtask is delegatable only when it is:

1. **Bounded** — success can be stated clearly;
2. **Independent** — it does not require constant coordination with the lead;
3. **Verifiable** — the lead can cheaply inspect or test the result.

Good:

- "Find every call site that assumes the old entity ID and report file + function."
- "Update these fixtures to schema v2; do not touch production code."
- "Implement parser X behind this existing interface and run tests A/B."

Bad:

- "Figure out the architecture."
- "Make this subsystem better."
- "Decide what we should build."

Ambiguity stays with the lead or goes back to Ali. A bigger model is not a substitute for a clear objective.

### E · Native tooling first

Use the agent platform's own subagent/delegation support when it can express the job cleanly.

Do **not** build a scheduler around something Codex already does natively.

If native delegation is unavailable for a particular task, a second ordinary Codex invocation is acceptable. The repository contract, not the transport, is what matters.

### F · Worktrees only for concurrent writers

Read-only scouts need no worktree.

A helper making a small edit within a lead-managed native session may not need one either if the platform safely coordinates file writes.

Use `git worktree` when two independent writing agents genuinely need separate filesystem state. Git is the isolation mechanism; SKY-022 does not build a worktree manager.

### G · Continuity is a small local checkpoint, not another memory system

For tasks likely to cross sessions/context boundaries, the **lead** maintains:

```text
.agent/CHECKPOINT.md
```

`.agent/` is gitignored.

The checkpoint contains only:

```text
Goal
Done
Current
Decisions needed to continue
Dead ends not to retry
Verification passed / remaining
Next exact step
```

It is disposable working memory, not truth. On completion, durable facts go to the proper home: directive/docs/ADR/journal/git, then the checkpoint disappears.

No separate run ledger in v1. Git history, the directive, the PR and the journal already cover durable history.

### H · Review is outside the helper family

A helper is not an independent reviewer of the lead that instructed it.

Normal changes use existing tests/gates and human review. Consequential changes may additionally receive a **fresh cold Sol review**, and especially sensitive cross-provider changes may receive a Claude review.

Review remains optional and proportional to risk; deterministic gates outrank every model opinion.

### I · Complexity must be earned

SKY-022 deliberately does **not** start with:

- GitHub issue queues;
- orchestration daemons;
- persistent workflow state;
- event ledgers;
- custom DAG engines;
- heartbeats;
- worker leases;
- bespoke retry frameworks;
- automatic merge machinery.

If repeated dogfooding exposes a concrete failure mode, automate that failure mode specifically.

## 3. Scope

### In scope

- a clear lead/helper operating contract;
- simple role/model routing;
- native lead-driven delegation;
- read-only scouting;
- bounded builder/mechanic delegation;
- a tiny optional `.agent/CHECKPOINT.md` continuity convention;
- optional `git worktree` isolation for truly parallel writers;
- proportional cold review guidance;
- a final thin Codex App Server phase after the simple model is proven.

### Non-goals

- production multi-agent operation;
- changing Skynet's A0–A5 autonomy ladder;
- widening T2/T3 access;
- giving construction helpers production credentials;
- a general-purpose agent platform;
- maximizing concurrency;
- automated merging of authored PRs;
- replacing `AGENTS.md`, directives, git, CI or existing deterministic gates.

### Trust boundary

SKY-022 is a **construction** pattern. Production operation remains behind the existing Skynet trust model and `bin/ops`.

Construction parallelism must never become an accidental second production-control path.

## 4. The plan

### Phase 1 · Role contract + tiny launcher  (~1–2h)   `[x]` done 2026-09-04

Goal: make the mental model concrete without building orchestration infrastructure.

Steps:
1. Add a short construction/multi-agent convention in the appropriate existing docs/conventions location rather than bloating `AGENTS.md`.
2. Define Lead / Builder / Mechanic / Scout and the BIV delegation test.
3. Define initial routing: Terra lead by default, Sol for genuinely hard/cross-cutting work, Terra builder, Luna mechanic/scout where appropriate.
4. Add the one-level / max-two-helper rule.
5. If it materially improves ergonomics, add a tiny `bin/agent` wrapper or equivalent helper that resolves a role to the configured Codex model. Keep it thin enough to read in one sitting.
6. Add a dry-run mode if a wrapper exists so the resolved role/model/prompt is visible before launch.
7. Do not add a service, state store or daemon.

Exit criteria:
- Ali can explain the whole model in one minute;
- a Lead, Builder, Mechanic and Scout can each be invoked deliberately;
- model mapping is centralized rather than scattered;
- no production authority changes.

### Phase 2 · Native lead-driven delegation  (~1–2h)   `[x]` done 2026-09-04 (PR #173)

Goal: prove the useful part of multi-agent work on a real Skynet task.

Steps:
1. Pick one real T1/repo-only task with at least two natural subtasks.
2. Run it with one Terra or Sol lead.
3. Have the lead decide whether delegation is worthwhile rather than forcing delegation.
4. Delegate one read-only Scout task and one bounded Builder or Mechanic task using native Codex delegation where available.
5. Require each helper prompt to state scope, output expected, write allowance, and verification requirement.
6. Lead receives the results, inspects them, integrates them, runs final tests/gates and owns the PR.
7. Record any coordination friction in the normal raw journal, not in a new telemetry system.

Exit criteria:
- one real task completes with useful delegation;
- lead remains clearly accountable;
- helper work is independently verifiable;
- delegation saves effort/context rather than creating obvious coordination tax.

### Phase 3 · Lightweight continuity  (~1–2h)   `[ ]` not started

Goal: make long tasks survive a fresh lead session with almost no machinery.

Steps:
1. Add `.agent/` to `.gitignore`.
2. Document the compact `.agent/CHECKPOINT.md` shape.
3. Define when the lead writes it: meaningful milestone, handoff/context reset, blocker, or before intentionally ending a long session. Not after every command.
4. Start a real task, stop after a meaningful milestone, then resume in a fresh Codex lead from only:
   - `AGENTS.md` / required design context;
   - the named SKY phase;
   - `.agent/CHECKPOINT.md`;
   - `git status` + `git diff`.
5. Verify the fresh lead continues from the recorded next step without rereading an old conversation transcript.
6. Delete the checkpoint when the task is complete after moving durable information to its correct home.

Exit criteria:
- a cold lead resumes a half-finished task correctly;
- checkpoint stays small and disposable;
- no second durable memory/ledger system is introduced.

### Phase 4 · Parallel writers only where they pay  (~1–2h)   `[ ]` not started

Goal: prove safe parallel editing using plain Git rather than custom coordination software.

Steps:
1. Pick a task with two genuinely independent writing subtasks.
2. Give each writer its own branch/worktree with ordinary `git worktree` commands.
3. Lead retains the integration branch and responsibility.
4. Run both helpers concurrently, bounded to their declared file/scope surfaces.
5. Integrate their commits/diffs through normal Git.
6. Exercise one intentional overlap/conflict and confirm the lead, not another orchestration layer, resolves it.
7. Document the rule: worktree by exception for parallel writers, not by default for every agent invocation.

Exit criteria:
- two writers can make progress without trampling one checkout;
- integration remains understandable with normal Git tools;
- no custom worktree lifecycle service is required.

### Phase 5 · Dogfood the foreman model  (~1–2h sessions across real work)   `[ ]` not started

Goal: test the pattern enough to distinguish real needs from imagined ones.

Run at least five real construction tasks covering:

1. one task completed entirely by a single Terra lead;
2. one task with Luna mechanical delegation;
3. one task with a read-only Scout;
4. one hard task led by Sol with a bounded Terra builder;
5. one task using two parallel writer worktrees.

For each, capture only useful observations in the existing journal:

- Was delegation actually faster/cleaner?
- Did the lead delegate too much or too little?
- Did helper output require expensive rework?
- Did context stay cleaner?
- Did worktree handling become annoying?
- Did we repeatedly wish for programmatic spawn/steer/resume/monitoring?

At phase close, write a short decision in this directive on what, if anything, deserves additional automation.

Exit criteria:
- at least five real tasks exercised the model;
- no recurring ambiguity about ownership;
- no helper accidentally gains production authority;
- any request for more orchestration is backed by repeated evidence rather than aesthetics.

### Phase 6 · Thin Codex App Server control surface  (~1–2h)   `[ ]` not started

Goal: add **only** the small amount of programmable control that proved useful in P1–P5, using Codex App Server instead of inventing our own agent protocol.

This phase is intentionally last. The simple lead/helper model must work before software starts coordinating it.

Steps:
1. Read the installed/current Codex App Server interface and generate/use its current schema rather than hard-coding assumptions.
2. Build the smallest practical adapter that can:
   - start a Codex thread/turn for a named role;
   - stream or surface progress;
   - return the final result to the lead;
   - cancel/stop a child cleanly;
   - optionally resume/continue when App Server supports that cleanly.
3. Keep the adapter stateless beyond what App Server itself needs for the active interaction; git + directive + checkpoint remain sufficient to recover if App Server state disappears.
4. Expose the adapter behind the same role vocabulary from P1 so callers ask for `builder` / `mechanic` / `scout`, not App Server internals.
5. Do **not** add a queue, scheduler, database, durable workflow engine, GitHub polling daemon, automatic merge system, or generic DAG executor.
6. Compare one real delegated task through App Server against the native/manual path.
7. Keep the App Server layer only where it removes demonstrated friction. If it merely adds indirection, document that result and leave the native path primary.

Exit criteria:
- a lead can programmatically launch at least one bounded helper through a tiny App Server adapter;
- the adapter remains optional and replaceable;
- losing App Server state cannot lose architectural/system truth;
- the construction model is still understandable as "one lead with a couple of helpers," not as a distributed system.

## 5. Operating doctrine after completion

The desired steady state is:

```text
well-specified normal task
        ↓
     Terra lead
        │
        ├── delegates nothing if unnecessary
        ├── Luna mechanic for chores
        ├── Luna/Terra scout for bounded investigation
        └── Terra builder for an isolated implementation chunk
        ↓
 lead integrates + verifies
        ↓
       PR
        ↓
      Ali
```

Hard/cross-cutting task:

```text
Sol lead
  ├── Terra builder
  └── Scout
  ↓
integrate / verify
  ↓
optional cold review
  ↓
PR
```

The lead is the foreman. Helpers are tools with judgment, not a committee.

## 6. ▶ Execute prompt

```text
Read planning/ideas/SKY-022-lean-multi-agent-construction-orchestration-lead-driven-delegation.md and execute Phase <N>.

Follow AGENTS.md and docs/system-design.md. Preserve SKY-022's simplicity doctrine: one accountable lead, one delegation level, at most two active helpers initially, delegate only bounded/independent/verifiable work, and do not build orchestration infrastructure the phase does not explicitly require.

Construction work does not gain production authority. Plan loudly, then run quietly. Land authored work by PR and never self-merge it. When the phase exit criteria are met, perform the phase close-out.
```

## 7. Phase close-out

After every completed phase:

- [ ] Land authored work through a PR; the agent never merges its own authored PR.
- [ ] Write/refresh `[[SKY-022-progress]]` with what shipped, what was learned, and the next exact phase.
- [ ] Flip the completed phase box to `[x]`, bump `current_phase`, `updated`, and status as appropriate.
- [ ] Run `bin/plan list` to refresh the roadmap.
- [ ] Put raw surprises/dead ends in the journal rather than bloating durable design docs.
- [ ] Leave a cold-startable Continue prompt.

Continue prompt:

```text
Continue planning/ideas/SKY-022-lean-multi-agent-construction-orchestration-lead-driven-delegation.md at Phase <N+1>.
Resume from [[SKY-022-progress]]. Follow AGENTS.md and preserve the one-lead / shallow-delegation / complexity-must-be-earned doctrine.
```

## 8. Status log

- 2026-09-04 — minted. Chosen shape: one accountable lead, shallow native delegation to Builder/Mechanic/Scout helpers, lightweight checkpointing for long tasks, worktrees only for genuine parallel writers, dogfood before automation, and Codex App Server as the **final thin control-surface phase**, not the foundation.
- 2026-09-04 — **P1 done** (PR #172): role contract in `docs/conventions/construction.md`, native `.codex/agents/*.toml` + `.codex/config.toml` cap, `bin/agent` launcher.
- 2026-09-04 — **P2 done** (PR #173): first real lead+helper run. A Claude lead delegated to real Codex helpers via `bin/agent` — a read-only Scout (`gpt-5.6-luna`) scoped the gap, a Builder (`gpt-5.6-terra`) implemented it — to make the construction doctrine's `[testable]` claims machine-enforced (`invariants.json` `construction` section + `check-invariants.sh` check #6 + `tests/construction-test.sh`, wired into hook + CI). Fixed a P1 `bin/agent` bug found by dogfooding (`codex exec` 0.149.0 has no `--ask-for-approval`). Lead verified all helper output incl. live fail-closed proofs; owns the PR, does not self-merge. Raw episode in `journal/`.
