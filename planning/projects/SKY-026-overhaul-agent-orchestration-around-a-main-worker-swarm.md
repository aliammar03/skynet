---
id: SKY-026
title: "Overhaul agent orchestration around a Main-directed worker swarm"
status: in-progress
horizon: long
created: 2026-09-10
updated: 2026-09-12
phases: 5
current_phase: 4
tier_touched: [T1]
related:
  - AGENTS.md
  - docs/conventions/construction.md
  - .codex/config.toml
  - .codex/agents/
  - agent_docs/
  - planning/archive/SKY-022-lean-multi-agent-construction-orchestration-lead-driven-delegation.md
  - planning/projects/SKY-025-make-operational-outcomes-verifiable-and-prune-misleading-guidance.md
---

# SKY-026 · Main-directed worker swarm

> SKY-026 completely supersedes SKY-022. Current construction uses one Main, bounded native specialist
> workers, independent verification, compact `agent_docs`, fresh external review of the open authored
> PR, then bounded closeout on that **same accepted PR** before one human merge.

## Goal

Make Skynet construction simple, cheap in Main-context, independently verifiable, and recoverable across
sessions without creating a second orchestration platform.

Design donor: `https://github.com/viettran-edgeAI/codex_workflow`, snapshot originally reviewed at
`6d9b06f73bee7f899001b0bb102c70529a24313f` (packaged architecture `1.1.17`). Borrow source contracts
aggressively where they fit, but keep Skynet-native runtime, trust boundaries, and Git workflow.

SKY-022 is inert historical provenance only. No current role, prompt, test, launcher, doctrine, alias,
fallback, or compatibility path may depend on Scout/Mechanic/Builder or SKY-022 behavior.

## Current topology

```text
Ali
 ↓
Main ── Companion (persistent read-only)
 ├── Investigator(s) (read-only evidence)
 ├── Default Executor(s) (bounded implementation)
 ├── Senior Executor 0..1 (hard package)
 ├── Tester(s) (independent verification)
 └── Archivist (pre-review stable docs/memory)
```

Workers never spawn workers. Native Codex roles are the only worker runtime. Do not add a scheduler,
queue, DAG engine, workflow DB, leases/heartbeats, or custom agent transport unless native Codex truly
cannot express a required behavior and Ali separately authorizes that complexity.

## Core decisions

### Routes

| Route | Owner | Support | Use |
|---|---|---|---|
| Light | Main | none | small bounded work |
| Medium | Main | Companion / Investigator / Archivist | substantive work Main still implements/verifies |
| Heavy | Executors + Testers | full topology | decomposable cross-cutting work |

Light is default unless the task/directive selects another route. Main owns architecture, decomposition,
integration, risk/authority decisions, internal implementation acceptance, and user communication.
Heavy Main does not routinely take over Executor or Tester work.

### Roles

| Role | Model | Effort | Quantity |
|---|---|---|---:|
| Main | session-selected | task-selected | 1 |
| Companion | `gpt-5.6-luna` | xhigh | exactly 1 persistent |
| Investigator | `gpt-5.6-luna` | xhigh | as needed |
| Default Executor | `gpt-5.6-luna` | max | as needed |
| Senior Executor | `gpt-5.6-sol` | medium | max 1 |
| Tester | `gpt-5.6-luna` | xhigh | as needed |
| Archivist | `gpt-5.6-luna` | xhigh | one at substantive pre-review closure |

Source TOML wins if prose disagrees. Construction runs inside the unprivileged `aliammar` account and
grants no production authority. `gh pr merge` and root-grant spellings remain hard-blocked to agents.

### Capsules and coordination

Every initial worker assignment has a deployment-unique Task ID plus the role capsule defined in
`docs/conventions/construction.md`. Follow-ups repeat Task ID and send only the delta.

Batch independent evidence/work that informs the same Main decision. Keep overlapping mutation,
dependencies, uncertainty, and risky work sequential. No workflow-owned aggregate concurrency cap.
Ordinary defects return to the same Executor and then the same Tester.

### Agent memory

`agent_docs/` contains exactly six compact derived memory files. Constitution/runtime/current docs/
active directives/accepted evidence remain higher authority and win conflicts.

Main owns:
- `project_progress.md`
- `project_diary.md`
- `latest_session_work.md`

Archivist may own assigned stable memory before review:
- `project_overview.md`
- `project_core_tech.md`
- `project_structure.md`

No semantic sync daemon or second task DB.

## Canonical review → closeout → merge lifecycle

This section is the SKY-026 application of `docs/conventions/construction.md`.

```text
implementation/fix session
        ↓
one authored open PR
        ↓
reports PR + STOPS
        ↓
Ali starts fresh reviewer
        ↓
reviewer resolves + reviews + rechecks base/head
        ├── FIX → original session repairs same PR → STOP → fresh review
        └── ACCEPT → reviewer posts machine-readable acceptance marker to PR
                         ↓
                Ali tells original session "accepted"
                         ↓
                original session validates marker
                + bounded closeout on SAME PR
                         ↓
                prove post-ACCEPT delta is closeout-only
                + CI + final base recheck
                         ↓
                   Ali human-merges ONCE
```

### Review

Reviewer is implementation-read-only. It may inspect anything needed and run read-only/verification
work, but never repairs implementation. Its only allowed repository mutation is one ACCEPT marker
comment on the PR:

```text
<!-- skynet-acceptance:v1
scope=SKY-026
verdict=ACCEPT
base=<full reviewed base SHA>
head=<full reviewed head SHA>
-->
```

The reviewer resolves current target/base + PR head itself and rechecks both immediately before verdict.
If either moved before verdict, refresh affected evidence before ACCEPT. Ali never copies or compares
hashes.

### After Ali says `accepted`

The original implementation/fix session must:

1. fetch the acceptance marker itself;
2. verify the PR is still open and current base/head equal marker base/head **before** closeout;
3. apply only closeout bookkeeping on that same PR;
4. prove marker-head..final-head is closeout-only;
5. run closure-focused gates and normal CI;
6. recheck target/base still equals marker base;
7. report that same PR ready for one human merge and STOP.

Allowed post-ACCEPT Git surfaces:

- this directive's status/current-phase fields and normal move into `planning/archive/`;
- planning index/roadmap/state-map entries exposing next work;
- `agent_docs/project_progress.md`, `project_diary.md`, `latest_session_work.md`;
- append-only `journal/` closure evidence;
- generated planning/context views refreshed by their normal generators solely because closure state
  changed.

Forbidden after ACCEPT without fresh review:

- source/runtime/configuration;
- tests or invariants;
- AGENTS/construction doctrine/runbooks;
- behavioral documentation;
- stable agent memory;
- production definitions;
- any other substantive change.

The sanctioned closeout commit moves PR head by design and does not itself invalidate ACCEPT. Any base
movement from reviewed base, unexplained head movement, or substantive post-ACCEPT delta does invalidate
ACCEPT and requires fresh review.

Private GitHub Free leaves a non-atomic race window between the final agent recheck and Ali's later
click-to-merge. Prompt merge minimizes but does not eliminate it. Do not require a paid GitHub feature,
manual SHA handling, or a helper that falsely claims atomic read/check+merge behavior.

There is **no post-merge closeout PR** for normal work. Merge of the accepted PR publishes both reviewed
substantive work and its bounded closeout bookkeeping.

## Phase status

- **P1 accepted**: route/Main-worker doctrine transplanted; SKY-022 authority retirement began.
- **P2 accepted**: six native roles; no legacy role launcher; unprivileged construction boundary.
- **P3 accepted**: Heavy route proved Companion intake, Executor ownership, independent Tester, owner
  repair, same-Tester recheck.
- **P4 accepted**: six-file `agent_docs`, authority/ownership split, cold-start continuity and recorded
  token reporting established.
- **P5 implementation ready, fresh review required**: end-to-end dogfood, continuity pruning, complete
  SKY-022 authority removal, and the final review/closeout lifecycle are on open PR #253.

## P5 exit criteria

Before external review:

- Light/Medium/Heavy behavior matches doctrine;
- six specialist roles and config agree;
- `agent_docs/` is compact normal cross-session memory;
- remaining generated continuity views each have a distinct consumer;
- SKY-022 has zero current authority/callers/aliases/fallbacks;
- Heavy Main boundary and Executor↔Tester ownership hold;
- focused/full deterministic gates pass;
- PR #253 is open and implementation/fix session stops.

After reviewer ACCEPT:

- reviewer posts the SKY-026 acceptance marker on #253;
- Ali says only `accepted` to the original session;
- that session performs bounded closeout on #253 itself;
- closeout marks P5 done, sets `current_phase: 5`, marks SKY-026 done, updates Main-owned final state
  memory, refreshes planning state, archives SKY-026, appends closure evidence, and exposes SKY-025 as
  active focus;
- post-ACCEPT delta is proven closeout-only;
- #253 is then human-merged once;
- no closeout-only PR and no automatic second acceptance review.

If closeout discovers a needed substantive change, do not smuggle it into bookkeeping: make the change
on #253, mark ACCEPT stale, and send the same PR through fresh review again.

## Execute prompt

For implementation/fix work:

```text
Read planning/projects/SKY-026-overhaul-agent-orchestration-around-a-main-worker-swarm.md and continue
SKY-026 Phase 5 only. Follow AGENTS.md and docs/conventions/construction.md. Update the same open PR
#253. After publishing implementation/fixes, report the PR and STOP. Do not start acceptance review.
```

After Ali receives ACCEPT, Ali returns to that original session and says simply:

```text
accepted
```

The session follows **After Ali says `accepted`** above, closes out #253 itself, reports it ready for one
human merge, and stops.

## Review prompt

Fresh review needs only:

```text
Review open PR #253.
```

Reviewer must resolve/recheck Git revisions itself, post the acceptance marker on ACCEPT, and never ask
Ali to shuttle hashes.

## Current next action

Because this directive/workflow has been substantively changed after the previous review, the prior
ACCEPT is stale. Run one fresh review of open PR #253. On new ACCEPT, tell the original session only
`accepted`; it will close out #253 on the same PR, then Ali merges that PR once.
