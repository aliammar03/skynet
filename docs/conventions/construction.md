---
summary: "Main directs a specialist worker swarm on Light/Medium/Heavy routes; workers own bounded work, verification is independent, and a fresh session reviews the merged result and returns a fix prompt rather than repairing."
---

# Spoke · Construction delegation

> Main spends context on decisions that need the whole picture; specialist workers spend context on
> bounded work. Verification is independent of implementation, and final acceptance review runs in a
> fresh session that returns one paste-ready fix prompt — it never repairs.
> Governed by [`../conventions.md`](../conventions.md); production authority stays with the trust tiers.

Tags: **[testable]** = a deterministic gate can assert it; **[manual]** = requires review.

## Routes

Every deployment runs on one route. **Light** is the default when neither the user nor the active
directive packet selects another; do not infer Medium or Heavy merely because workers exist. A
directive may select the route so Ali does not micromanage worker spawning; keep that route for the
substantive deployment until it is explicitly changed. `[manual]`

| Route | Production & verification owner | Support | Use |
|---|---|---|---|
| **Light** | Main | none | Q&A and small bounded leaf work |
| **Medium** | Main | Companion, Investigator, Archivist | substantive work that benefits from context/research support while Main still implements and verifies |
| **Heavy** | Executors + Testers | full topology | large or cross-cutting work that decomposes into bounded packages |

## Main is a decision owner, not an extra worker

Main owns task understanding, architecture and cross-package contracts, material causal/root-cause
decisions, decomposition and worker ownership, integration, risk/authority decisions, final
acceptance, and user communication. In a substantive **Heavy** deployment Main does **not** routinely
write production code or tests, run the Executor's implementation, execute the Tester's verification,
run ordinary deployment operations, chase routine logs/environment checks, or take a package over
because its first worker attempt failed. `[manual]`

Main may directly inspect the **smallest** evidence needed for an architecture, scope, risk, causal,
or acceptance decision. Route the rest. Worker unavailability does not authorise Main to become an
Executor or Tester — reassign, replace, pause, or report the blocker. `[manual]`

## Roles and defaults

Main is the invoking session. Workers are native Codex subagents; they never orchestrate children.
Initial defaults (verify exact identifiers, efforts, and sandboxes against installed harness
metadata or a safe dry-run — **source TOML wins over any README**; do not silently substitute, report
routing blocked instead): `[manual]`

| Role | Model | Effort | Sandbox | Quantity |
|---|---|---|---|---|
| Main | session-selected | task-selected | invoking session | 1 |
| Companion | `gpt-5.6-luna` | xhigh | read-only | exactly 1 persistent per deployment |
| Investigator | `gpt-5.6-luna` | xhigh | read-only | as needed |
| Default Executor | `gpt-5.6-luna` | max | workspace-write | as needed |
| Senior Executor | `gpt-5.6-sol` | medium | workspace-write | at most 1 |
| Tester | `gpt-5.6-luna` | xhigh | workspace-write | as needed |
| Archivist | `gpt-5.6-luna` | xhigh | workspace-write | one at substantive closure, plus explicit doc assignments |

- **Companion** — persistent, project-centred read-only secretary: bounded context intake, large
  synthesis, and retained operational context. It is not a message bus; workers report to Main.
- **Investigator** — disposable read-only worker for one bounded, unfamiliar project or Internet
  evidence gap. It supplies evidence; Main owns the causal decision.
- **Default Executor** — owns local discovery, implementation, self-check, deployment operations, and
  ordinary repair inside one bounded package.
- **Senior Executor** — the one optional higher-reasoning worker for an exceptionally hard
  mathematical, logical, architectural, or cross-cutting package. Record when it was not justified.
- **Tester** — independent verifier owning the assigned verification, test assets, and execution; it
  does not perform production repair.
- **Archivist** — substantive-closure worker for concise assigned documentation outside Main-owned
  directive/journal state; see [Continuity](#continuity-and-truth-surfaces).

## Context routing

At substantive Medium/Heavy entry, before broad exploration, Main builds a compact working-context map:

- **Direct** — decision-critical contracts, interfaces, and evidence Main must inspect itself;
- **Companion** — supporting or bulky non-decisive project context, returned as one bounded synthesis;
- **Investigator** — one bounded unfamiliar project or Internet evidence gap.

The map is working state, not durable documentation; reclassify only when evidence changes relevance.
Do not directly explore a Companion/Investigator surface unless it becomes decision-critical. `[manual]`

## Task capsules

Every initial worker assignment opens with a deployment-unique **Task ID** and the capsule for that
role. Follow-ups repeat the Task ID and send only changed capsule parts. `[manual]`

| Role | Capsule parts |
|---|---|
| Companion | `Project Context Scope` · `Context Task + Goal` · `Main-Agent Context Guidance` |
| Investigator | `Investigation Context` · `Evidence Question + Goal` · `Main-Agent Investigation Guidance` |
| Default / Senior Executor | `Implementation Context + Ownership` · `Implementation Task + Goal` · `Main-Agent Implementation Guidance` |
| Tester | `Verification Context` · `Verification Goal` · `Main-Agent Verification Guidance` |
| Archivist | `Documentation Context + Audience` · `Documentation Task + Goal` · `Main-Agent Documentation Guidance` |

A capsule carries only material context, contracts, boundaries, decisions, constraints, intended
outcome, and cautions. Leave bounded discovery, command selection, implementation, and ordinary
troubleshooting to the owning worker. Give the Tester acceptance intent, risks, contracts, and gates —
not a test script tailored to the implementation.

## Batching and coordination

Optimise for **fewer Main decision turns and less Main-context replay** while preserving quality;
aggregate worker token use is not the goal. `[manual]`

- Dispatch independent workers that inform the same decision together, wait for the relevant set, and
  synthesise once. Open another batch only when earlier evidence changes the next question.
- Run independent, non-overlapping mutable packages concurrently when dependencies allow. Keep
  dependencies, overlapping mutations, uncertainty, and risky work sequential.
- Do not poll workers, request status-only updates, or re-request evidence already returned.
- Batch Main's own independent reads, searches, and metadata checks when the inputs are known together.

## Ownership, repair, and lifecycle

```text
Executor implements + self-checks → Tester independently verifies → ordinary defect?
   yes → same owning Executor repairs → same Tester rechecks → PASS
```

Main intervenes only when evidence changes a material decision: a capsule/contract conflict, ownership
or scope change, architecture, authority, security/migration risk, an external blocker, or repeated
focused failure. The resulting Main action is a revised decision and package, not operational takeover.
After one evidence-free worker response, send one focused retry; after a second, replace the worker or
report the limitation — Main does not become the Executor or Tester. `[manual]`

Concurrency is bounded by platform capacity and task judgement, **not a workflow-owned quota**. The
only standing limits are semantic: exactly one persistent Companion per deployment; at most one Senior
Executor; concurrent mutable assignments require non-overlapping ownership; workers never spawn
workers; dependencies and risk stay sequential; and production authority never expands because more
construction workers exist. Do not add an LLM wave manager, scheduler, queue, DAG engine, workflow
database, lease/heartbeat service, or custom agent transport unless native Codex genuinely cannot
express a required behaviour and Ali separately authorises that complexity. `[manual]`

## Fresh external review

Executor self-check, Tester verification, and Main acceptance are the internal gates. Final acceptance
review then runs in a **fresh session outside the swarm**. The reviewer never repairs the work: if it
finds a fixable defect its entire final response is one complete, paste-ready fix prompt for the
original implementation session. That session fixes; a fresh reviewer reviews again; repeat until
ACCEPT. Human merge makes the accepted result effective — authored PRs stay human-merged. `[manual]`

## Continuity and truth surfaces

There is **one canonical home per fact** — no second durable tracker and no `agent_docs/` truth tree.
Donor continuity maps onto existing Skynet surfaces: `[manual]`

| Continuity need | Canonical Skynet home |
|---|---|
| overview / architecture | [`../system-design.md`](../system-design.md) + relevant `docs/design/` |
| current position / progress | the active `planning/projects/SKY-###` directive |
| decisions, discarded approaches, lessons | append-only [`../../journal/`](../../journal/README.md) |
| session handoff | directive close-out + generated digest/context map + optional disposable checkpoint |
| operator / public docs | their existing canonical docs and runbooks |

Main owns acceptance and active directive state. The Archivist receives only verified facts, may update
explicitly assigned current docs/runbooks and append journal evidence, and **never** decides acceptance
or hand-edits generated outputs (`inventory/`, `docs/generated/`) — those are regenerated by their
owning tools. For work crossing sessions, keep a compact ignored `.agent/CHECKPOINT.md` and delete it
once durable facts reach their canonical home. `[manual]`

## Trust and native tooling

Construction grants **zero production authority**: no production credentials, root grants, or T2/T3
actions reach a worker, and the sandbox is a filesystem leash, not authorisation. See [`git.md`](git.md)
and the constitution. `[manual]`

Native Codex subagents are the **only** runtime mechanism — Main spawns a worker in-session (`spawn_agent`,
`agent_type = <role>`), and Codex loads that role's complete definition from its role file: instructions,
model, and effort are applied per role. There is no standalone launcher: a shell wrapper that only sets
model/effort/sandbox cannot load a role's developer instructions, so it is not a role and must not stand
in for one. Use a named role only when the installed or project configuration actually exposes it; if a
required role is not exposed, report that route/role as **blocked** rather than silently substituting a
legacy role. The runtime surfaces are [`.codex/agents/`](../../.codex/agents/) (one role per `*.toml`,
discovered by Codex as a config layer), [`.codex/config.toml`](../../.codex/config.toml), and
[`invariants.json`](../../invariants.json) (checked by `scripts/check-invariants.sh`) — a role is
claimable only once these agree with this doctrine. `[testable/manual]`

Each role file **declares** its sandbox, and the gate enforces the declaration and bans
`danger-full-access`. At runtime a spawned worker's filesystem reach is the spawning session's sandbox
as a **ceiling** — a role never escalates above it (a workspace-write role spawned under a read-only
Main runs read-only), and in the installed Codex the role file's own `sandbox_mode` does not by itself
reduce a worker below a workspace-write parent. So a read-only role's no-write guarantee holds only when
Main spawns it from a suitably bounded session; treat the declaration as least-privilege intent, not an
unconditional runtime leash. The boundary that always holds is **zero production authority**: no
credential, token, root grant, or T2/T3 action reaches any worker regardless of its filesystem sandbox.
`[manual]`
