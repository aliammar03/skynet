---
id: SKY-009
title: Convention bedrock: doctrine spine and golden templates
status: done
horizon: short
created: 2026-08-17
updated: 2026-08-17
phases: 2
current_phase: 2
tier_touched: [T1]
related:
  - docs/system-design.md
  - docs/conventions.md
  - planning/scratchpad/2026-08-17-lint-gate-convention-enforcement.md
  - "[[SKY-009-progress]]"
---

# SKY-009 · Convention bedrock: doctrine spine and golden templates

> Make conventions *bedrock*: one authoritative definition, and every new artifact minted
> already conforming — so nothing hand-written can drift from the house style.

## 1. Problem / motivation
Conventions are the thing everything else flows from, but today they live in three places and
half of them are unwritten: `docs/conventions.md` (terse rules), `AGENTS.md` (contract), and
plain habit that only holds because the same agent keeps applying it by hand. Nothing makes a
*new* service, script, runbook, or ADR inherit the rules — it relies on the author remembering.
That's fragile at exactly the layer we most want to be bedrock.

## 2. Brainstorm — options considered
**How conventions are encoded and propagated** (the real axis):
- **Style A — Doctrine spine:** one authoritative prose definition; enforce by PR review.
  Cheapest, most flexible, weakest guarantee (drift caught only if a reviewer looks).
- **Style B — Golden templates + scaffolding:** convention lives in reference artifacts + a
  generator; new stuff is *born correct*. Doesn't catch edits to existing files.
- **Style C — Executable contract (lint + CI gate):** rules become `bin/lint` + pre-commit/CI;
  PRs go red on drift. Strongest guarantee, highest cost, some friction.
- **Decision:** build toward the **layered set — A defines, B mints, C guards (CHOSEN)** — but
  ship **A+B now** and **park C**. A+B already makes new work born-correct and gives one
  definition; C only pays off once the rules are written and stable, and asserts those same
  rules. Building C against rules still in flux would hard-code churn.
  → C is parked in `planning/scratchpad/2026-08-17-lint-gate-convention-enforcement.md`
  (full design + wiring facts); revive as a follow-on once A+B land.

**Where the doctrine lives:**
- **Option A —** keep expanding the single `docs/conventions.md`. Simple, but grows unwieldy.
- **Option B —** hub + spokes: `conventions.md` shrinks to an index + invariant rules, depth
  moves to `docs/conventions/*.md`.
- **Decision:** chose **hub + spokes (CHOSEN)** — mirrors the constitution ↔ `docs/design/`
  pattern already in use; consistent, and itself a convention-about-conventions. (Confirm in P1.)

**`bin/new` placement:** own binary vs subcommand of `bin/ops` — **defer to P2**, decide when
scaffolding lands.

## 3. The plan
- **Scope / non-goals:** IN — write the authoritative convention set (A) and template+scaffold
  new artifacts from it (B). OUT — the lint/CI gate (parked, Style C); rewriting existing
  services/scripts wholesale (a future backfill belongs with C, not here).
- **Hosts & tiers touched:** none — repo-only, docs + `bin/`. **T1.** No trust-tier or
  blast-radius change, so no invariant rewrite in `docs/system-design.md` — only a pointer /
  extension-point note to the new conventions hub.
- **Rollback posture:** `git revert` the phase PR; templates + `bin/new` are additive.
- **Grants / human actions:** none beyond the standard PR merge (Ali merges; agent never does).

### Phase 1 — Doctrine spine (A)  (~1–2h)   `[x]` done
Steps:
1. Audit de-facto conventions across `compose/`, `scripts/`, `bin/`, `runbooks/`, `docs/`,
   `planning/`; list every rule already followed by hand and every ambiguity.
2. Resolve ambiguities into canonical answers (e.g. single-vs-split env, volume-path rules,
   branch-name grammar, frontmatter schemas per artifact type).
3. Restructure into hub + spokes: shrink `docs/conventions.md` to index + invariant rules;
   write `docs/conventions/{naming,layout,scripts,compose,git,docs,metadata}.md`.
4. Tag each rule **testable / not-testable** (so the parked lint gate can pick it up verbatim).
5. Add pointers from `docs/system-design.md` (extension point) and `AGENTS.md`.

Exit criteria: every current convention is written down in exactly one authoritative place;
ambiguities have a CHOSEN answer; hub links all spokes; `system-design.md` + `AGENTS.md` point in.
Grants / human actions: none beyond PR merge.

### Phase 2 — Golden templates + scaffolding (B)  (~1–2h)   `[x]` done
Steps:
1. Create `compose/_template/`, `scripts/_template.sh`, `runbooks/_template.md`,
   `docs/decisions/_template.md` — each embedding the P1 rules verbatim (directives already
   covered by `bin/plan`).
2. Write `bin/new <kind> <name>` that stamps the right skeleton (reuse `bin/plan` idioms:
   arg parsing, `REPO_DIR`, slug guarding — note the `/`-in-title sed bug from scratchpad).
3. Decide `bin/new` standalone vs `bin/ops` subcommand; document usage in the layout spoke.
4. Smoke-test: generate one of each kind, confirm it matches the doctrine.

Exit criteria: `bin/new service|script|runbook|adr <name>` produces a doctrine-conforming
skeleton for each type; usage documented; templates are the single source the generator reads.
Grants / human actions: none beyond PR merge.

## 4. ▶ Execute prompt
> Paste into a fresh Skynet session to run this directive. Swap `<N>` for the phase to run.
```
Read planning/projects/SKY-009-convention-bedrock-doctrine-spine-and-golden-templates.md and execute Phase <N>.
Follow AGENTS.md: plan loudly then run quietly, never merge your own PRs, request the
narrowest host / shortest grant the phase needs, and checkpoint at the listed human/grant
steps. When the phase's exit criteria are met, do the "Phase close-out" at the bottom.
```

## 5. Phase close-out (resume material)
Run this every time a phase finishes successfully — it's what makes the next session cold-startable:
- [ ] Land the work via **PR** (agent never merges its own).
- [ ] Write/refresh a memory `SKY-009-progress` (what shipped, what's next, gotchas) + a MEMORY.md pointer.
- [ ] Bump this file's frontmatter (`current_phase`, `status`, `updated`) and flip the phase box to `[x]`.
- [ ] `bin/plan list` to refresh the roadmap index.
- [ ] Paste the **Continue prompt** below to resume in a fresh session:
```
Continue planning/projects/SKY-009-convention-bedrock-doctrine-spine-and-golden-templates.md at Phase <N+1>.
Prereqs carried from the last phase: <…>. Resume context from memory [[SKY-009-progress]].
Follow AGENTS.md as above.
```

## 6. Status log
*(One dated line per milestone — cite PR numbers; convert relative dates to absolute. Newest last.)*
- 2026-08-17 — created (draft). Chose layered A→B→C; shipping A+B, parked C to scratchpad.
- 2026-08-17 — **Phase 1 done** (doctrine spine). `docs/conventions.md` restructured into a
  hub + 7 spokes (`docs/conventions/{naming,layout,scripts,compose,git,docs,metadata}.md`), every
  rule tagged testable/manual; `system-design.md` (§5 extension point + §7 spoke note) and
  `AGENTS.md` point in. Ambiguities resolved: **static addressing is now the standard for all
  guests** (ADR 0001 amended in place — file renamed `0001-static-ip-addressing.md`,
  `network.md` reconciled); doctrine set that **ADRs are always amended in place, never
  superseded**. Hub+spokes confirmed as the structure. Merged to main (rode a `bin/plan` title
  sed-escape fix along with it).
- 2026-08-17 — **Phase 2 done** (golden templates + scaffolding) — **directive complete**. All
  templates consolidated in **one folder `templates/`** (`compose/`, `script.sh`, `runbook.md`,
  `adr.md` + a README-as-catalog), each embedding the P1 spoke rules verbatim. `bin/new
  service|script|runbook|adr <name>` stamps a doctrine-conforming skeleton, reading `templates/`
  as the single source (reuses `bin/plan` idioms + the sed-escape helper; auto-numbers ADRs).
  **Decision:** `bin/new` is **standalone** (sibling of `bin/plan`), not a `bin/ops` subcommand —
  `bin/ops` is the engine runner, a different concern. Usage documented in the `layout` spoke.
  Style C (lint gate) remains parked.
