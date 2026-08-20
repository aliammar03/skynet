---
id: SKY-005
title: Imperative ops discipline: recon toolkit, diagnosis library, lab bench
status: in-progress
horizon: short
created: 2026-08-17
updated: 2026-08-20
phases: 3
current_phase: 1
tier_touched: [T1, T2, T2+]   # recon is T1; diagnosis uses existing root grants (T2+); bench is
                              # the docker-dmz throwaway host (T2). No new blast radius.
related:
  - runbooks/README.md
  - docs/design/access-and-trust.md
  - planning/scratchpad/2026-08-17-declarative-future-and-agent-cognition.md
  - "[[skynet-service-standard]]"
  - "[[SKY-005-progress]]"
---

# SKY-005 · Imperative ops discipline: recon toolkit, diagnosis library, lab bench

> Make the *imperative* side of Skynet — exploration, diagnosis, fixing — a real discipline instead
> of improvised root grants, and enforce the principle **diagnose imperatively, fix declaratively.**

## 1. Problem / motivation
The declarative loop is polished; the imperative side is thin. Today "figure out why X is broken" is
runbooks + an ad-hoc root grant + improvised commands. Three concrete gaps:
- **No standard recon** — every investigation re-invents the same 20 commands, and even *looking*
  often reaches for a grant it doesn't need.
- **Diagnosis is improvised** — no triage library for the common failure classes, so quality depends
  on what the agent remembers that session.
- **Fixes risk becoming orphans** — an imperative one-off fix mutates a host and *creates drift* that
  nothing reconciles. The fix should route back through git wherever possible.

## 2. Brainstorm — options considered

**Recon**
- **Option A — improvise per incident.** Flexible, but slow and grant-hungry (you grab root just to
  look).
- **Option B — a standing read-only `scripts/recon.sh` (T1).** Emits one structured snapshot —
  services, unit states, recent logs, disk/mem/cpu, listening ports, recent config/pkg changes,
  container health — that the agent reasons over. Keeps *looking* inside T1.
- **Decision:** **Option B (CHOSEN).** Cheap "what's going on here" with no grant to observe.

**Diagnosis**
- **Option A — rigid decision-tree scripts.** Deterministic but brittle; real incidents don't fit
  the tree.
- **Option B — LLM-guided triage runbooks.** Each embeds the diagnostic commands + branches for a
  failure class (container crash-loop, disk full, cert expired, DNS fail, backup missed, Arcane
  stuck), but leaves judgement to the agent.
- **Decision:** **Option B (CHOSEN).** Extends the existing runbook model; the agent stays the brain.

**The fix principle**
- **Decision (CHOSEN): "diagnose imperatively, fix declaratively — no orphan fixes."** The root grant
  is for *understanding*; the fix is a PR to `compose/` / a nix module / a tofu resource whenever it
  can be. Emergency imperative fixes are *immediately reconciled back* into declared state. Candidate
  for promotion to a `docs/system-design.md` principle.

**Lab bench (safe reproduction)**
- **Option A — a dedicated scratch VM.** Clean, but a new guest to maintain.
- **Option B — reuse `vm-docker-dmz`** (memory-tagged throwaway / destructive-OK) as the bench, plus
  per-layer dry-runs (`tofu plan`, `nixos-rebuild dry-activate`, compose in a throwaway context).
- **Decision:** **Option B (CHOSEN).** "Try it on the bench, show the diff, then propose" becomes the
  default reflex. See [[skynet-service-standard]].

## 3. The plan
- **Scope / non-goals:** recon script, diagnosis runbooks, formalized bench, and the fix principle.
  **Non-goal:** automating the *fixes* themselves (that rides the autonomy ratchet / SKY-004).
- **Hosts & tiers touched:** ops VM + any host under investigation. Recon = T1. Diagnosis may use an
  existing per-host **T2+ root grant**. Bench = `vm-docker-dmz` (T2). No new blast radius.
- **Rollback posture:** all additive (scripts/runbooks); `git revert`. The bench is throwaway by design.
- **Grants / human actions:** normal narrowest-host/shortest-duration grants when a diagnosis needs root.

### Phase 1 — recon toolkit  (~1–2h)   `[x]` done (2026-08-20)
`scripts/recon.sh <host>` → one structured (JSON/markdown) snapshot; wire it into a "start here"
runbook. Exit: a single command yields a full host picture at T1, no grant to observe.
**Shipped:** `scripts/recon.sh` (Markdown snapshot, local or `svc-ops@` SSH, degrades where root
would reveal more — never requires a grant) + `runbooks/recon.md` (start-here triage, catalogued).

### Phase 2 — diagnosis library  (~1–2h)   `[ ]` not started
Triage runbooks for the top failure classes, each embedding diagnostic commands + decision branches
and ending in an incident record for the journal ([[SKY-006-progress]]). Exit: ≥4 failure classes
have a triage runbook.

### Phase 3 — lab bench + fix principle  (~1–2h)   `[ ]` not started
Formalize `vm-docker-dmz` as the bench + per-layer dry-run reflex; propose the "fix declaratively /
no orphan fixes" principle (optional `docs/system-design.md` PR). Exit: bench documented; principle
landed.

## 4. ▶ Execute prompt
```
Read planning/projects/SKY-005-imperative-ops-discipline-recon-toolkit-diagnosis-library-lab-bench.md and execute Phase <N>.
Follow AGENTS.md: plan loudly then run quietly, never merge your own PRs, request the
narrowest host / shortest grant the phase needs, and checkpoint at the listed human/grant
steps. When the phase's exit criteria are met, do the "Phase close-out" at the bottom.
```

## 5. Phase close-out (resume material)
- [ ] Land the work via **PR** (agent never merges its own).
- [ ] Write/refresh a memory `SKY-005-progress` (what shipped, what's next, gotchas) + a MEMORY.md pointer.
- [ ] Bump this file's frontmatter (`current_phase`, `status`, `updated`) and flip the phase box to `[x]`.
- [ ] `bin/plan list` to refresh the roadmap index.
- [ ] Paste the **Continue prompt** below to resume in a fresh session:
```
Continue planning/projects/SKY-005-imperative-ops-discipline-recon-toolkit-diagnosis-library-lab-bench.md at Phase <N+1>.
Prereqs carried from the last phase: <…>. Resume context from memory [[SKY-005-progress]].
Follow AGENTS.md as above.
```

## 6. Status log
- 2026-08-17 — created (draft) from the declarative-future brainstorm §2. The imperative side becomes
  a discipline; "diagnose imperatively, fix declaratively" is the through-line. Pairs with SKY-006 (incidents → journal).
