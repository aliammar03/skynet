---
id: SKY-022
title: Codex App Server as a future programmable agent control plane
status: draft
horizon: long
created: 2026-09-04
updated: 2026-09-04
phases: 0
current_phase: 0
tier_touched: [T1]
related:
  - docs/system-design.md
  - AGENTS.md
  - planning/ideas/SKY-017-the-road-to-full-agent-control-verification-proving-ground-and-an-evidence-earned-ratchet.md
  - "[[SKY-022-progress]]"
---

# SKY-022 · Codex App Server as a future programmable agent control plane

> Keep Codex App Server on the shelf as the clean upgrade path if the lightweight lead→subagent construction model eventually needs programmatic spawning, steering, resumption, or monitoring.

## 1. Problem / motivation

The preferred construction model is deliberately simple: one lead agent owns the task and may delegate a small number of bounded subtasks to native subagents. Git, the SKY directive, normal branches/worktrees when needed, deterministic tests, and an optional untracked `.agent/CHECKPOINT.md` provide the rest.

That simplicity should be preserved until it hurts.

Codex App Server is relevant only if repeated real-world friction appears around things such as:

- programmatically starting or resuming Codex threads;
- steering a running child agent from another process;
- observing several long-running agent turns without terminal babysitting;
- recovering cleanly from agent-process failure;
- coordinating a small number of workers when native delegation is no longer enough.

This directive exists so that capability is remembered without prematurely turning Skynet into an orchestration platform.

## 2. Brainstorm — options considered

**Option A — adopt App Server now.**
Gives a programmable Codex harness immediately, but introduces custom orchestration code before a demonstrated need exists.

**Option B — stay with CLI/native delegation forever.**
Simplest possible system, but leaves no named path if construction later needs durable programmatic control.

**Option C — keep App Server as an explicit deferred extension point.**
Use native Codex delegation and ordinary CLI workflows today; revisit only when measured pain justifies it.

**Decision: C (CHOSEN).** Complexity must be earned. App Server is a future primitive, not a current dependency.

## 3. Activation criteria

Do not promote or implement SKY-022 merely because App Server is available. Revisit it only when at least one recurring failure mode is demonstrated across real construction work, for example:

1. native lead→subagent delegation repeatedly cannot express the required workflow;
2. long-running jobs are frequently lost or require manual reconstruction after process/session failure;
3. Ali is repeatedly babysitting multiple Codex sessions just to start, resume, or collect their results;
4. steering or cancellation of running agents from a single control point becomes a repeated need;
5. the same orchestration shell glue is being reimplemented in several places.

A one-off inconvenience is not enough. Prefer simplifying the workflow first.

## 4. Constraints if activated

If this idea is eventually promoted:

- App Server remains an implementation detail behind Skynet's agent-agnostic contract.
- The repo, not App Server thread state, remains the source of truth.
- Production authority does not move into the construction plane.
- No database, queue, scheduler, or workflow engine is added unless independently justified.
- Prefer a thin adapter over a framework.
- Native Codex capabilities are used before rebuilding equivalent machinery.
- A fresh agent must still be able to recover from git + directive + working tree/checkpoint if App Server state disappears.

## 5. First experiment if promoted

The first implementation should be intentionally tiny:

1. start `codex app-server` locally;
2. connect with the smallest practical client;
3. create one thread and one turn;
4. stream progress and capture completion;
5. prove interruption/resume behavior;
6. compare the result against plain `codex exec` and native delegation;
7. keep it only if it removes a real source of friction.

No daemon, queue, multi-agent scheduler, or custom state store in the first experiment.

## 6. ▶ Execute prompt

```text
Read planning/ideas/SKY-022-codex-app-server-as-a-future-programmable-agent-control-plane.md.
Before doing any implementation, verify that at least one Activation criterion is supported by repeated evidence from real Skynet construction work. If not, leave SKY-022 as an idea and report that YAGNI still wins.

If the criterion is met, first promote this directive through the normal planning lifecycle and design the smallest experiment that tests whether Codex App Server materially improves the existing lead→subagent workflow. Preserve AGENTS.md and docs/system-design.md invariants.
```

## 7. Status log

- 2026-09-04 — minted as a deferred long-horizon idea. App Server is explicitly not part of the current lightweight construction path; revisit only after demonstrated orchestration pain.
