---
id: SKY-001
title: Retire the deployment plan; stand up the system-design constitution + spokes
status: done
horizon: long
created: 2026-08-16
updated: 2026-08-16
phases: 4
current_phase: 4
tier_touched: [T1, T2, T2+, T3]   # docs-only, NO grants — but it rewrites the governing contract for
                                  # every tier (incl. the T3 wording + the merge dial), so it IS the
                                  # design-doc PR the boundary-change rule requires.
related: [docs/history/deployment-plan-v5.md, docs/system-design.md, docs/architecture.md, AGENTS.md, CLAUDE.md, "[[skynet-a6-next]]"]
---

# SKY-001 · Skynet defines itself — retire the plan, write the constitution + spokes

> The deployment plan drove Skynet from an empty VM to a graduated agent. That job is done.
> Freeze it for the record, and replace it with a forward-looking **system design** that defines
> the invariants and the extension points so the real expansion can begin without drifting past
> its own trust boundaries. The build was the birth; this is Skynet defining itself.

## 1. Problem / motivation
`docs/deployment-plan.md` (v5, "final", 493 lines) is **two documents in one cover**:
- an enduring **design** — §§1–12 + the Judgement Day checklist + Appendix A (bootstrap); and
- a **build log** — §13 phases, the build-status table, the A2/A4/A5 results, "resuming at A6".

Graduation (A6, 2026-08-16) ended the second job. The merged file is already **factually stale**
— §13 still shows A5.5/A6 "in progress" — and it is written as a *plan to reach a state*, not a
*definition of the state we now hold and intend to grow*. Seven files point at it as the
authoritative design, and `AGENTS.md` names it the tiebreaker ("the plan wins"). It cannot be
both a frozen artifact and the living contract. So: retire the plan whole (nostalgia intact),
and author a proper system design in its place.

## 2. Brainstorm — options considered
- **Option A — split in place:** keep `deployment-plan.md`, carve §13 into a `build-log.md`,
  reframe the top. Cheapest, but keeps the name "plan" for a system that's past planning, and
  keeps the design as one monolith that must be reopened for every future change.
- **Option B — one big `system-design.md`:** replace the plan with a single deep doc. Better name,
  but the invariants (change over years) and the domain detail (change over months) stay welded
  together, so expansion still reopens the whole thing.
- **Option C — constitution + spokes (CHOSEN):** a lean canonical `docs/system-design.md` holding
  only the slow-changing invariants + trust model + extension points, delegating domain depth to
  `docs/design/*.md` spokes. Expansion touches a spoke, not the constitution; the constitution
  stays short enough to actually read before a T2+/T3 change.
- **Decision:** **Option C.** Archive the whole v5 plan verbatim in `docs/history/` for reference
  and nostalgia; distill its build log into a readable `docs/history/build-log.md`.

## 3. The plan
- **Scope / non-goals.** In: freeze the plan, author the constitution + six spokes, re-point the
  7 referencing files, reconcile the always-loaded `AGENTS.md` contract wording, renumber the
  misfiled PBS directive. Out: no infra changes, no grants, no new services — this is pure
  docs/contract work. (The forward-looking systems it *names* — proxy, vault, SSO — become their
  own `SKY-###` later; this directive only reserves the room for them.)
- **Design principles baked into the new doc:**
  - **Voice** — keep and lean into the repo's Terminator flavor: Judgement Day invariants, the
    kill switch, "self-aware" at graduation, the CA as the one key Skynet *cannot mint for itself*.
    Flavor in the prose, never at the cost of a precise technical claim.
  - **Built to grow** — no hardcoded counts (the `ops-managed` pools are a *set*, "two today,
    grown by PR — never a fixed number"); invariants split into **hard laws** vs
    **version-controlled dials** (the human-merge gate is a dial whose first foreseeable loosening
    is agent auto-merge of *docs-only* PRs, not an eternal "never"); spokes with explicit forward
    hooks for a reverse proxy / ingress, a secrets vault beyond sops+age, and SSO/Authentik out of
    T3; the spoke set itself is **open** (likely-next: `identity-and-proxy.md`).
- **Hosts & tiers touched.** None operationally (docs-only, no grants). But it rewrites the
  contract governing *every* tier — including the T3 wording and the merge dial — so it satisfies
  the "boundary change ⇒ PR the design doc" rule by construction (it *is* that PR).
- **Rollback posture.** Every phase is a PR; `git revert` restores the prior doc state. Nothing
  destructive — the old plan survives as `history/deployment-plan-v5.md` even at the end.
- **Grants / human actions.** None beyond the usual: Ali reviews and merges each phase PR
  (the agent never merges its own).

### Phase 1 — Sync, renumber, mint the directive  (~1h)   `[x]` done
Steps:
1. `git fetch` + fast-forward local `main` (was behind #27/#28/#31).
2. Renumber the misfiled PBS directive **SKY-001 → SKY-002** (`git mv`, bump `id:`, fix self-refs,
   add a status-log note). ID moved before any progress memory existed → no external pointer breaks.
3. Author **this** directive (SKY-001) into `planning/projects/` with all four phases + prompts.
4. Update memory pointers so the PBS follow-up reads SKY-002 (`skynet-backups`, `skynet-a6-next`, `MEMORY.md`).

Exit criteria: on a branch, PBS directive is SKY-002 with clean self-refs, SKY-001 is this file,
memory points at SKY-002 for PBS, `next_id` → SKY-003. → PR.
Grants / human actions: Ali merges the P1 PR.

### Phase 2 — Author the new design (additive)  (~1–2h)   `[x]` done
Steps:
1. Write `docs/system-design.md` (constitution): invariants (hard laws vs dials), trust model,
   agent-agnostic contract, **extension points**, **growth directions**, spoke index (open set).
2. Write the six spokes under `docs/design/`: `network.md`, `access-and-trust.md`, `secrets.md`,
   `gitops-loop.md`, `disaster-recovery.md`, `observability.md` — each sourced from its plan
   section (see the content-sourcing map in the SKY-001 close-out plan) + its forward hook.
3. Write `docs/history/build-log.md` — the distilled, past-tense A1→A6 story (PR numbers preserved).
4. Add a top banner to `deployment-plan.md`: "⚠️ SUPERSEDED by `docs/system-design.md` — retained
   until P3 archive" (keeps `main` unambiguous while both coexist).

Exit criteria: new constitution + spokes + build-log exist and are self-consistent (every spoke
the constitution indexes exists); old plan still present but banner-marked; no design fact dropped.
→ PR.

### Phase 3 — Re-point + archive + retire  (~1h)   `[x]` done
Steps:
1. `git mv docs/deployment-plan.md docs/history/deployment-plan-v5.md` (frozen verbatim).
2. Re-point all 7 referencing files to `docs/system-design.md`; reword the tiebreaker
   ("the plan wins" → "the design wins") in `AGENTS.md` + `docs/architecture.md`; update the
   planning tier-touch rule in `planning/README.md` + `planning/TEMPLATE.md`.
3. **Reconcile the merge wording:** `AGENTS.md §6`'s flat "never merges its own" → the
   version-controlled-dial framing, matching the constitution.
4. Grep-verify: no live `deployment-plan` pointer outside `history/`, no "the plan wins" left,
   no broken relative links, merge-wording consistent, no hardcoded "two ops-managed pools".

Exit criteria: `system-design.md` is the sole authoritative design; all references resolve; the
always-loaded contract matches the constitution. → PR.

### Phase 4 — Close-out  (~30m)   `[x]` done
Steps:
1. `bin/plan archive SKY-001` (status → done) + `bin/plan list` (regenerate roadmap).
2. Memory: rewrite `skynet-a6-next` to point at `system-design.md`; write `SKY-001-progress`;
   refresh `MEMORY.md`.

Exit criteria: roadmap shows SKY-001 done + SKY-002 in ideas; memory reflects the new canon. → PR
(may fold into P3's close-out).

## 4. ▶ Execute prompt
> Paste into a fresh Skynet session to run this directive. Swap `<N>` for the phase to run.
```
Read planning/projects/SKY-001-system-design-constitution-and-spokes.md and execute Phase <N>.
Follow AGENTS.md: plan loudly then run quietly, never merge your own PRs, request the
narrowest host / shortest grant the phase needs, and checkpoint at the listed human/grant
steps. When the phase's exit criteria are met, do the "Phase close-out" at the bottom.
```

## 5. Phase close-out (resume material)
Run this every time a phase finishes successfully — it's what makes the next session cold-startable:
- [ ] Land the work via **PR** (agent never merges its own).
- [ ] Write/refresh a memory `SKY-001-progress` (what shipped, what's next, gotchas) + a MEMORY.md pointer.
- [ ] Bump this file's frontmatter (`current_phase`, `status`, `updated`) and flip the phase box to `[x]`.
- [ ] `bin/plan list` to refresh the roadmap index.
- [ ] Paste the **Continue prompt** below to resume in a fresh session:
```
Continue planning/projects/SKY-001-system-design-constitution-and-spokes.md at Phase <N+1>.
Prereqs carried from the last phase: <…>. Resume context from memory [[SKY-001-progress]].
Follow AGENTS.md as above.
```

## 6. Status log
- 2026-08-16 — created (in-progress). Born from the post-graduation question "what's the fate of
  the deployment plan?" Decided: retire it whole, author a constitution + spokes system design
  built for expansion (sci-fi flavor kept). Full approved plan lives in the session that minted
  this. P1 executing: renumbered the misfiled PBS directive to SKY-002. See [[skynet-a6-next]].
- 2026-08-16 — **P1 merged** (PR #32): renumber + directive minted. **P2 done** (this PR): authored
  `docs/system-design.md` (constitution) + 6 spokes under `docs/design/` + `docs/history/build-log.md`;
  bannered the old plan "SUPERSEDED". Additive — old plan still present; all internal links resolve.
  Next: P3 (`git mv` plan → `history/`, re-point the 7 refs, reword the merge/tiebreaker contract).
- 2026-08-16 — **P3 done** (this PR): `git mv docs/deployment-plan.md → docs/history/deployment-plan-v5.md`
  (frozen, banner flipped to ARCHIVED). Re-pointed **every** live reference — turned out to be more
  than 7 files (AGENTS.md ×4, CLAUDE.md, README.md ×3, docs/architecture.md, docs/backup-strategy.md,
  planning/{README,TEMPLATE,projects/README}, runbooks/README.md, ca/README.md → the access-and-trust
  spoke, SKY-002). Reworded the tiebreaker ("the plan wins" → "the design wins") and **AGENTS.md §6**'s
  flat "never merges its own" → the merge-dial framing; de-hardcoded "two pools" → "the set (two today)".
  Grep-verified: no live pointer to the old path, no "plan wins", zero broken links repo-wide.
  Next: P4 close-out.
- 2026-08-16 — **P4 done — SKY-001 COMPLETE.** Archived this directive to `planning/archive/`
  (status → done); regenerated the roadmap; re-pointed the steady-state memory [[skynet-a6-next]]
  and [[SKY-001-progress]] at `docs/system-design.md`. The deployment plan is retired; Skynet's
  living design is the constitution + spokes. Skynet has finished defining itself. 🤖
