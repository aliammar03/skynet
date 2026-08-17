---
id: SKY-004
title: Reactive operations: event-driven layer + drift-as-signal
status: draft
horizon: long
created: 2026-08-17
updated: 2026-08-17
phases: 3
current_phase: 0
tier_touched: [T1, T2]   # T1 observe/propose; graduating any event→action to auto-approve is a
                         # T2 autonomy-ratchet step ⇒ PR docs/system-design.md + AGENTS.md.
related:
  - docs/design/observability.md
  - docs/design/gitops-loop.md
  - docs/system-design.md
  - planning/scratchpad/2026-08-17-declarative-future-and-agent-cognition.md
  - "[[SKY-006-progress]]"
  - "[[SKY-004-progress]]"
---

# SKY-004 · Reactive operations: event-driven layer + drift-as-signal

> Turn Skynet from batch (Arcane polls + a 03:30 nightly) into *reactive* — the agent wakes on a
> signal, and drift (desired − observed) becomes a first-class event. This is how the open control
> loop finally closes.

## 1. Problem / motivation
Everything today is **batch**. Arcane polls git; the nightly runs once at 03:30, report-only. The
[observability spoke](../../docs/design/observability.md) says it plainly: *there's no live signal
that pages when something breaks between nightlies.*

Worse, the system has two truths — `compose/` (**desired**, git→reality via Arcane) and
`inventory/` + the firewall mirror (**observed**, reality→git) — and **nothing wires the gap between
them back in.** Drift is noticed only when an agent happens to read inventory. In control-theory
terms: a plant, two sensors, no controller. Someone hand-edits the firewall or a container dies at
04:00 and Skynet is blind until the next nightly. (Full write-up:
[scratchpad thesis §1/§3](../scratchpad/2026-08-17-declarative-future-and-agent-cognition.md).)

## 2. Brainstorm — options considered

**Event transport**
- **Option A — a real broker (NATS / Redis streams).** Durable, scalable. But it's a standing
  service and a new paradigm — *raises the branching factor* we've been right to keep low, for a
  lab with a handful of event sources.
- **Option B — a tiny webhook receiver + a script.** A single small listener on the ops VM (research
  brief: `adnanh/webhook`, a static Go binary, **mandatory HMAC signature verification**) turns an
  HTTP hook into a scoped `bin/ops` invocation; ntfy (already used for grant-approval; consume via
  `ntfy subscribe`) carries alerts outbound. Lowest complexity, regenerable, no new always-on infra
  of note. **The receiver is a *trigger, not a store*** — it authenticates and dispatches one
  allowlisted capability, holds no T2+/T3 credential, and git stays authoritative (Flux's model).
- **Decision:** **Option B (CHOSEN).** Reach for a broker (NATS / Redis streams) only if real
  fan-out ever justifies it.

**How an event is allowed to *act* (safety)**
- **Option A — events can trigger actions immediately.** Fast, but blows past the autonomy ratchet.
- **Option B — reactive-but-report-only first; graduate specific `event→action` pairs onto the
  auto-approve list one at a time, each by PR.** Same ratchet already in the constitution, applied to
  reactivity instead of the nightly.
- **Decision:** **Option B (CHOSEN).** An event may *always* observe + propose + alert; it may only
  *act* for a pair explicitly promoted in `docs/system-design.md` + `AGENTS.md`.

**Drift signal**
- Emit a **drift event** when desired ≠ observed, per layer: `docker compose config`/`--dry-run` diff
  (works today), firewall-mirror vs a declared baseline, and later `tofu plan -detailed-exitcode`
  (exit 2 = drift) / `nixos-rebuild dry-activate` once those layers exist (SKY-008 / SKY-007). Drift
  is the **best-fit event source** because desired state already lives in git.
- **Decision:** start with the layers that exist now (compose + firewall mirror); infra-layer drift
  lights up for free as SKY-007/008 land. **This is literally the controller from §1.**

## 3. The plan
- **Scope / non-goals:** build the *observe → propose → alert* reactive spine and drift detection.
  **Non-goal:** any autonomous action — that's a later, per-pair ratchet step.
- **Hosts & tiers touched:** ops VM (`vm-skynet-ops`). P1–P2 are **T1** (observe/propose only). P3
  (first graduated action) is **T2** and **requires a `docs/system-design.md` + `AGENTS.md` PR**.
- **Rollback posture:** disable a timer / `systemctl stop` the receiver / `git revert`. Nothing
  destructive; report-only until P3.
- **Grants / human actions:** none for P1–P2 beyond normal PR merge. P3 is a ⚠ hard checkpoint
  (widening autonomy).

### Phase 1 — drift-as-signal, report-only  (~1–2h)   `[ ]` not started
A scheduled diff (compose config + firewall-mirror vs declared baseline) that emits an ntfy alert
and a journal note ([[SKY-006-progress]]) when desired ≠ observed. **No actions.**
Exit: hand-editing the firewall or stopping a tracked container produces a same-day drift alert.

### Phase 2 — webhook receiver, propose-only  (~1–2h)   `[ ]` not started
A small listener on the ops VM: GitHub merge webhook → deploy-verify + inventory refresh; Renovate PR
opened → triage note. Still only proposes/reports.
Exit: a merge to `compose/` triggers an immediate verify run instead of waiting for 03:30.

### Phase 3 — graduate the first event→action pair  (~1–2h)   `[ ]` not started
Promote **one** well-understood pair (candidate: *merge to `compose/` → Arcane verify + inventory
commit*) onto the auto-approve list. **⚠ hard checkpoint — PRs `docs/system-design.md` (autonomy
dial) + `AGENTS.md` (auto-approve list).**
Exit: exactly one event→action pair acts autonomously, recorded in the constitution.

## 4. ▶ Execute prompt
```
Read planning/projects/SKY-004-reactive-operations-event-driven-layer-drift-as-signal.md and execute Phase <N>.
Follow AGENTS.md: plan loudly then run quietly, never merge your own PRs, request the
narrowest host / shortest grant the phase needs, and checkpoint at the listed human/grant
steps. When the phase's exit criteria are met, do the "Phase close-out" at the bottom.
```

## 5. Phase close-out (resume material)
- [ ] Land the work via **PR** (agent never merges its own).
- [ ] Write/refresh a memory `SKY-004-progress` (what shipped, what's next, gotchas) + a MEMORY.md pointer.
- [ ] Bump this file's frontmatter (`current_phase`, `status`, `updated`) and flip the phase box to `[x]`.
- [ ] `bin/plan list` to refresh the roadmap index.
- [ ] Paste the **Continue prompt** below to resume in a fresh session:
```
Continue planning/projects/SKY-004-reactive-operations-event-driven-layer-drift-as-signal.md at Phase <N+1>.
Prereqs carried from the last phase: <…>. Resume context from memory [[SKY-004-progress]].
Follow AGENTS.md as above.
```

## 6. Status log
- 2026-08-17 — created (draft) from the declarative-future brainstorm. Batch→reactive + drift-as-event
  as the way the open control loop closes. Research feeding this: `planning/scratchpad/research/2026-08-17-reactive-memory.md`.
