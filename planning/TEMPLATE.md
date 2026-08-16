---
id: SKY-000
title: <short imperative title>
status: draft          # draft | approved | in-progress | blocked | done | abandoned
horizon: short         # short | long   (mainly for ideas/)
created: 2026-01-01
updated: 2026-01-01
phases: 1
current_phase: 0
tier_touched: [T1]     # T1 | T2 | T2+ | T3 — if T2+/T3 or a boundary changes, PR docs/system-design.md too
related: []            # e.g. docs/system-design.md, planning/projects/SKY-0xx-*.md, [[memory-slug]]
---

# SKY-000 · <Title>

> One-line pitch: what this changes and why it's worth a session.

## 1. Problem / motivation
What's wrong, missing, or worth improving today. The pain, concretely.

## 2. Brainstorm — options considered
*(Kept for the record. This is the "we talked it through" step — preserve the roads not taken.)*
- **Option A —** … tradeoffs.
- **Option B —** … tradeoffs.
- **Decision:** chose **X** because … .

## 3. The plan
- **Scope / non-goals:** what's in, what's explicitly out.
- **Hosts & tiers touched:** … (drives grants + whether `docs/system-design.md` needs a PR).
- **Rollback posture:** how we back out (git revert, disable timer, etc.).
- **Grants / human actions needed:** the narrowest host + shortest duration per phase.

### Phase 1 — <name>  (~1–2h)   `[ ]` not started
Steps:
1. …
2. …

Exit criteria (how we know it's done): …
Grants / human actions: …

<!-- Add Phase 2, Phase 3, … Keep each phase to ~1–2h so it fits one session. -->

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
- 2026-01-01 — created (draft).
