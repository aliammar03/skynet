---
id: SKY-026
title: "Overhaul agent orchestration around a Main-directed worker swarm"
status: in-progress
horizon: long
created: 2026-09-10
updated: 2026-09-10
phases: 5
current_phase: 0
tier_touched: [T1]
related:
  - AGENTS.md
  - docs/conventions/construction.md
  - .codex/config.toml
  - .codex/agents/
  - bin/agent
  - planning/archive/SKY-022-lean-multi-agent-construction-orchestration-lead-driven-delegation.md
  - planning/projects/SKY-025-rebuild-the-skynet-engine-in-python.md
  - "[[SKY-026-progress]]"
---

# SKY-026 · Overhaul agent orchestration around a Main-directed worker swarm

> Replace SKY-022's small lead + two-helper construction model with a Skynet-native adaptation of
> `viettran-edgeAI/codex_workflow`: expensive intelligence owns decisions, cheap specialist agents
> own bounded work, context is routed deliberately, workers are batched, verification is independent,
> and failed reviews return a single paste-ready fix prompt to the original implementation session.

## 1. Goal and donor

Skynet should stop treating multi-agent work as "a lead that sometimes delegates" and adopt a real
orchestration topology designed around **Main-agent context economy**.

The design donor is:

- repository: `https://github.com/viettran-edgeAI/codex_workflow`
- donor snapshot reviewed when this directive was minted: commit
  `6d9b06f73bee7f899001b0bb102c70529a24313f`
- packaged architecture described there as version `1.1.17`

Implementation should inspect the donor source contracts again before changing Skynet. Borrow the
current upstream implementation **aggressively** where it still fits. Prefer source contracts over
README prose when they disagree. The primary donor surfaces are:

- `codex_workflow/AGENTS.md`
- `codex_workflow/heavy_route.md`
- `codex_workflow/medium_route.md`
- `codex_workflow/agents/*.toml`
- `codex_workflow/archivist.md`
- the deployment-token-report skill/parser and its tests
- lifecycle/runtime code only where it provides a useful deterministic primitive rather than an
  installer for files Skynet already owns

This directive is intentionally willing to overturn SKY-022. Where SKY-026 lands a conflicting
construction rule, **SKY-026 wins**. SKY-022 remains archived historical evidence; do not rewrite its
history to pretend this architecture was always the plan.

### Target topology

```text
                              Ali
                               │
                               ▼
                    ┌─────────────────────┐
                    │        MAIN         │
                    │ session-selected   │
                    │                     │
                    │ architecture        │
                    │ decomposition       │
                    │ causal decisions    │
                    │ integration         │
                    │ acceptance          │
                    └─────────┬───────────┘
                              │
       ┌──────────────────────┼──────────────────────────┐
       │                      │                          │
       ▼                      ▼                          ▼
┌──────────────┐      ┌──────────────┐          ┌────────────────┐
│  COMPANION   │      │ INVESTIGATOR │          │   EXECUTORS    │
│ Luna xhigh   │      │ Luna xhigh   │          │   Luna max     │
│ persistent   │      │ disposable   │          │ bounded writes │
│ read-only    │      │ read-only    │          └───────┬────────┘
└──────────────┘      └──────────────┘                  │
                                                       │ hard package
                                                       ▼
                                              ┌────────────────┐
                                              │ SENIOR EXECUTOR│
                                              │   Sol medium   │
                                              │ max one active │
                                              └────────────────┘
                                                       │
                                      implementation   │
                                                       ▼
                                              ┌────────────────┐
                                              │     TESTER     │
                                              │  Luna xhigh    │
                                              │ independent QA │
                                              └───────┬────────┘
                                                      │ defect
                                                      ▼
                                               owning Executor
                                                      │
                                                      └──► same Tester

                                      verified deployment
                                               │
                                               ▼
                                        ┌────────────┐
                                        │ ARCHIVIST  │
                                        │ Luna xhigh │
                                        │ docs/report│
                                        └────────────┘
```

No worker orchestrates children. The Main coordinates every worker directly. Do not introduce an LLM
"wave manager", scheduler, queue, DAG engine, workflow database, heartbeat system, lease service, or
custom agent transport unless native Codex capabilities demonstrably cannot express a required
behavior and Ali explicitly authorizes a new directive for it.

## 2. Decisions

### A · Borrow the donor architecture, not its installer or second memory system — CHOSEN

Copy the orchestration semantics and worker contracts closely. Do **not** install
`codex_workflow` into Skynet as a parallel framework and do not create its `agent_docs/` tree as a
second source of truth.

Map donor continuity onto Skynet's existing authoritative surfaces:

| Donor concept | Skynet owner |
|---|---|
| project overview / architecture | `docs/system-design.md` + relevant `docs/design/` spokes |
| project structure / ownership | repo + generated context map where applicable |
| progress / current position | active `planning/projects/SKY-###` directive |
| diary / lessons / discarded approaches | append-only `journal/` |
| latest-session handoff | directive close-out + generated agent digest/context map + optional disposable checkpoint |
| public/operator docs | their existing canonical docs/runbooks |

A fact gets one canonical home. Do not mirror the same operational truth into another durable tracker.

### B · Main is a decision owner, not an extra production worker — CHOSEN

In Heavy route, the Main owns:

- task understanding and route selection/confirmation;
- architecture and cross-package contracts;
- causal/root-cause decisions when broad project context matters;
- decomposition and worker ownership;
- integration decisions;
- risk and authority decisions;
- final acceptance and user communication.

In Heavy route, Main should **not** routinely:

- write production code or tests;
- perform implementation assigned to an Executor;
- run the Tester's verification on its behalf;
- do ordinary deployment operations;
- chase routine logs or environment diagnostics;
- take over a worker's package merely because the first attempt failed.

Main may perform a minimal direct read when the exact evidence controls an architecture, scope, risk,
or acceptance decision. Everything else should be routed to the correct specialist.

### C · Adopt Light / Medium / Heavy route semantics — CHOSEN

Borrow the donor's three-route model.

| Route | Main owns implementation? | Workers | Use |
|---|---:|---|---|
| **Light** | yes | none | Q&A, tiny leaf tasks, quick bounded edits |
| **Medium** | yes | Companion, Investigator, Archivist as useful | substantive work needing context/research support but where Main should personally implement |
| **Heavy** | no for ordinary production | full topology | large/cross-cutting work that can be decomposed |

Default to **Light** when no route is selected by the user or active directive packet. Do not silently
upgrade an ordinary interactive task merely because workers exist. A directive may explicitly select
Medium or Heavy so Ali does not have to micromanage orchestration every phase.

Once Medium or Heavy is selected for a substantive deployment, keep that route for that deployment
unless the user or directive changes it.

### D · Adopt the donor role split and model defaults — CHOSEN

Initial Skynet defaults, matching donor source contracts where practical:

| Role | Model | Effort | Sandbox | Quantity |
|---|---|---|---|---:|
| Main | session-selected | task-selected | invoking session | 1 |
| Companion | `gpt-5.6-luna` | xhigh | read-only | exactly 1 persistent in deployment state |
| Investigator | `gpt-5.6-luna` | xhigh | read-only | as needed |
| Default Executor | `gpt-5.6-luna` | max | workspace-write | as needed |
| Senior Executor | `gpt-5.6-sol` | medium | workspace-write | max 1 |
| Tester | `gpt-5.6-luna` | xhigh | workspace-write | as needed |
| Archivist | `gpt-5.6-luna` | xhigh | workspace-write | 1 at substantive closure, plus explicit doc assignments |

The current donor README may drift from source TOMLs. **The source TOML wins.** Verify exact model IDs,
effort names, sandbox support, and agent configuration against the installed Codex harness before
landing them. Do not silently substitute an unsupported identifier.

For SKY-026 implementation itself, prefer **Sol High** as the Main for the architecture/contract
phases. Astra Medium may be used when a genuinely consequential cross-cutting decision benefits from
it. After the new workers exist, dogfood the new Heavy route rather than continuing to emulate it by
hand.

### E · Replace Scout / Mechanic / Builder with the donor roles — CHOSEN

`scout`, `mechanic`, and `builder` were useful SKY-022 stepping stones. They should not remain as a
second active role vocabulary after SKY-026.

Retire their `.codex/agents/*.toml` definitions, launcher routes, tests and doctrine when the new roles
replace all known callers. A compatibility alias/shim is allowed only for a demonstrated external
caller and must have an owner plus removal condition. Do not keep aliases merely for familiarity.

### F · Knowledge capsules are the worker API — CHOSEN

Use the donor's role-specific capsule shapes. Every initial worker assignment starts with a deployment-
unique **Task ID**. Follow-ups repeat Task ID and send only changed capsule parts.

| Role | Initial capsule |
|---|---|
| Companion | `Project Context Scope` · `Context Task + Goal` · `Main-Agent Context Guidance` |
| Investigator | `Investigation Context` · `Evidence Question + Goal` · `Main-Agent Investigation Guidance` |
| Default/Senior Executor | `Implementation Context + Ownership` · `Implementation Task + Goal` · `Main-Agent Implementation Guidance` |
| Tester | `Verification Context` · `Verification Goal` · `Main-Agent Verification Guidance` |
| Archivist | `Documentation Context + Audience` · `Documentation Task + Goal` · `Main-Agent Documentation Guidance` |

A capsule transfers the Main's relevant **knowledge and decisions**, not just a command. Include only
material context, references, boundaries, contracts, constraints, intended outcome, recommended
approach and cautions. Leave bounded discovery, command selection, implementation and ordinary
troubleshooting to the worker that owns them.

### G · Context routing is explicit — CHOSEN

After deployment-state intake, Main maintains a small working context map:

- **Direct** — decision-critical contracts/evidence Main must inspect itself;
- **Companion** — bulky/supporting project context that should return as one bounded synthesis;
- **Investigator** — a bounded unfamiliar project/Internet evidence gap.

This map is working state, not a new durable document. Revise it only when evidence changes relevance.
Do not directly explore a Companion/Investigator surface unless it becomes decision-critical.

Companion is persistent and project-centered. Investigator is disposable and evidence-gap-centered.
Do not make Companion an LLM message bus: workers report to Main, not to Companion.

### H · Batch coordination; do not wake Main for noise — CHOSEN

Borrow the donor batching discipline closely:

- dispatch independent workers that inform the same decision together;
- wait for the relevant set and synthesize once;
- start another batch only if prior evidence materially changes the next question;
- launch non-overlapping mutable packages concurrently when dependencies allow;
- keep dependencies, overlapping writes, uncertainty and risky changes sequential;
- do not poll workers or request status-only updates;
- do not rerequest evidence already returned;
- batch Main's own independent read/search/metadata operations too.

Optimize for **fewer Main decision turns and lower Main-context replay**, not minimum aggregate worker
tokens. Cheap worker tokens are allowed to buy expensive Main-context savings.

### I · Remove the arbitrary two-helper ceiling, but keep a conservative platform safety ceiling — CHOSEN

SKY-022's `max_concurrent_threads_per_session = 2` is too restrictive for the new topology.

Set a **Skynet platform ceiling of 6** initially. Six is a guardrail, not a target. Doctrine should not
encourage filling every slot. Typical Heavy deployments should use only the workers justified by real
independent packages.

Concurrency rules matter more than count:

- exactly one persistent Companion;
- at most one Senior Executor;
- mutable workers need non-overlapping ownership;
- workers never spawn workers;
- production credentials/authority are never gained merely because construction fan-out increased.

A later evidence-backed directive may raise/lower the ceiling. Do not create dynamic auto-scaling
logic for it.

### J · Executor owns routine repair; Tester owns independent verification — CHOSEN

Borrow the donor repair loop:

```text
Executor implements + self-checks
        ↓
Tester independently verifies
        ↓
ordinary defect?
   yes ─────► same owning Executor repairs
                  ↓
             same Tester rechecks
                  ↓
                 PASS
```

Main should not enter an operational debugging loop for ordinary package defects. Escalate to Main
only when evidence changes a material decision: package contract, ownership, scope, architecture,
security/migration risk, required authority, external blocker, or repeated focused failure.

After one evidence-free worker response, send one focused retry. After a second, replace the worker or
report the limitation; Main does not automatically take over production/verification work.

### K · Keep Skynet's production trust model completely separate — CHOSEN

Construction roles grant **zero production authority** by themselves.

Workers receive no production credentials, T2 root grant, T3 access, or implicit permission to touch
live infrastructure. Any live action still follows `docs/system-design.md`, AGENTS trust tiers,
capability-specific gates and human checkpoints. Authored PRs remain human-merged.

The new orchestration system coordinates construction. It does not become a second production-control
plane.

### L · Keep fresh independent review outside the implementation swarm — CHOSEN

An Executor's Tester validates its package, and Main integrates/accepts the deployment internally. That
is **not** the final independent review.

The final/phase acceptance review runs in a **fresh session outside the implementation swarm**. The
reviewer must not repair the implementation itself. If defects exist, it emits one paste-ready fix
prompt addressed to the original implementation session. The original session fixes; a fresh review
session reviews again. Repeat until ACCEPT.

This replaces SKY-025's reviewer-repairs-directly behavior for SKY-026.

## 3. Scope / non-goals

### In scope

- rewrite `docs/conventions/construction.md` around the new topology;
- reduce/adjust `AGENTS.md` so the always-loaded contract exposes only the load-bearing route and
  safety rules, with detail loaded from the construction spoke;
- replace old Codex worker definitions with Companion, Investigator, Default Executor, Senior
  Executor, Tester and Archivist;
- adapt `.codex/config.toml` and relevant invariant tests;
- adapt `bin/agent` only as a thin standalone/debug mirror where it still earns its existence;
- add/adjust deterministic tests for role names, models/efforts, sandboxes, concurrency and forbidden
  nesting/authority;
- implement route selection, capsules, context routing, batching and repair doctrine;
- map Companion/Archivist continuity onto Skynet's existing directive/journal/digest/context system;
- borrow a small deterministic deployment token-report facility if current Codex usage data makes it
  reliable and testable;
- dogfood the architecture on real SKY-026 work;
- remove superseded SKY-022 active guidance and stale role references from current docs/scripts/tests.

### Explicitly out

- installing the donor's whole lifecycle manager into Skynet;
- adding `agent_docs/` as a second project-memory tree;
- an LLM worker-manager/wave-barrier layer;
- scheduler, queue, DAG engine, workflow DB, retries/leases/heartbeats service;
- custom inter-agent protocol when native Codex agents suffice;
- automatic model router beyond explicit route/role defaults;
- automatic merging of authored work;
- widening any production trust tier or credential surface;
- rewriting archived SKY-022 history;
- changing SKY-025's engine-rebuild scope except where it must consume the new construction contract.

## 4. Plan

### Phase 1 · Transplant the orchestration contract  `[ ]` not started
**Recommended Main:** Sol High

Goal: make the donor architecture the single current construction model in doctrine before wiring all
roles.

Steps:
1. Re-read the donor source contracts at the pinned snapshot and current upstream `main`. Record only
   material differences that change implementation; do not create a permanent upstream changelog.
2. Rewrite `docs/conventions/construction.md` instead of layering patches onto SKY-022 wording. Import
   the donor's Light/Medium/Heavy routes, Main execution boundary, context routing, batching,
   role-specific capsules, lifecycle/repair rules and no-manager-agent rule.
3. Preserve only Skynet-specific deltas: trust tiers, human merge, existing memory/source-of-truth
   system, directive mechanics, final fresh review, platform ceiling 6.
4. Tighten `AGENTS.md` to the minimum always-loaded orchestration contract and link to the spoke for
   details. Remove obsolete Scout/Mechanic/Builder language from current doctrine rather than adding
   "do not use old roles" patches everywhere.
5. State explicitly that SKY-026 supersedes SKY-022 where current construction doctrine conflicts;
   archived SKY-022 stays untouched.
6. Add deterministic assertions for the invariants that can be machine checked; do not pretend
   qualitative orchestration choices are mechanically provable.

Exit criteria:
- one canonical construction doctrine describes the new topology and route model;
- Main/worker ownership and repair boundaries are unambiguous;
- the current contract contains no active duplicate SKY-022 role model;
- Skynet trust/merge/memory boundaries remain unchanged;
- docs contain current rules, not migration narrative.

Close-out: PR + journal episode + directive progress bump + `bin/plan list`.

### Phase 2 · Replace worker roles and platform configuration  `[ ]` not started
**Recommended Main:** Sol High; use the first available new read-only workers as soon as safe

Goal: make native Codex configuration match the new doctrine.

Steps:
1. Add Skynet-native worker TOMLs closely derived from donor source:
   - `companion`
   - `investigator`
   - `default_executor`
   - `senior_executor`
   - `tester`
   - `archivist`
2. Preserve donor role perspective: worker instructions speak to what that worker knows and owns, not
   from the workflow designer's omniscient perspective.
3. Adapt project-specific source domains:
   - Companion reads Skynet repo/directives/journal/generated context rather than `agent_docs/`;
   - Archivist writes only explicitly assigned canonical docs/journal surfaces and never hand-edits
     generated artifacts;
   - all roles preserve Skynet production-isolation rules.
4. Remove `builder.toml`, `mechanic.toml`, `scout.toml` and current references once caller search proves
   replacement is complete. Keep no compatibility aliases without a demonstrated caller.
5. Set `agents.max_concurrent_threads_per_session = 6` and enforce it consistently with invariants/tests.
6. Adapt `bin/agent` and its tests to the new role names if the launcher remains useful. Keep it thin;
   native subagents are the primary path.
7. Verify model IDs/efforts/sandboxes using installed harness metadata or safe dry runs; source comments
   are not proof of runtime availability.

Exit criteria:
- all six worker roles resolve with intended models/efforts/sandboxes;
- exactly one current role vocabulary exists;
- read-only roles cannot write;
- write roles gain no production authority;
- one-level orchestration and the six-thread platform ceiling are enforced as far as Codex exposes
  deterministic controls;
- launcher/tests/invariants agree with the actual config.

Close-out: PR + journal episode + directive progress bump + `bin/plan list`.

### Phase 3 · Wire Heavy orchestration, capsules, batching and repair  `[ ]` not started
**Recommended Main:** Sol High, running the new Heavy route

Goal: prove that the new system changes behavior, not merely filenames.

Steps:
1. Use one real substantial repository task from this phase as a Heavy deployment.
2. On deployment entry, create exactly one persistent Companion with no unnecessary inherited turn
   history; give it a bounded Skynet context intake and reuse it.
3. Build the Direct / Companion / Investigator working context map before broad exploration.
4. Dispatch at least two independent context/research lanes in one batch when the work naturally
   supports it; synthesize once after both return. Do not manufacture parallelism merely to satisfy
   the test.
5. Delegate at least one bounded implementation package to Default Executor using the exact capsule
   structure. The Main should not duplicate the implementation.
6. If a genuinely hard package appears, exercise Senior Executor; otherwise explicitly record that it
   was not justified. Do not invent a hard problem for dogfood.
7. Assign an independent Tester after implementation. Require the Tester to choose verification from
   acceptance intent and risks rather than echoing implementation details.
8. Exercise the repair loop on a real defect if one occurs. If nothing fails naturally, use a bounded
   test fixture or deliberately reversible synthetic package to prove Executor → Tester → Executor →
   Tester mechanics without corrupting production source.
9. Demonstrate delta-only worker follow-up and no polling/status chatter.
10. Verify Main's own tool use is batched where inputs were known together.

Exit criteria:
- Heavy route produces a complete real change while Main remains primarily decision/integration owner;
- capsules transfer enough project knowledge that workers do not need repeated broad rediscovery;
- independent verification is real;
- routine repair returns to the owning Executor and same Tester;
- no worker spawns another worker;
- Main is not repeatedly awakened for status-only coordination;
- resulting code quality/gates are at least as strong as the pre-SKY-026 path.

Close-out: PR + journal episode + directive progress bump + `bin/plan list`.

### Phase 4 · Adapt continuity, Archivist and token accounting  `[ ]` not started
**Recommended Main:** Sol High with Companion + Archivist; Default Executor for deterministic tooling

Goal: borrow the donor's closure/context economy without creating duplicate durable truth.

Steps:
1. Define Skynet's deployment-state intake from existing canonical sources. The Main reads only the
   minimum required high-level set once; Companion owns bulky/reusable intake and later delta/conflict
   checks.
2. Map donor closure semantics onto Skynet:
   - Main owns acceptance and active directive phase state;
   - Archivist receives verified facts only;
   - Archivist may update assigned current docs/runbooks and append the raw journal episode;
   - generated digest/context outputs are regenerated by their owning tools, never hand-edited;
   - optional `.agent/CHECKPOINT.md` remains disposable, not a second tracker.
3. Port/adapt the donor deployment-token-report concept if current Codex records expose sufficiently
   reliable usage data. Prefer borrowing the donor's parser/skill/test patterns over inventing a new
   accountant.
4. The report should identify deployment ID and per-agent usage using recorded values only. Do not
   estimate price or fabricate missing usage. If reliable data is unavailable, return a bounded
   limitation rather than creating a brittle pseudo-metric.
5. Make deployment IDs unique, lowercase and machine-safe for substantive Medium/Heavy work if the
   platform can carry them cleanly. Keep them runtime/accounting identifiers, not a new durable task
   database.
6. Test closure after completed, paused and blocked deployments so the next session has one clear
   entry point and no contradictory current-state documents.

Exit criteria:
- cold continuation works from Skynet's existing truth surfaces plus bounded Companion intake;
- no `agent_docs/` clone or parallel progress database exists;
- Archivist cannot decide acceptance or rewrite generated truth by hand;
- closure documentation is concise and current;
- token reporting is deterministic and honest if implemented, or explicitly omitted with evidence if
  the platform cannot support it reliably.

Close-out: PR + journal episode + directive progress bump + `bin/plan list`.

### Phase 5 · Dogfood, prune the old engine, and validate the whole system  `[ ]` not started
**Recommended Main:** Sol High, Heavy route

Goal: finish with one coherent orchestration engine and evidence that it works on Skynet-scale tasks.

Steps:
1. Dogfood at least three representative tasks without Ali instructing individual worker spawns:
   - one Light leaf task that correctly stays single-agent;
   - one Medium task where context/research support helps but Main owns implementation;
   - one Heavy task with multiple specialist workers and independent verification.
   The active directive may select the route; Ali should not need to micromanage worker topology.
2. For Heavy, demonstrate real batching, non-overlapping mutable ownership and at least two useful
   workers active during one deployment without turning six slots into a quota.
3. Demonstrate that a Senior Executor is used only when justified, or that Main correctly declines to
   spawn it.
4. Search the complete current repo for obsolete active references to Scout/Mechanic/Builder,
   max-two-helper doctrine, lead-owned Heavy verification, or other SKY-022 behavior. Remove or rewrite
   current guidance; leave archived history/journal evidence intact.
5. Verify `AGENTS.md`, construction doctrine, `.codex/*`, `bin/agent`, tests and invariants tell the
   same story.
6. Run the complete relevant repo gate suite plus full repo tests. Fix implementation defects in the
   owning session before requesting final independent review.
7. Produce a concise before/after evidence note in the journal: Main rollouts/wakeups when measurable,
   worker use, coordination failures/retries, and whether the six-thread ceiling was actually useful.
   Do not promote a tiny benchmark into a universal performance claim.
8. Mark SKY-026 ready for final independent review, but **do not mark done until the fresh review
   returns ACCEPT**.

Exit criteria:
- Light/Medium/Heavy all work as documented;
- Companion/Investigator/Executor/Senior/Tester/Archivist roles are live and internally consistent;
- no obsolete active SKY-022 role system remains;
- Main's Heavy execution boundary is respected;
- routine Tester failures round-trip through the owning Executor;
- current docs are lean and contain no migration story except the directive/journal;
- all deterministic gates pass;
- final review can reconstruct and challenge the whole change from merged/current repo evidence.

Close-out before review: implementation PR(s), journal episode, directive status remains `in-progress`
until external ACCEPT.

## 5. Operating model after SKY-026

### Light

```text
Ali → Main → done
```

### Medium

```text
Ali / directive
      ↓
     Main ───── Companion
      │   └─── Investigator(s)
      │
      └── Main implements + verifies
                    ↓
                Archivist
```

### Heavy

```text
Ali / directive
      ↓
     Main
      │
      ├── Companion
      ├── Investigator(s)
      ├── Default Executor(s)
      ├── Senior Executor (0..1)
      ├── Tester(s)
      └── Archivist
      │
      ▼
 Main integrates + accepts
      ↓
 authored PR
      ↓
 Ali merge / normal gate
      ↓
 fresh independent review
```

The guiding optimization is:

> **Spend Main context on decisions that need the whole picture. Spend worker context on bounded work.**

## 6. Review and repair protocol

This section is mandatory for SKY-026 acceptance and intentionally differs from SKY-025's
reviewer-can-repair workflow.

### Reviewer rules

The acceptance reviewer runs in a **fresh session** and does not modify the implementation.

Review against:

- this complete directive and all exit criteria;
- current `main` plus the implementation/fix PRs or merged SHAs;
- donor source contracts, using the pinned snapshot as baseline and current upstream only where useful;
- `AGENTS.md`, `docs/conventions/construction.md`, `.codex/*`, launcher/tests/invariants and all callers;
- full relevant deterministic gates and dogfood evidence;
- Skynet trust/memory/merge boundaries.

The reviewer may use read-only workers for evidence gathering, but it must own the verdict. It must not
turn a review defect into its own implementation branch.

### If review PASSES

Return a concise `ACCEPT SKY-026` verdict with the reviewed SHA/PR references and the critical gates
that passed. The original implementation session may then perform the final directive close-out if
that bookkeeping was intentionally held until acceptance.

### If review finds ANY fixable defect

**The reviewer's final response must contain only one fenced text block containing a paste-ready fix
prompt. No preamble, no explanation outside the block, no separate findings list.**

The prompt must be addressed to the **original SKY-026 implementation session** and contain everything
that session needs to act without seeing the review transcript:

```text
Continue the original SKY-026 implementation session and fix the independent review findings below.
Do not redesign unrelated work and do not self-accept SKY-026.

Review findings:
- <specific defect + evidence/reference>
- <specific defect + evidence/reference>

Required fixes:
- <bounded required outcome>
- <bounded required outcome>

Verification required:
- <specific affected tests/gates>
- run the relevant full repo gates after focused checks pass

Git/PR handling:
- if the reviewed implementation PR is still open, update that same branch/PR;
- if the reviewed work is already merged, create one bounded SKY-026 fix branch/PR from current main;
- do not merge your own PR.

When fixed, report the PR URL/commit, changed files, checks run/results, and any remaining limitation.
Then stop. The result will be reviewed again in a fresh independent review session.
```

Populate that template with real findings; do not emit placeholders.

### Re-review loop

```text
original implementation session fixes
             ↓
       PR / merged fix
             ↓
     FRESH review session
             ↓
        ACCEPT or one new
        paste-ready fix prompt
```

Repeat until ACCEPT. Do not ask the reviewer to repair its own findings. Do not require Ali to
translate review prose into instructions for the implementation session.

## 7. ▶ Execute prompt

Paste into a fresh session, replacing `<N>`:

```text
Read planning/projects/SKY-026-overhaul-agent-orchestration-around-a-main-worker-swarm.md and execute
Phase <N> only.

Borrow aggressively from viettran-edgeAI/codex_workflow using its source contracts as the donor, while
preserving the explicit Skynet deltas in SKY-026: existing truth/memory surfaces instead of agent_docs,
Skynet trust tiers, human merge, six-thread platform ceiling, and fresh external review.

Follow AGENTS.md and the directive. Keep current docs lean; history belongs in journal. Land one
reviewable PR, never merge your own authored work, and perform the phase close-out when the exit
criteria pass.
```

After Phase 2 has landed, later phases should use/dogfood the new route and worker contracts rather
than the old SKY-022 helper model.

## 8. ▶ Final review prompt

Paste into a **fresh** session after Phase 5 implementation evidence is ready:

```text
Independently review SKY-026 end to end.

Read planning/projects/SKY-026-overhaul-agent-orchestration-around-a-main-worker-swarm.md, current
AGENTS.md, docs/conventions/construction.md, .codex configuration/agents, launcher/tests/invariants,
all SKY-026 implementation/fix PRs or merged SHAs, and the relevant donor source contracts from
viettran-edgeAI/codex_workflow.

Do not modify the implementation and do not repair findings yourself. Verify the directive exit
criteria, role ownership, Light/Medium/Heavy behavior, context routing, task capsules, batching,
Executor↔Tester repair loop, closure/continuity, obsolete-role removal, model/sandbox configuration,
production isolation, human-merge boundary, and deterministic gates.

If everything passes, return a concise ACCEPT SKY-026 verdict with reviewed refs and critical evidence.
If any fixable defect exists, your FINAL RESPONSE MUST BE ONLY ONE fenced text block containing a
complete paste-ready fix prompt for the original SKY-026 implementation session. Include the exact
findings, required fixes, verification, and PR handling. No prose outside that block. The original
session will fix it, then a fresh independent session will review again.
```

## 9. Phase close-out

For Phases 1–4:

- land one reviewable PR; never self-merge;
- append the raw session evidence to `journal/`;
- bump `current_phase`, flip the completed phase `[x]`, set `updated`, and keep status `in-progress`;
- run `bin/plan list`;
- provide the next phase's Execute prompt.

For Phase 5:

- land implementation evidence and keep SKY-026 `in-progress` pending independent review;
- after external `ACCEPT SKY-026`, perform one bounded close-out update:
  - mark Phase 5 `[x]`;
  - set `current_phase: 5`, `status: done`, `updated`;
  - refresh roadmap with `bin/plan list`;
  - archive the directive using the normal planning lifecycle;
  - retain SKY-022 as historical evidence, not active doctrine.

## 10. Status log

- 2026-09-10 — SKY-026 minted. Design donor pinned to
  `viettran-edgeAI/codex_workflow@6d9b06f73bee7f899001b0bb102c70529a24313f`; intent is to borrow
  the orchestration architecture aggressively while preserving Skynet's existing source-of-truth,
  trust and merge boundaries. SKY-022 is superseded where current doctrine conflicts.
- 2026-09-10 — Review policy set: independent reviewer never repairs SKY-026 itself. A failed review
  emits only one paste-ready fix prompt for the original implementation session; fixes are then
  reviewed again in a fresh session until ACCEPT.
