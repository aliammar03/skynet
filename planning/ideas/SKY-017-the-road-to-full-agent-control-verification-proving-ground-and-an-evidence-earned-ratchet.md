---
id: SKY-017
title: The road to full agent control: verification, proving ground, and an evidence-earned ratchet
status: draft
horizon: long
created: 2026-08-28
updated: 2026-08-28
phases: 5
current_phase: 0
tier_touched: [T1, T2]   # P1–P3 build T1 machinery; P4–P5 graduate capabilities to A3/A4, which
                         # moves the autonomy dial ⇒ every promotion is a docs/system-design.md +
                         # AGENTS.md PR, human-merged forever (§2a: the agent never widens its leash).
related:
  - docs/system-design.md
  - docs/decisions/0005-full-agent-control-as-terminal-goal.md
  - planning/ideas/SKY-004-reactive-operations-event-driven-layer-drift-as-signal.md
  - planning/ideas/SKY-016-harden-the-service-deployment-workflow-verify-reachability-not-just-health-plus-scaffolding-helpers.md
  - planning/scratchpad/research/2026-08-28-complete-system-and-ansible.md
  - "[[SKY-017-progress]]"
---

# SKY-017 · The road to full agent control: verification, proving ground, and an evidence-earned ratchet

> Build the machinery that *buys* autonomy. The leash is on because the agent is unproven — so
> construct the thing that proves it: a place to rehearse, a way to verify, a second opinion, and a
> track record that turns promotion into a measurement instead of a feeling.

> **Status: idea.** The constitutional half landed first ([ADR 0005](../../docs/decisions/0005-full-agent-control-as-terminal-goal.md),
> system-design §1a). This directive is the build. Promote with `bin/plan start SKY-017`.

## 1. Problem / motivation

The goal is declared ([system-design §1a](../../docs/system-design.md)) and the ladder exists. What
doesn't exist is anything to spend on it.

- **The human is still the only verifier.** Every capability sits at **A1** — propose, human merges —
  except the nightly's generated-only self-merge at A4. There is no second check anywhere, so each
  loosening removes the only one.
- **There is nowhere to be wrong safely.** SKY-005 sketched a lab bench; nothing rehearses a real
  change against a real system. A2 is unreachable, which means A3 has no on-ramp.
- **Nothing measures the agent.** The ratchet says "graduate actions one at a time" and gives no
  criterion for when. Promotion is currently a judgement call by the person the promotion is meant
  to relieve.
- **Most actuators have no automatic rollback.** Arcane-from-git and deploy-rs magic-rollback both
  satisfy the reversibility test; `tofu apply`, DNS writes, container restarts and OS updates do not.
  Under ADR 0005 §3 that alone caps them below A4 no matter how well they work.
- **Nothing bounds a bad run.** A confidently-wrong agent inside its scope can touch every guest in
  the pool set in one pass. There is no change budget and no circuit breaker.

The through-line: **the system can act and can observe, but it cannot yet check itself.** That is the
whole gap between here and full agent control.

## 2. Brainstorm — options considered

**Where rehearsal happens (the proving ground)**
- **Option A — a permanent staging lab.** A parallel pool of long-lived twins. Highest fidelity;
  also a second lab to maintain, and a standing second blast radius. Its drift becomes its own
  problem.
- **Option B — ephemeral replicas, provisioned per rehearsal.** Tofu stands up throwaway guests in a
  `ops-rehearsal` pool from the same templates, the change is applied for real, assertions run, the
  guests are destroyed. Nothing persists, so nothing drifts — the same statelessness argument the
  rest of the system already makes. Costs provisioning time per run.
- **Option C — dry-run only.** `tofu plan`, `nixos-rebuild dry-activate`, `compose --dry-run`.
  Free and already available, but it proves the *plan* parses, never that the change *works*.
- **Decision:** **B (CHOSEN)**, with C as the always-on cheap tier. Rehearsal must execute or it
  isn't evidence. The ephemeral pool is a **blast-radius dial move** ⇒ system-design PR.

**What replaces the human as verifier**
- **Option A — more deterministic gates only.** Trustworthy and cheap, but only catches what was
  named in advance; can't catch "this works and is wrong".
- **Option B — gates + empirical verification (canary, health probe, auto-rollback).** Catches
  failures nobody predicted. This is the class the system most lacks.
- **Option C — B plus adversarial review by a second cold agent session.** Catches wrong-headedness.
  Errors correlate with the proposer's — more so on the same engine — so it is a filter, never a
  gate, and never replaces A or B.
- **Decision:** **all three, layered (CHOSEN)**, in that order of trust. Per ADR 0005 §2.

**How promotion is decided**
- **Option A — judgement, as today.** Doesn't scale and puts the decision on the person being
  relieved.
- **Option B — a recorded per-capability track record: N clean rehearsals + M clean supervised runs +
  a passing reversibility test, all in git, promotion by PR.** Mechanical, auditable, and slow in
  exactly the right way.
- **Decision:** **B (CHOSEN).** The record is generated (`inventory/`-class); the promotion PR is
  authored and human-merged forever.

**Containment for unattended action**
- **Option A — trust the scope declaration.** Scope is what a *correct* agent respects; the failure
  mode being defended against is an incorrect one.
- **Option B — a change budget per run (hosts touched, resources destroyed, records written) plus a
  circuit breaker that halts the run on the first unexplained failure and files a report.**
  Deterministic, enforced outside the agent's reasoning.
- **Decision:** **B (CHOSEN).** A budget the agent cannot raise mid-run is worth more than a scope it
  can rationalise.

## 3. The plan

- **Scope:** the proving ground, the verification layer, adversarial review, the track record, and
  budget/breaker containment — then the first two real graduations to prove the ladder works.
- **Non-goals:** graduating anything irreversible (permanently checkpointed, ADR 0005 §3); replacing
  the deterministic gates with agent judgement; any change to the T3 boundary; touching the CA.
- **Hosts & tiers touched:** ops VM (T1 machinery), a new `ops-rehearsal` pool (T2, blast-radius dial
  ⇒ **system-design PR**), and the capabilities graduated in P4–P5 (autonomy dial ⇒ **system-design +
  AGENTS.md PR**, human-merged).
- **Rollback posture:** every phase is additive and revertible — `git revert`, disable a timer,
  destroy the rehearsal pool. No phase changes an existing actuator's authority except P4/P5, which
  are themselves the reviewed promotions.
- **Grants / human actions:** none for P1–P3 beyond normal PR merge. P4/P5 each need Ali to merge the
  promotion PR — that merge **is** the approval, and is the permanent human step.

### Phase 1 — the reversibility audit + the change budget  (~1–2h)   `[ ]` not started
Cheapest first, and it tells the rest of the directive what it's working with.
Steps:
1. Enumerate every actuator the agent can drive today (Arcane deploy, `tofu apply`, Technitium
   record write, Cloudflare record write, container restart, guest snapshot, `apt` upgrade,
   deploy-rs activation). For each, record: is rollback **automatic**, **tested**, and **agent-
   independent**? Land it as an authored table beside `invariants.json`.
2. Classify each as *reversible* / *irreversible-by-nature* / *reversible-but-unproven*. The last
   bucket is the work queue for P2; the middle one is permanently checkpointed.
3. Implement the **change budget**: a per-run ceiling (guests touched, records written, destroys = 0)
   read from authored data and enforced by a non-LLM wrapper the agent runs *inside*, not beside.
4. Implement the **circuit breaker**: first unexplained failure halts the run, writes a journal
   incident, and alerts — no continue-on-error across hosts.

Exit criteria: every actuator has a recorded reversibility verdict; a run that exceeds its budget
aborts deterministically; a rehearsed failure trips the breaker and files an incident.

### Phase 2 — the proving ground  (~1–2h)   `[ ]` not started
Steps:
1. **⚠ Blast-radius dial:** PR `docs/system-design.md` to add an `ops-rehearsal` pool with its own
   scoped ACL — throwaway by construction, never holding a real workload, excluded guests unchanged.
2. Tofu module that stands up a replica guest from the same template the real fleet uses, and a
   `bin/ops rehearse <capability>` entry point: provision → apply the change for real → run the
   capability's assertions → destroy → emit a **rehearsal record** (pass/fail, diff, timings).
3. Wire the cheap dry-run tier (`tofu plan`, `dry-activate`, `compose --dry-run`) as the always-on
   pre-check in front of it.

Exit criteria: `bin/ops rehearse deploy-service` provisions, deploys, asserts, destroys, and leaves
a machine-readable record — with no residue in the real pools.

### Phase 3 — verification + adversarial review  (~1–2h)   `[ ]` not started
Steps:
1. **Post-change verification** as a first-class step, not a runbook sentence: bounded plan diff
   before apply, canary scope where the actuator supports it, health probe after, and **automatic
   rollback on probe failure** — driven by the dumb executor, not by the agent noticing. Reuses
   SKY-016's reachability work rather than duplicating it.
2. **Adversarial review**: `bin/ops review <ref>` opens a second, cold session (different engine
   where available) with no shared context, handed only the diff, the constitution, and the stated
   intent. It votes and explains; the vote is advisory, recorded on the PR, and never replaces a gate.
3. Attribute drift (SKY-004) to an entity, so a verification failure names *what* regressed.

Exit criteria: a deliberately-broken change is caught and auto-rolled-back without human action; the
reviewer session flags a constitution-violating diff it was not told to look for.

### Phase 4 — the track record, and the first graduation to A3  (~1–2h)   `[ ]` not started
Steps:
1. A generated per-capability record (`inventory/`-class, nightly-refreshed): rehearsals run,
   outcomes, supervised runs, failures, current level. Rendered into the digest so a cold agent knows
   what it is trusted with.
2. Pick the first graduation: **restart an unhealthy container in a declared compose project**.
   Reversible, bounded, high-frequency, obviously useful, and its failure mode is visible.
3. Run it at A2 until the record is clean, then **⚠ PR the promotion to A3** (`AGENTS.md` §3 +
   system-design §2b). Human-merged — permanently, by §2a.

Exit criteria: the record is generated and legible; one capability is at A3 with the evidence that
bought it linked from the promotion PR.

### Phase 5 — the first A4, end to end  (~1–2h)   `[ ]` not started
Steps:
1. Take the P4 capability to **A4**: automatic rollback proven in the failure case, budget and
   breaker enforced, alert on action rather than approval before it.
2. Run the full intent→delivery path once for a real service — intent, draft, gates, review,
   rehearsal, apply, verify, publish, back up, document — measuring where a human was actually
   needed. That list is the roadmap's next input.
3. **⚠ Drill the stateless invariant**: rebuild a service's *system* class from git alone into an
   empty running state, then restore payload separately. Prove §2a's rebuild law rather than
   asserting it.

Exit criteria: one capability runs unattended with a tested automatic rollback; the intent→delivery
walkthrough names every remaining human touchpoint; the git-alone rebuild drill passes.

## 4. ▶ Execute prompt
```
Read planning/projects/SKY-017-the-road-to-full-agent-control-verification-proving-ground-and-an-evidence-earned-ratchet.md and execute Phase <N>.
Follow AGENTS.md: plan loudly then run quietly, never merge your own PRs, request the
narrowest host / shortest grant the phase needs, and checkpoint at the listed human/grant
steps. Every promotion PR is human-merged — you never widen your own leash. When the phase's
exit criteria are met, do the "Phase close-out" at the bottom.
```

## 5. Phase close-out (resume material)
- [ ] Land the work via **PR** (agent never merges its own).
- [ ] Write/refresh a memory `SKY-017-progress` (what shipped, what's next, gotchas) + a MEMORY.md pointer.
- [ ] Bump this file's frontmatter (`current_phase`, `status`, `updated`) and flip the phase box to `[x]`.
- [ ] `bin/plan list` to refresh the roadmap index.
- [ ] Paste the **Continue prompt** below to resume in a fresh session:
```
Continue planning/projects/SKY-017-the-road-to-full-agent-control-verification-proving-ground-and-an-evidence-earned-ratchet.md at Phase <N+1>.
Prereqs carried from the last phase: <…>. Resume context from memory [[SKY-017-progress]].
Follow AGENTS.md as above.
```

## 6. Status log
- 2026-08-28 — created (draft). Constitutional half landed first: ADR 0005 + system-design §1a
  (terminal goal, A0–A5 ladder, the never-delegated law, the git-alone rebuild law).
