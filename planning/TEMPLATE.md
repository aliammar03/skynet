---
id: SKY-000
title: <short imperative title>
status: draft          # draft | approved | in-progress | blocked | done | abandoned
horizon: short         # short | long   (mainly for ideas/)
created: 2026-01-01
updated: 2026-01-01
phases: 1
current_phase: 0
tier_touched: [T1]     # T1 | T2 | T2+ | T3 — if it hits T2+/T3 or moves a blast-radius boundary,
                       # the plan MUST also PR docs/system-design.md (the constitution).
related:               # authoritative files this directive touches
  - docs/system-design.md
---

# SKY-000 · <Title>

> One-line pitch: what this changes and why it's worth a session.

<!-- HOW TO USE THIS TEMPLATE (delete this block once the directive is fleshed out).
  `bin/plan` stamps this file for every new directive and auto-fills id / title / created /
  updated / status / horizon — so editing THIS file raises the floor for all future plans.
  The conventions that keep directives uniform (all proven in SKY-001 / SKY-003):
    • Sizing — one phase = one reviewable PR. Anything bigger ⇒ split it.
    • Decisions — one block per decision in §2; mark the winner (CHOSEN); keep the roads
      not taken so nobody re-litigates them.
    • Checkpoints — flag every T3 / destructive / credential / leaves-scope step as a
      ⚠ hard checkpoint (Ali acts; the agent stops and waits).
    • One PR per phase — it carries the work, `bin/check` evidence, its tier, and the §4 Status update.
    • Frontmatter — keep parsed keys value-only (NO inline `#` on title/phases/current_phase);
      `current_phase` = last COMPLETED phase (0 = not started); bump `phases` as you add them.
-->

## 1. Problem / motivation
What's wrong, missing, or worth improving today. The pain, concretely.

## 2. Brainstorm — options considered
*(The "we talked it through" record — one block per decision. Mark the winner (CHOSEN) and
preserve the roads not taken, with the tradeoff that killed each, so they stay killed.)*
- **Option A —** … tradeoffs.
- **Option B —** … tradeoffs.
- **Decision:** chose **X (CHOSEN)** because … .

<!-- Repeat the block for each independent decision (engine, placement, tier, TLS, …). -->

## 3. The plan
- **Scope / non-goals:** what's in, what's explicitly out.
- **Hosts & tiers touched:** … (drives grants + whether `docs/system-design.md` needs a PR).
- **Rollback posture:** how we back out (`git revert`, disable a timer, `docker compose down`, …).
- **Grants / human actions:** the narrowest host + shortest duration per phase.

### Phase 1 — <name>   `[ ]` not started   · review: Light | Full
Steps:
1. …
2. …

Exit evidence (how we know it's done): … — for a write path, name the failure-case test.
Grants / human actions: … — mark any T3 / destructive / credential step a **⚠ hard checkpoint**.

<!-- Add Phase 2, Phase 3, … Each phase is one PR. The tier is Full if the phase touches anything
     on the Full list in docs/conventions/construction.md. -->

## 4. Status
Current: Phase 0 not started. Next: Phase 1.
<!-- The phase PR itself updates this block, the phase box, and the frontmatter
     (`current_phase`, `status`, `updated`) — merge is completion. Run `bin/plan list` in the same PR. -->

## 5. Prompts
Execute / review: [`planning/prompts/`](../prompts/README.md) with this directive's path.

## 6. Status log
*(One dated line per milestone — cite PR numbers; convert relative dates to absolute. Newest last.)*
- 2026-01-01 — created (draft).
