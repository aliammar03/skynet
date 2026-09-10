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
  - bin/agent
  - planning/archive/SKY-022-lean-multi-agent-construction-orchestration-lead-driven-delegation.md
  - planning/projects/SKY-025-rebuild-the-skynet-engine-in-python.md
  - "[[SKY-026-progress]]"
---

# SKY-026 · Overhaul agent orchestration around a Main-directed worker swarm

> Completely supersede SKY-022's lead + two-helper construction model with a Skynet-native adaptation
> of `viettran-edgeAI/codex_workflow`: Main spends context on decisions, specialist workers own bounded
> work, coordination is batched, verification is independent, and failed reviews return one paste-ready
> fix prompt to the original implementation session.

## 1. Goal and donor

Skynet should stop treating multi-agent work as "a lead that sometimes delegates" and adopt a real
orchestration topology designed around **Main-agent context economy**.

Design donor:

- `https://github.com/viettran-edgeAI/codex_workflow`
- snapshot reviewed at mint: `6d9b06f73bee7f899001b0bb102c70529a24313f`
- packaged architecture described there as `1.1.17`

Implementation must inspect the donor source contracts again before changing Skynet and borrow the
current upstream implementation **aggressively** where it still fits. Prefer source contracts over
README prose when they disagree. Primary donor surfaces:

- `codex_workflow/AGENTS.md`
- `codex_workflow/heavy_route.md`
- `codex_workflow/medium_route.md`
- `codex_workflow/agents/*.toml`
- `codex_workflow/archivist.md`
- deployment-token-report skill/parser/tests
- lifecycle/runtime code only where a deterministic primitive is useful to Skynet itself

### SKY-022 supersession rule

**SKY-026 completely supersedes SKY-022.** Once SKY-026 is accepted:

- SKY-022 has **zero current construction authority**;
- no current agent, doctrine, launcher, test, invariant, runbook, prompt, or workflow may use SKY-022
  as a fallback, compatibility contract, secondary source, or behavioral reference;
- no Scout / Mechanic / Builder compatibility aliases survive merely to preserve SKY-022 interfaces;
- any current caller that still depends on SKY-022 behavior must be migrated to SKY-026 or removed;
- current documentation must point only to the SKY-026 construction contract;
- the archived SKY-022 directive and its journal episodes remain untouched **only as inert historical
  provenance** and may be consulted only when explicitly investigating history, never to decide how
  current construction should operate.

Do not rewrite or delete historical records to make the transition look cleaner. Supersession means
**no present-tense authority**, not erasing provenance.

### Target topology

```text
                              Ali
                               │
                               ▼
                    ┌─────────────────────┐
                    │        MAIN         │
                    │ session-selected   │
                    │ architecture       │
                    │ decomposition      │
                    │ causal decisions   │
                    │ integration        │
                    │ acceptance         │
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

Main coordinates workers directly. Workers never orchestrate children. Do not add an LLM wave
manager, scheduler, queue, DAG engine, workflow database, heartbeat system, lease service, or custom
agent transport unless native Codex genuinely cannot express a required behavior and Ali separately
authorizes that new complexity.

## 2. Decisions

### A · Borrow the donor architecture, not a parallel installed framework — CHOSEN

Copy the orchestration semantics and worker contracts closely. Do **not** install `codex_workflow`
into Skynet as a second orchestration product if the same behavior can live cleanly in Skynet's own
files.

Also do not create donor `agent_docs/` as a second truth system. Map donor continuity onto Skynet:

| Donor concept | Skynet canonical owner |
|---|---|
| overview / architecture | `docs/system-design.md` + relevant `docs/design/` |
| project structure / ownership | repo + generated context map where applicable |
| progress / current position | active `planning/projects/SKY-###` directive |
| diary / discarded approaches / lessons | append-only `journal/` |
| session handoff | directive close-out + generated digest/context map + optional disposable checkpoint |
| operator/public docs | their existing canonical docs/runbooks |

One fact, one canonical home. No duplicate durable tracker.

### B · Main is a decision owner, not an extra Heavy-route worker — CHOSEN

Heavy Main owns:

- task understanding;
- architecture and cross-package contracts;
- material causal/root-cause decisions;
- decomposition and worker ownership;
- integration decisions;
- risk/authority decisions;
- final acceptance and user communication.

Heavy Main should not routinely:

- write production code or tests;
- perform implementation assigned to an Executor;
- execute the Tester's verification;
- run ordinary deployment operations;
- chase routine logs/environment checks;
- take over a package because its first worker attempt failed.

Main may directly inspect the smallest evidence needed for an architecture, scope, risk, causal, or
acceptance decision. Route the rest.

### C · Adopt Light / Medium / Heavy routes — CHOSEN

| Route | Production/verification owner | Support | Intended use |
|---|---|---|---|
| **Light** | Main | none | Q&A and small leaf work |
| **Medium** | Main | Companion, Investigator, Archivist | substantive work benefiting from context/research support while Main still implements |
| **Heavy** | Executors + Testers | full topology | large/cross-cutting work that can be decomposed |

Borrow donor route semantics closely: Light is default when neither user nor active directive packet
selects another route. Do not infer Medium/Heavy merely because workers exist. A directive may select
a route so Ali does not have to micromanage worker spawning. Keep the selected route for that
substantive deployment unless explicitly changed.

### D · Adopt the donor roles and model defaults — CHOSEN

Initial defaults, matching donor source contracts unless the installed harness proves an identifier or
effort unsupported:

| Role | Model | Effort | Sandbox | Quantity |
|---|---|---|---|---:|
| Main | session-selected | task-selected | invoking session | 1 |
| Companion | `gpt-5.6-luna` | xhigh | read-only | exactly 1 persistent in deployment state |
| Investigator | `gpt-5.6-luna` | xhigh | read-only | as needed |
| Default Executor | `gpt-5.6-luna` | max | workspace-write | as needed |
| Senior Executor | `gpt-5.6-sol` | medium | workspace-write | max 1 |
| Tester | `gpt-5.6-luna` | xhigh | workspace-write | as needed |
| Archivist | `gpt-5.6-luna` | xhigh | workspace-write | one at substantive closure, plus explicit doc assignments |

When README and worker TOML disagree, **source TOML wins**. Verify exact identifiers/efforts/sandboxes
against installed Codex metadata or safe dry-runs; do not silently substitute.

For SKY-026 itself, use **Sol High** as the preferred Main for architecture/contract work. Astra Medium
is appropriate when a genuinely consequential cross-cutting decision warrants it. After the new roles
exist, later phases must dogfood them.

### E · Delete the SKY-022 role surface, do not preserve compatibility — CHOSEN

Retire SKY-022's `scout`, `mechanic`, and `builder` role vocabulary, TOMLs, launcher routes, tests,
prompts and current doctrine. Perform a complete caller/reference search and **migrate every current
caller** to the new roles or delete the obsolete caller.

Do not create compatibility aliases or shims for SKY-022 role names. If an external current caller is
discovered, update that caller as part of SKY-026. If it cannot be updated safely, SKY-026 is blocked
until the dependency is resolved rather than preserving SKY-022 as a fallback.

### F · Knowledge capsules are the worker API — CHOSEN

Every initial worker assignment begins with a deployment-unique **Task ID** and uses donor capsule
shapes. Follow-ups repeat Task ID and send only changed capsule parts.

| Role | Initial capsule |
|---|---|
| Companion | `Project Context Scope` · `Context Task + Goal` · `Main-Agent Context Guidance` |
| Investigator | `Investigation Context` · `Evidence Question + Goal` · `Main-Agent Investigation Guidance` |
| Default/Senior Executor | `Implementation Context + Ownership` · `Implementation Task + Goal` · `Main-Agent Implementation Guidance` |
| Tester | `Verification Context` · `Verification Goal` · `Main-Agent Verification Guidance` |
| Archivist | `Documentation Context + Audience` · `Documentation Task + Goal` · `Main-Agent Documentation Guidance` |

Capsules transfer Main's relevant knowledge, rationale, contracts, constraints, boundaries, intended
outcome and cautions. Leave bounded discovery, command selection, implementation and ordinary
troubleshooting to the owner worker.

### G · Explicit context routing — CHOSEN

At substantive Medium/Heavy entry, Main builds a compact working context map:

- **Direct**: decision-critical contracts/evidence Main must inspect;
- **Companion**: supporting/bulky project context returned as one bounded synthesis;
- **Investigator**: a bounded unfamiliar project or Internet evidence gap.

The map is working state, not durable documentation. Reclassify only when evidence changes relevance.
Do not directly explore a Companion/Investigator surface unless it becomes decision-critical.

Companion is persistent and project-centered. Investigator is disposable and evidence-gap-centered.
Workers report to Main, not to Companion; Companion is not an LLM message bus.

### H · Batch coordination and suppress Main wakeup noise — CHOSEN

Borrow donor batching rules closely:

- dispatch independent workers informing the same decision together;
- wait for the relevant set and synthesize once;
- open another batch only when previous evidence changes the next question;
- run independent non-overlapping mutable packages concurrently when dependencies allow;
- keep dependencies, overlapping mutations, uncertainty and risky work sequential;
- do not poll workers or request status-only updates;
- do not rerequest evidence already returned;
- batch Main's own independent reads/searches/metadata checks when inputs are known together.

Optimization target: **fewer Main decision turns and less Main-context replay while preserving quality**.
Aggregate worker token minimization is not the goal.

### I · Borrow upstream's no-workflow-cap concurrency model — CHOSEN

Delete SKY-022's artificial `max_concurrent_threads_per_session = 2` policy. Upstream intentionally
removed its workflow-owned aggregate cap; SKY-026 should follow that design rather than invent a new
number.

Concurrency is controlled by platform capacity and task judgment, not a workflow quota. Keep only
semantic limits that matter:

- exactly one persistent Companion per deployment;
- at most one Senior Executor;
- concurrent mutable assignments require non-overlapping ownership;
- workers never spawn workers;
- dependencies/risk remain sequential;
- production authority never expands because more construction workers exist.

If current Codex requires a technical maximum, use the platform-supported/default mechanism without
turning that value into Skynet doctrine. Do not add dynamic auto-scaling logic.

### J · Executor owns ordinary repair; Tester owns independent verification — CHOSEN

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
architecture, authority, security/migration risk, external blocker, or repeated focused failure.

After one evidence-free worker response, send one focused retry. After a second, replace the worker or
report the limitation. Main does not automatically become Executor or Tester.

### K · Construction authority remains separate from production authority — CHOSEN

Worker role or sandbox grants **zero production authority**. Workers receive no production credential,
root grant, T2/T3 permission, or implicit live-infrastructure access merely because they can edit the
workspace. Live actions still follow `docs/system-design.md`, trust tiers, capability gates and human
checkpoints. Authored work remains human-merged.

### L · Fresh external review stays outside the implementation swarm — CHOSEN

Executor self-check + Tester verification + Main acceptance are internal Heavy-route gates. Final
acceptance review runs in a **fresh session** outside that swarm.

The reviewer never repairs SKY-026. If it finds a fixable defect, it emits exactly one complete
paste-ready prompt for the original implementation session. That session fixes; a fresh reviewer then
reviews again. Repeat until ACCEPT.

## 3. Scope and non-goals

### In scope

- rewrite `docs/conventions/construction.md` around donor semantics;
- shrink/adjust `AGENTS.md` so only load-bearing route/safety rules stay always loaded;
- replace old worker TOMLs with Companion, Investigator, Default Executor, Senior Executor, Tester,
  Archivist;
- adapt `.codex/config.toml`, `bin/agent`, tests and invariants;
- remove the old two-helper cap rather than replacing it with another arbitrary cap;
- implement route selection, capsules, context routing, batching, ownership and repair doctrine;
- map Companion/Archivist continuity onto existing Skynet truth surfaces;
- borrow deterministic token-reporting machinery where reliable;
- dogfood the architecture on real SKY-026 work;
- remove **all current SKY-022 orchestration dependencies and authority references**;
- preserve SKY-022 only inside archive/journal as inert provenance.

### Explicitly out

- installing a parallel `codex_workflow` control plane when Skynet can own the same contracts;
- creating `agent_docs/` as a second durable truth tree;
- LLM wave-manager/barrier parents;
- scheduler, queue, DAG engine, workflow DB, worker leases/heartbeats/retry service;
- custom inter-agent transport when native Codex works;
- automatic merge of authored work;
- widening production trust/credential boundaries;
- preserving any SKY-022 compatibility API, role alias, fallback doctrine, or current behavior;
- rewriting/deleting archived SKY-022 or journal history;
- changing unrelated SKY-025 engine scope.

## 4. Plan

### Phase 1 · Transplant the orchestration contract  `[x]` done
**Recommended Main:** Sol High

Goal: make donor semantics the one current construction model before wiring all workers.

Steps:
1. Re-read pinned donor source and current upstream `main`; record only material implementation deltas.
2. Rewrite `docs/conventions/construction.md` rather than patching SKY-022 wording. Import routes,
   Main boundary, context routing, batching, capsules, lifecycle/repair rules and no-manager-agent rule.
3. Preserve only explicit Skynet deltas: existing truth surfaces, trust tiers, human merge, directive
   lifecycle, fresh external review.
4. Reduce `AGENTS.md` to the minimum always-loaded orchestration contract and link the spoke for detail.
5. Remove current Scout/Mechanic/Builder, max-two-helper and other SKY-022 wording rather than adding
   transition notes or compatibility language.
6. Search all current doctrine/prompts/runbooks for SKY-022 references. Migrate any reference that
   supplies present behavior to SKY-026; historical/archive references may remain only where explicitly
   historical.
7. Add deterministic assertions only for rules the machine can actually prove.

Exit criteria:
- one canonical current construction doctrine;
- Main/worker ownership and repair boundaries unambiguous;
- **no current source derives construction authority from SKY-022**;
- no fallback to SKY-022 exists when SKY-026 is silent;
- no new production authority or memory truth tree;
- current docs state present rules, not migration narrative.

Close-out: PR + journal episode + directive progress bump + `bin/plan list`.

### Phase 2 · Replace worker roles and Codex configuration  `[x]` done
**Recommended Main:** Sol High

Goal: make native Codex config match doctrine and eliminate the SKY-022 runtime surface.

Steps:
1. Add Skynet-native TOMLs closely derived from upstream for `companion`, `investigator`,
   `default_executor`, `senior_executor`, `tester`, and `archivist`.
2. Preserve worker-perspective instructions rather than workflow-designer omniscience.
3. Adapt only Skynet-specific source domains: Companion uses repo/directives/journal/generated context;
   Archivist writes assigned canonical docs/journal only and never hand-edits generated outputs; all
   roles preserve production isolation.
4. Remove old `builder.toml`, `mechanic.toml`, `scout.toml` after a complete caller search. Migrate every
   live caller; do not retain aliases or shims.
5. Remove SKY-022's workflow-owned max-two thread setting. Follow upstream's no-workflow-cap model; if
   current Codex itself requires a technical maximum, use platform-supported behavior without making
   the number doctrine.
6. Adapt `bin/agent` and tests to new names if the launcher still earns its thin debug/standalone role.
7. Remove any launcher command, environment knob, test expectation or invariant whose only purpose is
   preserving SKY-022 behavior.
8. Verify model IDs, efforts and sandboxes from installed harness metadata/dry-runs.

Exit criteria:
- six roles resolve with intended model and effort (applied per role from the role file);
- one current role vocabulary;
- Companion/Investigator are read-only by role ownership/instructions, and their TOMLs retain
  `sandbox_mode = "read-only"` as least-privilege intent / future-compatible declaration;
- filesystem reach is bounded by the spawning session — the project `.codex/config.toml` pins the
  construction session sandbox so **no construction worker inherits `danger-full-access`** (on Codex
  0.153.4 a role file's own `sandbox_mode` is not applied per child; see the platform note below);
- write roles gain no production authority, and production authority stays zero regardless of sandbox;
- no SKY-022 role alias, compatibility route, launcher, or artificial thread cap remains;
- tests/invariants agree with actual config and assert only what is machine-checkable (exact role
  set, model/effort/instructions, declared sandbox intent, no `danger-full-access` in any role file or
  the project config).

Platform note (Codex 0.153.4): per-role `sandbox_mode` is **not** an enforceable child filesystem
leash — `AgentRoleOverrides` applies instructions/model/reasoning but not sandbox, and
`apply_spawn_agent_runtime_overrides` copies the spawning turn's permission profile into the child
(`spawn_agent` exposes no child-sandbox argument). The enforceable boundary is the session sandbox set
in `.codex/config.toml`; the original wording "read-only roles cannot write" was not achievable and is
replaced above rather than silently dropped.

Close-out: PR + journal episode + directive progress bump + `bin/plan list`.

### Phase 3 · Wire Heavy orchestration, capsules, batching and repair  `[x]` done
**Recommended Main:** Sol High using the new Heavy route

Goal: prove behavior changed, not just filenames.

Steps:
1. Use a real substantial repository task from this phase as a Heavy deployment.
2. On deployment entry create exactly one persistent Companion with no unnecessary inherited turns;
   give it bounded Skynet context intake and reuse it.
3. Build Direct / Companion / Investigator working context before broad exploration.
4. Batch independent context/research lanes when naturally available; synthesize once.
5. Delegate at least one bounded implementation package to Default Executor using the exact capsule
   shape. Main must not duplicate it.
6. Use Senior Executor only if a genuinely hard package exists; otherwise record it was not justified.
7. Assign an independent Tester after implementation; give acceptance intent/risks, not a test script
   tailored to the implementation.
8. Exercise Executor→Tester→Executor→Tester repair on a natural defect or a bounded reversible
   synthetic fixture if no real defect occurs.
9. Demonstrate delta-only follow-up and no status polling.
10. Batch Main's own known-input inspections.

Exit criteria:
- Heavy completes a real change with Main primarily directing/integrating;
- capsules prevent repeated broad rediscovery;
- independent verification is genuine;
- ordinary repair returns to owner Executor and same Tester;
- no worker spawns children;
- no needless Main wakeup chatter;
- repo gates are at least as strong as before.

Close-out: PR + journal episode + directive progress bump + `bin/plan list`.

### Phase 4 · Adapt continuity, Archivist and token accounting  `[ ]` not started
**Recommended Main:** Sol High with Companion + Archivist

Goal: borrow donor closure/context economy without duplicating durable truth.

Steps:
1. Define Medium/Heavy intake from existing canonical Skynet sources. Main directly reads only the
   decision-critical set once; Companion owns bulky/reusable intake and later delta/conflict checks.
2. Map closure:
   - Main owns acceptance + active directive state;
   - Archivist gets verified facts only;
   - Archivist may update explicitly assigned current docs/runbooks and append journal evidence;
   - generated digest/context outputs are regenerated by their owning tools, never hand-edited;
   - optional `.agent/CHECKPOINT.md` remains disposable.
3. Port/adapt donor deployment-token-report patterns if current Codex exposes reliable recorded usage.
   Prefer donor parser/skill/tests over a new accounting design.
4. Report recorded usage only. Do not estimate price or fabricate missing counts. If reliable data is
   unavailable, record that limitation and omit brittle pseudo-metrics.
5. Use unique lowercase machine-safe deployment IDs for substantive Medium/Heavy work if current Codex
   can carry them cleanly. They are accounting boundaries, not a task database.
6. Test completed, paused and blocked closure paths for one clear next-session entry point.

Exit criteria:
- cold continuation uses existing Skynet truth + bounded Companion intake;
- no `agent_docs/` clone or second progress DB;
- Archivist cannot decide acceptance or hand-edit generated truth;
- closure docs remain concise/current;
- token report is deterministic/honest if implemented, or explicitly omitted with evidence.

Close-out: PR + journal episode + directive progress bump + `bin/plan list`.

### Phase 5 · Dogfood, eradicate SKY-022 current authority, and validate end to end  `[ ]` not started
**Recommended Main:** Sol High, Heavy route

Goal: finish with one coherent orchestration engine, zero SKY-022 current authority, and real
Skynet-scale evidence.

Steps:
1. Dogfood three representative tasks without Ali instructing individual worker spawns:
   - Light leaf task that stays single-agent;
   - Medium task where support helps but Main implements;
   - Heavy task with multiple specialists and independent verification.
   The active directive may select the route; Ali should not micromanage topology.
2. In Heavy, demonstrate useful concurrent workers with non-overlapping ownership when real work allows;
   do not treat fan-out as a quota.
3. Demonstrate Senior Executor is used only when justified, or correctly omitted.
4. Search **all current repo surfaces** for Scout/Mechanic/Builder, max-two-helper, lead-owned Heavy
   verification, active SKY-022 links, SKY-022-derived tests/prompts, or any other current dependence on
   SKY-022. Migrate or delete every one. Archive/journal references are allowed only when clearly
   historical and incapable of steering current behavior.
5. Verify `AGENTS.md`, construction doctrine, `.codex/*`, launcher, tests, invariants, prompts and
   runbooks tell one SKY-026 story.
6. Run focused and full relevant repo gates. Fix implementation defects before requesting final review.
7. Journal concise before/after evidence: Main wakeups/rollouts when measurable, worker use,
   coordination failures/retries and concurrency behavior. Do not universalize a tiny benchmark.
8. Mark ready for independent review but keep SKY-026 `in-progress` until ACCEPT.

Exit criteria:
- Light/Medium/Heavy behave as documented;
- all six specialist roles are live and internally consistent;
- **SKY-022 has zero current construction authority, callers, aliases, fallbacks, or compatibility
  surface**;
- Heavy Main boundary is respected;
- Tester defects round-trip through owner Executor;
- current docs stay lean and historical narrative stays in directive/journal;
- deterministic gates pass;
- fresh reviewer can reconstruct and challenge the entire result without consulting SKY-022 for
  present behavior.

Close-out before review: implementation PR(s), journal evidence, status stays `in-progress`.

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
      ├── Companion
      ├── Investigator(s)
      ├── Default Executor(s)
      ├── Senior Executor (0..1)
      ├── Tester(s)
      └── Archivist
      ↓
 Main integrates + accepts
      ↓
 authored PR
      ↓
 normal human merge gate
      ↓
 fresh independent review
```

Optimization target:

> **Spend Main context on decisions that need the whole picture. Spend worker context on bounded work.**

SKY-022 is not part of this operating model. It is an archived historical artifact only.

## 6. Review and repair protocol

This is mandatory and intentionally differs from SKY-025's reviewer-repairs-directly behavior.

### Reviewer rules

Run acceptance review in a **fresh session**. Reviewer does not modify implementation. Review:

- complete SKY-026 directive and exit criteria;
- current `main` plus implementation/fix PRs or merged SHAs;
- donor source contracts;
- `AGENTS.md`, construction doctrine, `.codex/*`, launcher/tests/invariants/prompts/runbooks and callers;
- deterministic gates + dogfood evidence;
- trust/memory/merge boundaries;
- proof that SKY-022 has **no current construction authority or compatibility surface**.

Reviewer may inspect SKY-022 only as historical provenance when needed to verify that its active
surfaces were actually removed. The reviewer must never use SKY-022 to fill a gap in SKY-026 behavior.
Reviewer may use read-only workers for evidence but owns the verdict.

### PASS

Return a concise `ACCEPT SKY-026` verdict with reviewed refs and critical passing evidence. Then the
original implementation session may perform final close-out bookkeeping held for acceptance.

### FIX

If **any fixable defect** exists, the reviewer's final response must be **only one fenced text block**
containing a complete paste-ready prompt for the original SKY-026 implementation session. No preamble,
no separate findings list, no prose outside the block.

Populate this structure with real findings, never placeholders:

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

### Re-review

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

Repeat until ACCEPT. Reviewer never repairs its own findings. Ali never has to translate review prose
into implementation instructions.

## 7. ▶ Execute prompt

Paste into a fresh session, replacing `<N>`:

```text
Read planning/projects/SKY-026-overhaul-agent-orchestration-around-a-main-worker-swarm.md and execute
Phase <N> only.

SKY-026 completely supersedes SKY-022. Do not use SKY-022 as current guidance, a fallback contract, or
compatibility target. Its archive/journal material is historical provenance only.

Borrow aggressively from viettran-edgeAI/codex_workflow using its source contracts as the donor, while
preserving only the explicit SKY-026 Skynet deltas: existing canonical truth/memory surfaces instead of
agent_docs, Skynet production trust tiers, human merge, and fresh external review.

Follow AGENTS.md and this directive. Keep current docs lean; history belongs in journal. Land one
reviewable PR, never merge your own authored work, and perform phase close-out when exits pass.
```

After Phase 2 lands, later phases must use/dogfood the new route and worker contracts. The old
SKY-022 helper model is not an allowed fallback.

## 8. ▶ Final review prompt

Paste into a **fresh** session after Phase 5 implementation evidence is ready:

```text
Independently review SKY-026 end to end.

Read planning/projects/SKY-026-overhaul-agent-orchestration-around-a-main-worker-swarm.md, current
AGENTS.md, docs/conventions/construction.md, .codex configuration/agents, launcher/tests/invariants,
current construction prompts/runbooks, all SKY-026 implementation/fix PRs or merged SHAs, and the
relevant donor source contracts from viettran-edgeAI/codex_workflow.

SKY-026 must completely supersede SKY-022. Verify that SKY-022 has zero current construction authority,
callers, aliases, fallbacks, compatibility behavior, or present-tense documentation references. Archived
directive/journal material may remain only as inert history and must not be required to determine
current behavior.

Do not modify the implementation and do not repair findings yourself. Verify all directive exit
criteria, role ownership, Light/Medium/Heavy behavior, context routing, task capsules, batching,
Executor↔Tester repair, continuity/closure, obsolete-role removal, model/sandbox configuration,
production isolation, human merge, and deterministic gates.

If everything passes, return a concise ACCEPT SKY-026 verdict with reviewed refs and critical evidence.
If any fixable defect exists, your FINAL RESPONSE MUST BE ONLY ONE fenced text block containing a
complete paste-ready fix prompt for the original SKY-026 implementation session. Include exact
findings, required fixes, verification and PR handling. No prose outside that block. The original
session will fix it; then a fresh independent session will review again.
```

## 9. Phase close-out

Phases 1–4:

- land one reviewable PR; never self-merge;
- append raw session evidence to `journal/`;
- bump `current_phase`, phase checkbox and `updated`; keep `in-progress`;
- run `bin/plan list`;
- provide next Execute prompt.

Phase 5:

- land implementation evidence and keep `in-progress` pending independent review;
- after `ACCEPT SKY-026`, one bounded close-out update marks Phase 5 `[x]`, sets `current_phase: 5`,
  `status: done`, refreshes roadmap, and archives through normal planning lifecycle;
- SKY-022 remains untouched in archive/journal **solely as inert historical provenance**. It must not
  appear in any current authority chain or be required for current construction behavior.

## 10. Status log

- 2026-09-10 — SKY-026 minted using `viettran-edgeAI/codex_workflow` as the architecture donor;
  snapshot `6d9b06f73bee7f899001b0bb102c70529a24313f`. Borrow upstream aggressively while preserving
  Skynet's existing truth, production trust and human-merge boundaries.
- 2026-09-10 — supersession clarified: **SKY-026 completely supersedes SKY-022**. SKY-022 retains no
  current authority, fallback, compatibility role, alias or caller. Archived directive/journal material
  remains only as inert historical provenance.
- 2026-09-10 — review policy set: reviewer never repairs SKY-026. Failed review returns only one
  paste-ready fix prompt to the original implementation session; fresh re-review repeats until ACCEPT.
- 2026-09-10 — concurrency aligned with upstream: remove the SKY-022 two-helper cap and do not replace
  it with another workflow-owned aggregate number; rely on platform capacity plus
  ownership/dependency/risk rules.
- 2026-09-10 — **Phase 1 done.** Rewrote `docs/conventions/construction.md` around donor semantics
  (routes, Main boundary, six roles, context routing, capsules, batching, repair loop, no-cap
  concurrency, fresh-session-review-returns-fix-prompt, Skynet continuity map). Migrated `AGENTS.md`,
  `docs/conventions.md`, `docs/system-design.md`, the construction runbook (+ re-rendered catalog),
  the generated context map, and SKY-025's optional-worker notes off the lead+two-helper vocabulary.
  Runtime surface (`.codex/*`, launcher, tests, invariants) intentionally deferred to Phase 2; the
  exhaustive SKY-022 sweep of SKY-025's inline execution model is deferred to Phase 5.
- 2026-09-10 — **Phase 2 done.** Added six `.codex/agents/*.toml` (companion, investigator,
  default_executor, senior_executor, tester, archivist) closely derived from the pinned donor TOMLs,
  re-pointed off `agent_docs/` onto Skynet's canonical surfaces, with production isolation on every
  role. Deleted builder/mechanic/scout. Verified luna·xhigh / luna·max / sol·medium against the live
  harness (codex 0.153.4) via real `codex exec` runs — source TOML values hold, no substitution.
  Established that `max_concurrent_threads_per_session` is a real codex field, not a SKY-022 invention;
  per Decision I removed the pinned `= 2` and let codex's default apply — the gate now fails if a cap
  reappears. Rewrote `bin/agent` to launch the six roles resolving each one from its TOML (dropped
  `lead`/`review`/`--tier`/`AGENT_MODEL_*`), updated `invariants.json` + `scripts/check-invariants.sh`
  + `tests/{agent,construction}-test.sh`. All deterministic gates green. Token accounting stays for
  Phase 4; the full current-authority SKY-022 sweep stays for Phase 5.
- 2026-09-10 — **Phase 2 fix (independent-review findings).** Stays `current_phase: 2`; Phase 3 unreleased
  until a fresh re-review accepts. (1) Verified from pinned openai/codex rust-v0.153.4 source that roles
  are discovered from each config layer's `agents/*.toml` and spawned in-session via `spawn_agent`
  (`agent_type=<role>`), loading the complete role contract; there is no standalone CLI for a named role.
  `bin/agent` only set model/effort/sandbox and never loaded `developer_instructions`, so it was a false
  mirror — **deleted** it and `tests/agent-test.sh`, and migrated every current-authority reference
  (construction.md, the construction runbook, sky-025-map.md, pre-commit, CI) to native-spawn-only.
  (2) Ran a live native smoke on the installed harness: all six roles spawned and resolved (no
  `unknown agent_type`), each child carried its own role file's `developer_instructions`, and the per-role
  model override applied (luna/sol as declared); a read-only-parent run confirmed the sandbox ceiling.
  Current discovery evidence no longer depends on SKY-022. (3) Regenerated `planning/README.md` with
  `bin/plan list` → SKY-026 `2/5`. Rewrote `construction-test.sh` to validate the real role TOMLs (23/0).
  Also corrected an honest overclaim: a role file's `sandbox_mode` is the enforced DECLARATION, but
  runtime filesystem reach is bounded by the spawning session (the parent is the ceiling) — the
  always-true boundary is zero production authority.
- 2026-09-10 — **Phase 2 fix #2 (second re-review: the construction session boundary).** Stays
  `current_phase: 2`; Phase 3 unreleased. The re-review confirmed per-role `sandbox_mode` is not an
  enforceable child leash on Codex 0.153.4 (role overrides carry instructions/model/reasoning, not
  sandbox; the spawn path copies the spawning turn's permission profile), and that the user-level
  `danger-full-access` default meant workers could inherit it. Established the boundary at the SESSION
  level instead of a launcher (YAGNI): project `.codex/config.toml` now pins
  `sandbox_mode = "workspace-write"` (network on), which overrides the user default (project layer wins
  per Codex config precedence). Verified on the installed harness: a normal project session runs
  workspace-write, and a native smoke (companion/investigator/default_executor/tester) showed every
  child inheriting workspace-write — **none danger-full-access**. Reworded the Phase 2 exit criterion
  "read-only roles cannot write" to the achievable contract (read-only by ownership/intent; session
  sandbox bounds filesystem reach; no worker inherits danger-full-access; zero production authority).
  Fixed the stale surfaces (nix/home/aliammar.nix bin/agent comment; companion/investigator mechanical
  comments; construction.md; runbook). The gate + construction-test now assert the project config is
  workspace-write and never danger-full-access (26/0). No launcher/proxy/second transport built.
- 2026-09-10 — **Phase 3 done.** Ran a real Heavy deployment with Task ID
  `sky026-p3-20260910`: exactly one reused Companion plus one Investigator supplied a batched context
  intake; one Default Executor owned the donor-derived construction contract gate; an independent
  Tester found two fail-open worker-orchestration mutations; the same Executor repaired them from a
  delta-only capsule and the same Tester rechecked to PASS (42/0). Main directed, integrated and owned
  acceptance without duplicating implementation or verification. Senior Executor was not justified.
  The gate now rejects drift in capsule shape, Task-ID/delta continuity, worker ownership, the repair
  loop, semantic role quantities and retired architecture. No worker spawned children, no production
  authority was used, and no custom dispatcher/runtime was added. Phase 4 is next.
- 2026-09-10 — **Phase 3 accepted follow-up: quiet disposable verification.** Phase 3 remains done at
  `current_phase: 3`. Current construction guidance now keeps ordinary repo-local and TMP-only T1
  mutation/cleanup inside `workspace-write` without operator escalation, prefers canonical tests and
  encoded repeatable fixtures, and uses language-native temporary lifecycles for exploratory scratch.
  The construction gate enforces the guidance on mutable worker roles and rejects project approval
  overrides (46/0). The inherited `on-request` posture, root-grant and authored-merge checkpoints stay
  unchanged; no broad `rm` rule, allowlist or permission framework was added. Phase 4 remains next.
