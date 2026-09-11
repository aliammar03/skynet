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
Initial defaults (verify exact identifiers and efforts against installed harness metadata or a safe
dry-run — **source TOML wins over any README**; do not silently substitute, report routing blocked
instead). The **Model** and **Effort** are applied per role from its file. The unprivileged NixOS
`aliammar` account is the common filesystem/OS boundary; role ownership can be narrower. `[manual]`

| Role | Model | Effort | Filesystem/OS boundary | Quantity |
|---|---|---|---|---|
| Main | session-selected | task-selected | `aliammar` account | 1 |
| Companion | `gpt-5.6-luna` | xhigh | `aliammar` account; read-only ownership | exactly 1 persistent per deployment |
| Investigator | `gpt-5.6-luna` | xhigh | `aliammar` account; read-only ownership | as needed |
| Default Executor | `gpt-5.6-luna` | max | `aliammar` account | as needed |
| Senior Executor | `gpt-5.6-sol` | medium | `aliammar` account | at most 1 |
| Tester | `gpt-5.6-luna` | xhigh | `aliammar` account | as needed |
| Archivist | `gpt-5.6-luna` | xhigh | `aliammar` account | one at substantive closure, plus explicit doc assignments |

- **Companion** — persistent, project-centred secretary, **read-only by ownership and instructions**:
  bounded context intake, large synthesis, and retained
  operational context. It is not a message bus; workers report to Main.
- **Investigator** — disposable worker for one bounded, unfamiliar project or Internet evidence gap,
  **read-only by ownership and instructions**. It supplies evidence; Main owns the causal decision.
- **Default Executor** — owns local discovery, implementation, self-check, deployment operations, and
  ordinary repair inside one bounded package.
- **Senior Executor** — the one optional higher-reasoning worker for an exceptionally hard
  mathematical, logical, architectural, or cross-cutting package. Record when it was not justified.
- **Tester** — independent verifier owning the assigned verification, test assets, and execution; it
  does not perform production repair.
- **Archivist** — substantive-closure worker for concise assigned documentation outside Main-owned
  directive/journal state; see [Continuity](#continuity-and-truth-surfaces).

## Context routing

At substantive Medium/Heavy entry, before broad exploration, Main reads the six compact files under
[`../../agent_docs/`](../../agent_docs/) once plus the active directive. These files are derived agent
memory, not runtime or configuration truth: when they conflict, the constitution, runtime/configuration,
current operational docs, active directive, and accepted evidence win and the memory is corrected.
Main then builds a compact working-context map:

- **Direct** — decision-critical contracts, interfaces, and evidence Main must inspect itself;
- **Companion** — supporting or bulky non-decisive project context, returned as one bounded synthesis;
- **Investigator** — one bounded unfamiliar project or Internet evidence gap.

Main reads the Direct set once. Companion owns the initial bulky/reusable canonical intake beyond the
compact memory set, then later checks only changed facts or conflicts; Investigator owns bounded
unfamiliar external evidence. The map is working state, not durable documentation; reclassify only when
evidence changes relevance. Do not directly explore a Companion/Investigator surface unless it becomes
decision-critical. `[manual]`

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

Executor self-check, Tester verification, and Main acceptance are the internal gates. The
implementation session then commits, pushes, opens its authored PR, returns the PR URL and review
handoff, and **stops**. Final acceptance review is an **operator-started action**: Ali manually starts
a separate fresh chat/session after human merge. The implementation session must not start, spawn, or
continue into that review. The reviewer never repairs the work: if it finds a fixable defect its entire
final response is one complete, paste-ready fix prompt for the original implementation session. That
session fixes and stops after publishing its fix PR; Ali manually starts another fresh reviewer. Repeat
until ACCEPT. `[manual]`

## Continuity and truth surfaces

[`../../agent_docs/`](../../agent_docs/) is the canonical compact **agent-memory view**, derived from
higher-authority sources rather than a second runtime/configuration truth tree. Keep exactly six files:
overview, core technology, structure, progress, reusable decisions/lessons, and latest-session handoff.
Summarise and link; do not copy procedures, inventories, raw episodes, or long history. `[testable/manual]`

Main owns acceptance and the deployment-state files `project_progress.md`, `project_diary.md`, and
`latest_session_work.md`. After acceptance, or when recording a paused/blocked closure, Main updates
those files and the active directive from verified evidence. The Archivist may update assigned stable
memory (`project_overview.md`, `project_core_tech.md`, `project_structure.md`) and assigned current
docs/runbooks; it never decides acceptance, rewrites Main-owned deployment state during closure, or
hand-edits generated outputs (`inventory/`, `docs/generated/`). `[manual]`

The generated digest remains the read-time view of recent decisions, open threads, and raw episodes;
the context map remains the generated routing/load-cost index. Neither generated view is required for
agent-memory continuity after `agent_docs/` and the active directive are read; retain each only for its
distinct generated-view consumer. `[manual]`

Every substantive closure leaves exactly one `## Next Entry Point` in `latest_session_work.md`: `[testable/manual]`

| State | Durable closure | One next entry point |
|---|---|---|
| complete | Main accepts, advances directive and progress, records reusable lessons plus the raw journal episode, and regenerates owned views | the next-phase Execute/Continue prompt |
| paused | Main records verified position, pending work, and checks without advancing the phase | the same-phase Continue prompt |
| blocked | Main records the exact external condition and sets directive/progress status `blocked` | the same-phase Continue prompt naming the unblock condition |

At the start of each substantive Medium/Heavy deployment, Main emits
`<!-- skynet-deployment-start: <deployment_id> -->` in its first commentary message. The ID is unique,
lowercase, underscore-safe working identity—not a task database. After all other closure work is sealed,
the one closing Archivist runs the project-local `deployment-token-report` skill. It reports only
recorded rollout counts and cached-input/input/output tokens from Codex session evidence; missing or
incomplete evidence is a reported limitation. Never estimate usage or price. `[testable/manual]`

## Trust and native tooling

Construction grants **zero production authority**: no production credentials, root grants, or T2/T3
actions reach a worker. The unprivileged `aliammar` Unix account is the filesystem/OS construction
boundary; role/model selection is not authorisation. See [`git.md`](git.md) and the constitution.
`[manual]`

Native Codex subagents are the **only** runtime mechanism — Main spawns a worker in-session (`spawn_agent`,
`agent_type = <role>`), and Codex loads that role's complete definition from its role file: instructions,
model, and effort are applied per role. There is no standalone launcher: a shell wrapper that only sets
model/effort cannot load a role's developer instructions, so it is not a role and must not stand
in for one. Use a named role only when the installed or project configuration actually exposes it; if a
required role is not exposed, report that route/role as **blocked** rather than silently substituting a
legacy role. The runtime surfaces are [`.codex/agents/`](../../.codex/agents/) (one role per `*.toml`,
discovered by Codex as a config layer), [`.codex/config.toml`](../../.codex/config.toml), and
[`invariants.json`](../../invariants.json) (checked by `scripts/check-invariants.sh`) — a role is
claimable only once these agree with this doctrine. `[testable/manual]`

Home Manager sets Codex to `approval_policy = "never"` and `sandbox_mode = "danger-full-access"`.
There is no project or role sandbox override. On the installed Codex, native children inherit the
spawning session's permission profile, so Main and workers can silently perform any ordinary action
available to the unprivileged `aliammar` account. Companion/Investigator remain read-only and all other
write scopes remain bounded by role ownership and instructions, not an OS sandbox. Prefer canonical
repository test commands and maintained fixtures for repeatable mutations; use language-native
temporary-directory lifecycle handling for disposable data. `[testable/manual]`

Exec-policy hard-blocks `gh pr merge`, `bin/grant-root`, and `./bin/grant-root`; these operations never
fall back to an approval prompt. Human merge and human-issued, time-bounded root grants remain the only
paths. No role/model receives a credential, token, root grant, T2/T3 authority, or permission to widen
its own leash. `[testable/manual]`
