---
id: SKY-026
title: "Overhaul agent orchestration around a Main-directed worker swarm"
status: in-progress
horizon: long
created: 2026-09-10
updated: 2026-09-10
phases: 5
current_phase: 3
tier_touched: [T1]
related:
  - AGENTS.md
  - docs/conventions/construction.md
  - .codex/config.toml
  - .codex/agents/
  - agent_docs/
  - planning/archive/SKY-022-lean-multi-agent-construction-orchestration-lead-driven-delegation.md
  - planning/projects/SKY-025-rebuild-the-skynet-engine-in-python.md
  - "[[SKY-026-progress]]"
---

# SKY-026 · Overhaul agent orchestration around a Main-directed worker swarm

> Completely supersede SKY-022 with a Skynet-native adaptation of `viettran-edgeAI/codex_workflow`:
> Main spends context on decisions, specialist workers own bounded work, coordination is batched,
> verification is independent, `agent_docs/` provides compact cross-session agent memory, and failed
> reviews return one paste-ready fix prompt to the original implementation session.

## 1. Goal and donor

Skynet should use a real orchestration topology built around **Main-agent context economy** rather than
"a lead that sometimes delegates".

Design donor:

- `https://github.com/viettran-edgeAI/codex_workflow`
- snapshot reviewed at mint: `6d9b06f73bee7f899001b0bb102c70529a24313f`
- packaged architecture described there as `1.1.17`

Implementation must re-read relevant donor source contracts before changing Skynet and borrow the
current upstream implementation aggressively where it still fits. Prefer source contracts over README
prose when they disagree. Important donor surfaces:

- `codex_workflow/AGENTS.md`
- `codex_workflow/heavy_route.md`
- `codex_workflow/medium_route.md`
- `codex_workflow/agents/*.toml`
- `codex_workflow/archivist.md`
- `codex_workflow/project_docs/*`
- deployment-token-report skill/parser/tests
- lifecycle/runtime code only where a deterministic primitive is useful to Skynet itself

### SKY-022 supersession

**SKY-026 completely supersedes SKY-022.** Once SKY-026 is accepted:

- SKY-022 has zero current construction authority;
- no current agent, doctrine, launcher, test, invariant, runbook, prompt, caller, alias, fallback, or
  compatibility path may depend on SKY-022 behavior;
- Scout / Mechanic / Builder are not current roles;
- current construction documentation points only to SKY-026 contracts;
- archived SKY-022 directive/journal material remains only as inert historical provenance and never
  decides current behavior.

Do not rewrite historical records merely to erase provenance.

### Target topology

```text
                                  Ali
                                   │
                                   ▼
                             ┌──────────┐
                             │   MAIN   │
                             │ decisions│
                             └────┬─────┘
                                  │
                  ┌───────────────┼──────────────────┐
                  │               │                  │
                  ▼               ▼                  ▼
             Companion       Investigator       Executor(s)
             Luna xhigh      Luna xhigh         Luna max
             persistent      disposable             │
                                                    │ hard package
                                                    ▼
                                             Senior Executor
                                              Sol medium 0..1
                                                    │
                                                    ▼
                                                 Tester
                                              Luna xhigh
                                                    │ defect
                                                    ▼
                                               same Executor
                                                    │
                                                    └──► same Tester

                         verified deployment / closure
                                   │
                                   ▼
                               Archivist
                               Luna xhigh
                                   │
                                   ▼
                           compact agent_docs
```

Main coordinates workers directly. Workers never orchestrate children. Do not add an LLM wave
manager, scheduler, queue, DAG engine, workflow database, heartbeat/lease service, or custom agent
transport unless native Codex genuinely cannot express a required behavior and Ali separately
authorizes that complexity.

## 2. Decisions

### A · Borrow the donor architecture and port `agent_docs/` natively — CHOSEN

Copy the donor orchestration and continuity semantics closely, but do not install `codex_workflow` as
a parallel control plane.

Port its six-document project-memory model into native Skynet as `agent_docs/`:

| File | Purpose | Higher-authority source |
|---|---|---|
| `project_overview.md` | compact project purpose, architecture, major workflows and decisions | `docs/system-design.md` + current design docs |
| `project_core_tech.md` | current technology stack and technical conventions needed for work | current repo/config/docs |
| `project_structure.md` | important directories, ownership and entry points | current repository |
| `project_progress.md` | current goals, directive position and next milestone | active `planning/projects/` directives |
| `project_diary.md` | distilled decisions, discarded approaches, mistakes and reusable lessons | accepted decisions + append-only journal |
| `latest_session_work.md` | latest substantive closure state, verification, blockers and next entry point | accepted deployment evidence + directive state |

`agent_docs/` is **canonical agent memory**, not higher-authority infrastructure truth. It exists to let
a cold Main recover project context cheaply. It may summarize authoritative facts, but it does not
replace their owners.

Authority rule:

```text
constitution / runtime / current docs / active directive / accepted evidence
                         │
                         │ distill
                         ▼
                    agent_docs/
```

If an `agent_docs/` claim conflicts with its higher-authority source, the higher-authority source wins
and `agent_docs/` is stale until repaired. This is intentional summarized duplication, not a second
independent truth system.

### B · Main is a decision owner, not an extra Heavy worker — CHOSEN

Heavy Main owns task understanding, architecture, cross-package contracts, material causal decisions,
decomposition, worker ownership, integration, risk/authority decisions, acceptance, and user
communication.

Heavy Main does not routinely write production code/tests, perform Executor work, execute Tester
verification, run ordinary deployment operations, chase routine logs, or take over a package after a
first worker failure. It may inspect the smallest evidence needed for a decision.

### C · Light / Medium / Heavy routes — CHOSEN

| Route | Production / verification owner | Support | Intended use |
|---|---|---|---|
| **Light** | Main | none | Q&A and small leaf work |
| **Medium** | Main | Companion, Investigator, Archivist | substantive work where Main still implements/verifies |
| **Heavy** | Executors + Testers | full topology | large/cross-cutting work decomposable into bounded packages |

Light is default when neither the user nor active directive selects another route. A directive may
select Medium/Heavy so Ali does not micromanage worker spawning. Keep that route for the substantive
deployment unless explicitly changed.

### D · Donor roles and defaults — CHOSEN

| Role | Model | Effort | Declared sandbox | Quantity |
|---|---|---|---|---:|
| Main | session-selected | task-selected | invoking session | 1 |
| Companion | `gpt-5.6-luna` | xhigh | read-only | exactly 1 persistent per deployment |
| Investigator | `gpt-5.6-luna` | xhigh | read-only | as needed |
| Default Executor | `gpt-5.6-luna` | max | workspace-write | as needed |
| Senior Executor | `gpt-5.6-sol` | medium | workspace-write | max 1 |
| Tester | `gpt-5.6-luna` | xhigh | workspace-write | as needed |
| Archivist | `gpt-5.6-luna` | xhigh | workspace-write | one at substantive closure, plus explicit doc assignments |

Source TOML wins if prose disagrees. Verify exact identifiers/efforts against the installed harness;
do not silently substitute.

### E · Delete SKY-022 role surface, no compatibility — CHOSEN

Current callers must use SKY-026 roles or be removed. Do not retain Scout/Mechanic/Builder aliases,
shims, launch routes, tests, prompts, or fallback semantics merely for compatibility.

### F · Knowledge capsules are the worker API — CHOSEN

Every initial assignment begins with a deployment-unique Task ID. Follow-ups repeat Task ID and send
only changed capsule parts.

| Role | Initial capsule |
|---|---|
| Companion | `Project Context Scope` · `Context Task + Goal` · `Main-Agent Context Guidance` |
| Investigator | `Investigation Context` · `Evidence Question + Goal` · `Main-Agent Investigation Guidance` |
| Default/Senior Executor | `Implementation Context + Ownership` · `Implementation Task + Goal` · `Main-Agent Implementation Guidance` |
| Tester | `Verification Context` · `Verification Goal` · `Main-Agent Verification Guidance` |
| Archivist | `Documentation Context + Audience` · `Documentation Task + Goal` · `Main-Agent Documentation Guidance` |

Capsules transfer Main's relevant knowledge, rationale, contracts, constraints, boundaries, outcome and
cautions. Leave bounded discovery, command selection, implementation and ordinary troubleshooting to
the owning worker.

### G · Explicit context routing — CHOSEN

At substantive Medium/Heavy entry, Main first reads the compact `agent_docs/` memory set once plus the
active directive. It then builds a working context map:

- **Direct**: decision-critical authoritative contracts/evidence Main must inspect itself;
- **Companion**: supporting or bulky canonical project context returned as one bounded synthesis;
- **Investigator**: a bounded unfamiliar project or Internet evidence gap.

The map is working state, not durable documentation. `agent_docs/` supplies orientation, not evidence
that overrides current authoritative sources.

Companion is persistent and project-centered. Investigator is disposable and evidence-gap-centered.
Workers report to Main, not to Companion.

### H · Batch coordination and suppress Main wakeup noise — CHOSEN

- dispatch independent workers informing the same decision together;
- wait for the relevant set and synthesize once;
- open another batch only when earlier evidence changes the next question;
- run non-overlapping mutable packages concurrently when dependencies allow;
- keep dependencies, overlapping writes, uncertainty and risky work sequential;
- do not poll workers or request status-only updates;
- do not rerequest evidence already returned;
- batch Main's own known-input reads/searches/checks.

Optimize for fewer Main decision turns and less Main-context replay while preserving quality. Aggregate
worker token minimization is not the goal.

### I · No workflow-owned aggregate concurrency cap — CHOSEN

Use platform capacity and task judgment, not a Skynet worker quota. Standing semantic limits remain:
exactly one persistent Companion, at most one Senior Executor, non-overlapping concurrent mutable
ownership, no worker-spawns-worker, sequential dependencies/risk, and no production-authority growth.

### J · Executor owns repair; Tester owns independent verification — CHOSEN

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

Main intervenes only when evidence changes a material decision: contract, ownership, scope,
architecture, authority, security/migration risk, external blocker, or repeated focused failure. One
evidence-free worker response gets one focused retry; a second gets replacement or a reported limit.

### K · Construction authority remains separate from production authority — CHOSEN

Worker role or filesystem sandbox grants zero production authority. No production credential, root
grant, T2/T3 permission or implicit live-infrastructure authority reaches a worker merely because it
can edit a workspace. Human merge remains required for authored work.

### L · Fresh review stays outside the implementation swarm — CHOSEN

Executor self-check + Tester verification + Main acceptance are internal gates. Final acceptance
review runs in a fresh session outside the implementation swarm. Reviewer never repairs SKY-026. Any
fixable defect produces only one complete paste-ready fix prompt for the original implementation
session; then a fresh session reviews again until ACCEPT.

### M · `agent_docs/` ownership and closure split — CHOSEN

Borrow the donor's split directly:

**Main owns deployment-state memory:**

- `agent_docs/project_progress.md`
- `agent_docs/project_diary.md`
- `agent_docs/latest_session_work.md`

Main updates those only from accepted/verified facts. `project_diary.md` contains distinct decisions,
discarded approaches, mistakes and reusable lessons, not chronology, commits, routine maintenance or
raw logs.

**Archivist owns assigned stable project memory:**

- `agent_docs/project_overview.md`
- `agent_docs/project_core_tech.md`
- `agent_docs/project_structure.md`
- explicitly assigned current docs/runbooks

Archivist receives verified facts only, stays inside assigned write surfaces, never decides
acceptance, and never hand-edits generated outputs.

Closure order for substantive Medium/Heavy work:

```text
workers complete evidence
        ↓
Main accepts or marks paused/blocked
        ↓
Main updates progress + diary + latest_session_work
        ↓
Archivist updates affected stable memory/docs
        ↓
owned generators refresh any retained generated context
        ↓
PR / human merge
        ↓
next fresh Main reads agent_docs + active directive
```

## 3. Scope and non-goals

### In scope

- donor-derived Light/Medium/Heavy orchestration;
- six native worker roles and task capsules;
- context routing, batching, repair ownership and independent verification;
- native Skynet `agent_docs/` continuity framework;
- Main/Archivist ownership rules for the six memory documents;
- compact cold-start intake from `agent_docs/` plus active directive;
- deterministic freshness/shape checks only where they prevent real drift;
- evaluation and pruning of redundant digest/context/checkpoint continuity surfaces after dogfood;
- deterministic token reporting if current Codex exposes reliable recorded usage;
- complete removal of current SKY-022 construction authority and compatibility;
- production trust tiers and human merge unchanged.

### Explicitly out

- installing a parallel `codex_workflow` control plane;
- treating `agent_docs/` as authority over constitution/runtime/active directives/current operational docs;
- a second task database or workflow state service;
- automatic semantic regeneration of `agent_docs/` by an LLM daemon;
- wave managers, schedulers, queues, DAG engines, leases/heartbeats or custom worker transport;
- automatic merge;
- wider production credentials/trust;
- SKY-022 aliases/fallbacks;
- rewriting historical archive/journal material;
- unrelated SKY-025 engine changes.

## 4. Plan

### Phase 1 · Transplant orchestration contract  `[x]` done

Accepted foundation: current construction doctrine uses donor route semantics, Main/worker ownership,
context routing, batching, capsules, repair lifecycle and fresh external review. Always-loaded agent
instructions were reduced and SKY-022 current-language migration began.

### Phase 2 · Replace worker roles and Codex configuration  `[x]` done

Accepted foundation: six native roles exist; legacy Scout/Mechanic/Builder roles and false standalone
launcher semantics are gone; no workflow-owned thread cap remains; model/effort resolution was tested;
construction session filesystem reach is bounded by project `workspace-write`, while production
authority remains zero.

### Phase 3 · Wire Heavy orchestration, capsules, batching and repair  `[x]` done

Accepted foundation: a real Heavy deployment proved one persistent Companion, batched context intake,
Executor ownership, independent Tester verification, same-Executor repair, same-Tester recheck,
delta-only follow-up and no child orchestration. The accepted follow-up also removed operator prompt
churn from ordinary repo/TMP-only mutation verification without weakening root/merge checkpoints.

### Phase 4 · Port `agent_docs`, Archivist closure and token accounting  `[ ]` not started
**Recommended Main:** Astra Medium with Companion + Archivist; use Heavy only for implementation packages that genuinely decompose.

Goal: make cold-session continuity cheap and explicit by porting the donor's six-document memory model
without creating a competing authority tree.

Steps:
1. Re-read donor `project_docs/*`, Archivist contract, Medium/Heavy intake and closure behavior. Borrow
   structure and ownership directly unless a Skynet-specific constraint requires a delta.
2. Create native `agent_docs/` with exactly the six core documents:
   - `project_overview.md`
   - `project_core_tech.md`
   - `project_structure.md`
   - `project_progress.md`
   - `project_diary.md`
   - `latest_session_work.md`
3. Populate them only from verified current Skynet evidence. No bootstrap placeholder may survive
   closure. Each document must make clear that conflicts defer to its higher-authority source.
4. Keep memory compact enough for repeated cold intake. Summarize and link/reference authoritative
   owners rather than copying procedures, raw logs, inventories or long historical narratives.
5. Wire construction doctrine/roles so substantive Medium/Heavy Main reads the compact memory set once
   plus the active directive before broad exploration. Main then directly inspects only decision-critical
   authoritative evidence; Companion owns bulky reusable canonical context and later conflict/delta checks.
6. Implement the donor ownership split:
   - Main updates `project_progress.md`, `project_diary.md`, `latest_session_work.md` after acceptance or
     when recording a paused/blocked closure;
   - Archivist may update assigned `project_overview.md`, `project_core_tech.md`, `project_structure.md`
     and assigned current docs/runbooks from verified facts;
   - Archivist cannot decide acceptance or rewrite Main-owned deployment-state files during closure.
7. Preserve existing generated digest/context map and optional checkpoint initially. Treat them as
   compatibility candidates under evaluation, not permanent companions to `agent_docs/`. Do not delete
   them until a cold-start comparison proves their unique value is absent or covered elsewhere.
8. Add only narrow deterministic checks that earn their keep, such as required file set, no bootstrap
   markers, ownership contract and prohibition on generated-output hand edits. Do not build a semantic
   sync daemon or pseudo-database.
9. Port/adapt donor deployment-token-report only if current Codex exposes reliable recorded usage.
   Report recorded counts only; never estimate price or fabricate missing data. If unavailable, document
   the limitation and omit brittle accounting.
10. Use one real Phase-4 closure to dogfood the full sequence: Main acceptance/state-memory update →
    Archivist stable-memory/doc update → PR. Then open a **fresh cold session** and verify it can recover
    the current project position from `agent_docs/` + active directive with only bounded authoritative
    follow-up reads.
11. Compare cold-start quality, required reads and Main wakeups against the existing digest/context-map
    path. Record evidence, not a universal benchmark.
12. Test completed, paused and blocked closure shapes so each leaves exactly one clear next entry point.

Exit criteria:
- six populated `agent_docs/` files exist and have explicit authority boundaries;
- a fresh Main can recover Skynet orientation/current work cheaply from `agent_docs/` + active directive;
- authoritative sources win every conflict and no agent treats `agent_docs/` as runtime/config truth;
- Main/Archivist ownership matches the chosen split;
- diary contains reusable decisions/lessons rather than chronology;
- latest-session memory contains verification, blockers/pending work and one clear next entry point;
- no second task database, sync daemon or automatic LLM memory service exists;
- retained generated continuity artifacts have a documented unique role or are marked as P5 retirement candidates;
- token reporting is deterministic/honest if implemented, otherwise explicitly omitted with evidence;
- focused and full relevant repo gates pass.

Close-out: one reviewable PR + journal episode + directive progress bump + `bin/plan list`.

### Phase 5 · Dogfood end to end, prune continuity duplication, eradicate SKY-022  `[ ]` not started
**Recommended Main:** Astra Medium, Heavy route where task decomposition is real.

Goal: finish with one coherent construction engine, one compact agent-memory layer, no redundant
continuity machinery without a distinct purpose, and zero current SKY-022 authority.

Steps:
1. Dogfood representative Light, Medium and Heavy tasks without Ali instructing individual worker
   spawns. The active directive may select route; operator should not micromanage topology.
2. Demonstrate useful concurrent workers with non-overlapping ownership when real work allows; fan-out
   is not a quota. Use Senior Executor only when justified.
3. Start at least one Medium/Heavy deployment from a fresh session using `agent_docs/` + active directive
   as the normal continuity path. Verify that stale or conflicting memory causes repair against the
   higher-authority source rather than blind trust.
4. Decide the fate of existing continuity artifacts from evidence:
   - `docs/generated/06-agent-digest.md`
   - `docs/generated/07-context-map.md`
   - optional `.agent/CHECKPOINT.md`
   - repeated handoff prose elsewhere.
   Delete or narrow anything whose agent-continuity purpose is now redundant. Keep a surface only when
   it has a clear unique consumer or function beyond `agent_docs/`.
5. Ensure `agent_docs/` itself stays compact. Remove copied procedures, historical narration, raw logs,
   duplicated inventories and any fact that does not materially improve cold agent recovery.
6. Search all current repo surfaces for Scout/Mechanic/Builder, max-two-helper, lead-owned Heavy
   verification, active SKY-022 links, SKY-022-derived tests/prompts or any current dependency. Migrate
   or delete every one. Archive/journal references may remain only as inert history.
7. Verify AGENTS, construction doctrine, `.codex/*`, agent roles, tests/invariants, prompts/runbooks,
   `agent_docs/` and any retained generated context tell one SKY-026 story.
8. Exercise Executor → Tester → same Executor repair → same Tester recheck again on natural work when a
   defect occurs; do not manufacture churn merely to satisfy the phase.
9. Run focused and full relevant gates. Fix implementation defects before external review.
10. Record concise dogfood evidence: cold-start reads, Main wakeups/rollouts when measurable, worker use,
    coordination failures/retries, continuity conflicts and concurrency behavior. Do not generalize a
    tiny sample.
11. Keep SKY-026 `in-progress` until the fresh external reviewer returns ACCEPT.

Exit criteria:
- Light/Medium/Heavy behave as documented;
- all six specialist roles are internally consistent;
- `agent_docs/` is the normal compact cross-session agent-memory surface;
- every remaining continuity artifact has a distinct justified role, otherwise it is removed;
- no source treats `agent_docs/` as higher authority than constitution/runtime/current docs/active directives;
- SKY-022 has zero current construction authority, callers, aliases, fallbacks or compatibility surface;
- Heavy Main boundary and Executor/Tester repair ownership hold;
- current docs stay lean and history remains in archive/journal;
- deterministic gates pass;
- fresh reviewer can reconstruct and challenge the current system without consulting SKY-022 for present behavior.

Close-out before review: implementation PR(s), journal evidence, status remains `in-progress`.

## 5. Operating model after SKY-026

### Light

```text
Ali → Main → done
```

### Medium

```text
agent_docs + active directive
          ↓
         Main ───── Companion
          │   └─── Investigator(s)
          │
          └── Main implements + verifies
                        ↓
                    Archivist
                        ↓
                    closure memory
```

### Heavy

```text
agent_docs + active directive
          ↓
         Main
          ├── Companion
          ├── Investigator(s)
          ├── Default Executor(s)
          ├── Senior Executor (0..1)
          ├── Tester(s)
          └── Archivist
          ↓
 Main integrates + accepts
          ↓
 Main state-memory update
          ↓
 Archivist stable-memory/docs update
          ↓
 authored PR
          ↓
 human merge
          ↓
 fresh independent review
```

Optimization target:

> **Spend Main context on decisions that need the whole picture. Spend worker context on bounded work.
> Spend durable context only on facts worth carrying into the next session.**

SKY-022 is archived historical provenance only.

## 6. Review and repair protocol

Acceptance review runs in a fresh session and does not modify implementation. Review:

- complete SKY-026 directive and exit criteria;
- current `main` plus implementation/fix PRs or merged SHAs;
- relevant donor source contracts;
- AGENTS, construction doctrine, `.codex/*`, roles, tests/invariants, prompts/runbooks and callers;
- `agent_docs/` content, ownership, authority boundaries and cold-start behavior;
- disposition of digest/context-map/checkpoint continuity surfaces;
- deterministic gates + dogfood evidence;
- trust/memory/merge boundaries;
- proof SKY-022 has no current construction authority or compatibility surface.

Reviewer may inspect SKY-022 only as history to verify old active surfaces were removed. It must never
use SKY-022 to fill a current behavior gap. Reviewer may use read-only workers for evidence but owns the
verdict.

### PASS

Return a concise `ACCEPT SKY-026` verdict with reviewed refs and critical evidence. Original
implementation session may then perform final close-out bookkeeping held for acceptance.

### FIX

If any fixable defect exists, the reviewer's final response must be only one fenced text block containing
a complete paste-ready prompt for the original SKY-026 implementation session. No prose outside it.

Use this populated structure:

```text
Continue the original SKY-026 implementation session and fix the independent review findings below.
Do not redesign unrelated work and do not self-accept SKY-026.

Review findings:
- <specific defect + evidence/reference>

Required fixes:
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

Then a fresh session reviews again. Repeat until ACCEPT. Reviewer never repairs its own findings.

## 7. ▶ Execute prompt

Paste into a fresh session, replacing `<N>`:

```text
Read planning/projects/SKY-026-overhaul-agent-orchestration-around-a-main-worker-swarm.md and execute
Phase <N> only.

SKY-026 completely supersedes SKY-022. Do not use SKY-022 as current guidance, a fallback contract, or
compatibility target. Its archive/journal material is historical provenance only.

Borrow aggressively from viettran-edgeAI/codex_workflow using source contracts as the donor. SKY-026
now intentionally ports donor agent_docs as native Skynet canonical agent memory. agent_docs is a
compact derived continuity layer: constitution/runtime/current operational docs/active directives and
accepted evidence remain higher authority and win any conflict.

Preserve Skynet production trust tiers, human merge and fresh external review. Follow AGENTS.md and
this directive. Keep current docs and agent memory lean; history belongs in journal. Land one reviewable
PR, never merge your own authored work, and perform phase close-out only when exits pass.
```

## 8. ▶ Final review prompt

Paste into a fresh session after Phase 5 implementation evidence is ready:

```text
Independently review SKY-026 end to end.

Read planning/projects/SKY-026-overhaul-agent-orchestration-around-a-main-worker-swarm.md, current
AGENTS.md, docs/conventions/construction.md, .codex configuration/agents, tests/invariants,
agent_docs/, current construction prompts/runbooks, all SKY-026 implementation/fix PRs or merged SHAs,
and relevant donor source contracts from viettran-edgeAI/codex_workflow.

SKY-026 must completely supersede SKY-022. Verify SKY-022 has zero current construction authority,
callers, aliases, fallbacks, compatibility behavior or present-tense authority references. Archived
material may remain only as inert history and must not determine current behavior.

Verify agent_docs is the compact cross-session agent-memory layer, with the donor-inspired six-file
shape and Main/Archivist ownership split, while constitution/runtime/current operational docs/active
directives/accepted evidence remain higher authority. Verify stale memory is repaired rather than
trusted, and that any retained digest/context-map/checkpoint surface has a distinct justified role.

Do not modify implementation and do not repair findings yourself. Verify all directive exits, role
ownership, Light/Medium/Heavy behavior, context routing, task capsules, batching, Executor↔Tester repair,
continuity/closure, obsolete-role removal, model/sandbox configuration, production isolation, human
merge and deterministic gates.

If everything passes, return a concise ACCEPT SKY-026 verdict with reviewed refs and critical evidence.
If any fixable defect exists, your FINAL RESPONSE MUST BE ONLY ONE fenced text block containing a
complete paste-ready fix prompt for the original SKY-026 implementation session. Include exact findings,
required fixes, verification and PR handling. No prose outside that block. The original session fixes;
then a fresh independent session reviews again.
```

## 9. Phase close-out

Phases 1–4:

- land one reviewable PR; never self-merge;
- append raw session evidence to `journal/`;
- bump current phase/checkbox while keeping `in-progress`;
- run `bin/plan list`;
- provide next Execute prompt.

Phase 5:

- land implementation evidence and keep `in-progress` pending independent review;
- after `ACCEPT SKY-026`, one bounded close-out marks Phase 5 done, sets `current_phase: 5`, marks the
  directive done, refreshes roadmap, and archives through normal planning lifecycle;
- SKY-022 remains only inert historical provenance.

## 10. Status

- P1 accepted: donor orchestration doctrine transplanted and SKY-022 current semantics began retirement.
- P2 accepted after fixes: six native roles, native spawning, project workspace-write construction leash,
  no legacy launcher semantics, no workflow-owned concurrency cap.
- P3 accepted: real Heavy route proved batched intake, persistent Companion, Executor ownership,
  independent Tester, owner repair and same-Tester recheck. Accepted follow-up removed permission churn
  for ordinary repo/TMP-only verification without weakening root/merge checkpoints.
- 2026-09-10 continuity decision changed before P4: port donor `agent_docs/` deliberately as **canonical
  agent memory derived from higher-authority Skynet truth**, then use P4/P5 dogfood to retire redundant
  continuity surfaces rather than maintaining parallel handoff systems forever.
