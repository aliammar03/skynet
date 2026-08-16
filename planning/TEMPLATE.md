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
related:               # files + memories this touches; [[slug]] cross-links a memory
  - docs/system-design.md
  - "[[SKY-000-progress]]"
---

# SKY-000 · <Title>

> One-line pitch: what this changes and why it's worth a session.

<!-- HOW TO USE THIS TEMPLATE (delete this block once the directive is fleshed out).
  `bin/plan` stamps this file for every new directive and auto-fills id / title / created /
  updated / status / horizon — so editing THIS file raises the floor for all future plans.
  The conventions that keep directives uniform (all proven in SKY-001 / SKY-003):
    • Sizing — one phase ≈ 1–2h (fits one session). Anything longer ⇒ split it.
    • Decisions — one block per decision in §2; mark the winner (CHOSEN); keep the roads
      not taken so nobody re-litigates them.
    • Checkpoints — flag every T3 / destructive / credential / leaves-scope step as a
      ⚠ hard checkpoint (Ali acts; the agent stops and waits).
    • Close-out — every phase ends with §5: PR + `SKY-000-progress` memory + frontmatter bump.
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

### Phase 1 — <name>  (~1–2h)   `[ ]` not started
Steps:
1. …
2. …

Exit criteria (how we know it's done): …
Grants / human actions: … — mark any T3 / destructive / credential step a **⚠ hard checkpoint**.

<!-- Add Phase 2, Phase 3, … Keep each phase to ~1–2h. Flip its box `[ ]`→`[x]` on close-out. -->

## 4. ▶ Execute prompt
> Paste into a fresh Skynet session to run this directive. Swap `<N>` for the phase to run.
```
Read planning/projects/SKY-000-slug.md and execute Phase <N>.
Follow AGENTS.md: plan loudly then run quietly, never merge your own PRs, request the
narrowest host / shortest grant the phase needs, and checkpoint at the listed human/grant
steps. When the phase's exit criteria are met, do the "Phase close-out" at the bottom.
```

## 5. Phase close-out (resume material)
Run this every time a phase finishes successfully — it's what makes the next session cold-startable:
- [ ] Land the work via **PR** (agent never merges its own).
- [ ] Write/refresh a memory `SKY-000-progress` (what shipped, what's next, gotchas) + a MEMORY.md pointer.
- [ ] Bump this file's frontmatter (`current_phase`, `status`, `updated`) and flip the phase box to `[x]`.
- [ ] `bin/plan list` to refresh the roadmap index.
- [ ] Paste the **Continue prompt** below to resume in a fresh session:
```
Continue planning/projects/SKY-000-slug.md at Phase <N+1>.
Prereqs carried from the last phase: <…>. Resume context from memory [[SKY-000-progress]].
Follow AGENTS.md as above.
```

## 6. Status log
*(One dated line per milestone — cite PR numbers; convert relative dates to absolute. Newest last.)*
- 2026-01-01 — created (draft).
