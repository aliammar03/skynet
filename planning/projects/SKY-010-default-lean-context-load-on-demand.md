---
id: SKY-010
title: Default-lean context — strip the baseline, load on demand
status: in-progress
horizon: short
created: 2026-08-17
updated: 2026-08-18
phases: 4
current_phase: 3
tier_touched: [T1]     # repo files + read-only greps on the ops VM. No blast radius; no PR to system-design.
related:
  - docs/design/memory.md
  - docs/decisions/0003-ambiguity-layering-and-format-follows-enforcement.md  # the retrieval pipe between machine-enforced and prose layers
  - docs/conventions/docs.md
  - docs/generated/06-agent-digest.md
  - AGENTS.md
  - runbooks/README.md
  - planning/scratchpad/research/2026-08-17-reactive-memory.md
  - planning/projects/SKY-006-agent-episodic-memory-journal-retrieval.md
  - "[[SKY-010-progress]]"
---

# SKY-010 · Default-lean context: strip the baseline, load on demand

> Make **nothing** enter the agent's context until a task actually needs it. Drive the always-loaded
> baseline down to the smallest high-signal set, and put everything else behind a **trigger + a
> reliable retrieval path**: a budget-tagged map of what's loadable and what it costs, and a
> read-time scout that does wide reads in a throwaway window. Working memory holds conclusions, not
> the corpus.

## 1. Problem / motivation
Skynet is stateless — every session rebuilds from git — so the context window is the scarce
resource. The governing principle (Anthropic's context-engineering guidance, confirmed by the
context-rot research): load the **smallest possible set of high-signal tokens**, and pull everything
else **just-in-time**. This isn't only economy — **irrelevant tokens actively degrade accuracy**:
every one draws from a finite attention budget and buries the decision-critical evidence, so all 18
top models tested got *worse* as input grew. Unnecessary context is a correctness bug, not just a
cost.

Skynet is already partway there (procedures, runbooks, journal are on-demand by design), but nothing
has *audited* what still auto-loads, and the just-in-time path is manual and blind:

| Symptom | Today | Cost |
|---|---|---|
| **Un-audited baseline** | no inventory of what enters context by default; assumed "lean enough" | can't prune what isn't measured |
| **Routing tax** | to pick *one* runbook the agent loads the *entire* catalog | ~1.5K tokens to choose, every time |
| **Blind budgeting** | no file declares its token weight; "retrieve sparingly" is vibes | the agent can't cost a load before making it |
| **Wide reads eat working memory** | "what did we try with CT 240?" ⇒ grep + read many episodes *into the main window* | 5–40K of raw pulled in, then mostly discarded |

The whole repo is only ~116K tokens (measured), so **the goal isn't shrinking a huge pile — it's
default-nothing:** a tiny baseline, and a trigger + retrieval path for everything else. This is the
cheap layer that precedes SKY-006 P3's semantic index — and may push its "overkill line" out far
enough that the vector index is never needed.

## 2. Approach — what we're building

**The rule — default-lean.** Nothing auto-loads unless a trigger fires. The always-loaded set is
audited down to the minimal contract; every other artifact is reachable only on demand, and moving
something off the baseline is *only* safe once it has a reliable retrieval path (the map, below).

**The map — a generated context manifest.** One machine-owned page under `docs/generated/` listing
every loadable artifact: path · one-line abstract · tier · trigger · ~token cost. The agent reads
*that* (~2–3K for the whole lab) and opens only the exact file it needs — instead of loading a whole
prose catalog to route. It's the digest doctrine (`06-agent-digest.md`) extended from "what happened"
to "what can I load and what does it cost." Regenerable ⇒ never drifts.

**The metadata — budget frontmatter.** Loadables carry `summary:` (one authored line) + optional
`trigger:`; a script computes `tokens:` (**generated, never hand-set** — it drifts). This makes
"retrieve sparingly" a *number*, feeds the map for free, and lets the audit rank baseline offenders.

**The scout — read-time distillation in a throwaway window.** For a *wide* question, a subagent greps
+ reads in its *own* context and returns only the ~500-token conclusion; the raw stays on disk, the
main window holds just the answer. This is read-time summarization (per ADR 0002) relocated off the
critical window — nothing is ever persisted. Because subagents are engine-specific and Skynet is
vendor-neutral, pair it with a scripted `bin/recall <topic>` (greps journal + docs, prints hits) that
any engine runs and a Claude scout can call internally. Same capability, degrades gracefully.

## 3. The plan
- **Scope / non-goals:** a baseline audit + default-lean doctrine; budget frontmatter + cost script;
  a generated context-map manifest; a read-time scout capability (`bin/recall`). **Non-goals:** any
  persisted/pre-baked summaries (banned by ADR 0002); the `sqlite-vec` semantic index (SKY-006 P3 —
  this directive aims to *defer* it); gutting the `AGENTS.md` contract below what every session
  genuinely needs (lean ≠ unsafe — the Judgement Day invariants stay always-loaded); promoting
  runbooks to executable capabilities (a sibling idea, noted in §6).
- **Hosts & tiers touched:** ops VM only, repo files + read-only greps. **T1**, no blast radius —
  **no PR to `docs/system-design.md`** required.
- **Rollback posture:** fully additive/reversible. `git revert`; the manifest is generated
  (disposable, rebuildable); `bin/recall` is read-only; baseline prunes are content moves, not deletes.
- **Grants / human actions:** none. Lands via PR like everything else (agent never merges its own).

### Phase 1 — baseline audit + default-lean doctrine  (~1–2h)   `[x]` done
Find and remove everything that auto-loads without earning it.
Steps:
1. **Inventory** what enters context by default: `CLAUDE.md` → `AGENTS.md` import, the mandated
   cold-boot reads (`06-agent-digest.md`), and any other always-on pointer. Measure each in tokens.
2. **Classify** every block as *always-needed* (the contract: trust tiers, Judgement Day invariants,
   plan-loudly/run-quietly) vs *on-demand-able* (reference detail, examples, catalogs). Anything
   on-demand-able moves behind a trigger — but only mark it "movable" now; it's not safe to relocate
   until Phase 3 gives it a retrieval path.
3. **Expand `docs/design/memory.md` — don't rewrite it.** The spoke is sound but episodic-heavy
   (SKY-006 authored it); its working-memory side is a single table cell. Add a first-class
   **working-memory discipline / default-lean** section — *nothing auto-loads unless a trigger fires;
   the always-loaded set is the minimal high-signal contract; irrelevant context is a correctness
   bug, not just cost* — and **rebalance the intro** so working-memory discipline reads as a peer to
   the episodic layer. **Leave §1 journal / §2 ADRs / §3 retrieval / the invariants / the loop / the
   boundary intact** — they're load-bearing and still true. Tag the new doctrine `[manual]` pending
   the lint gate. Do the *trivially safe* prunes now (dead pointers, duplicated prose).

Exit criteria: a measured inventory of the default-loaded set exists; each block is tagged
always/on-demand; the default-lean principle is documented; safe prunes landed.
Grants / human actions: none.

### Phase 2 — budget frontmatter + cost script  (~1–2h)   `[x]` done
Give every loadable a declared abstract and a computed token weight (so the audit + map have numbers).
Steps:
1. Add to the docs convention (`docs/conventions/docs.md`, the authoritative home): loadable `.md`
   artifacts carry `summary:` (one line) + optional `trigger:`; `tokens:` is **generated, never
   hand-authored**. Tag `[testable]` for the parked lint gate.
2. Write `scripts/budget-frontmatter.sh` — read-only, idempotent, content-stable: computes an approx
   token count per file (bytes/4 heuristic, documented) and reports/refreshes a `tokens:` field.
   Engine-neutral (matches the `render-*.sh` house style).
3. Backfill `summary:` on high-traffic loadables (runbooks, design spokes, generated docs); legacy
   files without one fall back to their first `# heading` so none is invisible.

Exit criteria: the script writes a per-file token weight; the convention documents
`summary`/`trigger`/generated-`tokens`; high-traffic files carry a `summary:`.
Grants / human actions: none.

### Phase 3 — the context-map manifest  (~1–2h)   `[x]` done
Build the on-demand index — the retrieval path that makes moving things off the baseline safe.
Steps:
1. Write `scripts/render-context-map.sh` (twin of `render-digest.sh`): walk the loadable dirs
   (`runbooks/`, `docs/design/`, `docs/conventions/`, `docs/generated/`, `journal/`, `templates/`),
   emit `docs/generated/07-context-map.md` — one row per artifact: path · summary · tier · trigger ·
   ~tokens. Content-stable + idempotent so it diffs only on real change.
2. Wire it into **both** nightly paths (`scripts/nightly.sh` + `bin/ops`/`runbooks/nightly.md`)
   alongside `render-digest.sh`, so the map stays fresh LLM-free.
3. Point the cold-boot flow at it (`AGENTS.md §4`, `06-agent-digest.md`): "for *what to load and what
   it costs*, see the context map." **Then relocate** the Phase-1 "on-demand-able" blocks off the
   baseline into their own triggered files, now that the map can surface them.

Exit criteria: `07-context-map.md` regenerates deterministically, lists every loadable with a token
cost, refreshes on the nightly, is referenced from cold-boot pointers; the Phase-1 movable blocks are
off the baseline and reachable via the map.
Grants / human actions: none. (`docs/generated/` is machine-owned — edit the renderer, never output.)

### Phase 4 — the read-time scout  (~1–2h)   `[ ]` not started
Move wide reads off the main window.
Steps:
1. Write `bin/recall <topic>` — read-only: greps `journal/` + docs, prints ranked file hits with
   their `summary:` line and token cost (leans on Phase 2 metadata). Vendor-neutral.
2. **Extend** `docs/design/memory.md` (add to §1's write-raw rule / the new working-memory section —
   don't rewrite): for a *wide* question, dispatch a **read-time scout** (a subagent where available;
   else `bin/recall` + targeted reads) that distills in a throwaway context and returns only the
   conclusion. **Persisting a scout's summary is forbidden** (ADR 0002) — the raw stays the source;
   the summary lives for one query.
3. Seed a journal `session` entry demonstrating the scout answering a real "what did we try with X?"

Exit criteria: `bin/recall <topic>` surfaces relevant episodes/docs with costs; the memory spoke
documents the read-time-scout pattern and its "never persist the summary" guardrail.
Grants / human actions: none.

## 4. ▶ Execute prompt
> Paste into a fresh Skynet session to run this directive. Swap `<N>` for the phase to run.
```
Read planning/projects/SKY-010-default-lean-context-load-on-demand.md and execute Phase <N>.
Follow AGENTS.md: plan loudly then run quietly, never merge your own PRs, request the
narrowest host / shortest grant the phase needs, and checkpoint at the listed human/grant
steps. When the phase's exit criteria are met, do the "Phase close-out" at the bottom.
```

## 5. Phase close-out (resume material)
Run this every time a phase finishes successfully — it's what makes the next session cold-startable:
- [ ] Land the work via **PR** (agent never merges its own).
- [ ] Write/refresh a memory `SKY-010-progress` (what shipped, what's next, gotchas) + a MEMORY.md pointer.
- [ ] Bump this file's frontmatter (`current_phase`, `status`, `updated`) and flip the phase box to `[x]`.
- [ ] `bin/plan list` to refresh the roadmap index.
- [ ] Paste the **Continue prompt** below to resume in a fresh session:
```
Continue planning/projects/SKY-010-default-lean-context-load-on-demand.md at Phase <N+1>.
Prereqs carried from the last phase: <…>. Resume context from memory [[SKY-010-progress]].
Follow AGENTS.md as above.
```

## 6. Status log
*(One dated line per milestone — cite PR numbers; convert relative dates to absolute. Newest last.)*
- 2026-08-17 — created (draft) from a session on context/token footprint. Measured the lab:
  always-loaded ≈ 2.3K tokens, whole repo ≈ 116K. Reframed around **default-lean**: the goal is
  *default-nothing* — a minimal baseline + a trigger & retrieval path for everything else — grounded
  in the context-rot finding that irrelevant tokens degrade *accuracy*, not just cost. Precedes (and
  may obviate) SKY-006 P3's semantic index. Sibling idea: promoting deterministic runbooks to
  executable capabilities (kills procedural read cost) — worth its own SKY-###.
- 2026-08-17 — promoted to **projects/** (active, fully phased). Ready to execute from Phase 1.
- 2026-08-18 — **Phase 1 done.** Measured the default-loaded baseline (bytes/4): always-loaded ≈ 2.3K
  (`CLAUDE.md` 213 + `AGENTS.md` 2090), cold-boot `06-agent-digest.md` 946, whole repo ≈ 115.6K.
  Classified each block always/movable (`AGENTS.md` §4 deploy-detail + §5 planning-detail marked
  *movable*, relocation deferred to P3; Judgement Day invariants stay always-loaded). Documented the
  **default-lean discipline** as a first-class `[manual]` section in `docs/design/memory.md` (peer to
  the episodic layer) with the audited-baseline table; rebalanced the intro + four-kinds "Working"
  row. No forced prunes — baseline is link-clean. Progress: memory `[[SKY-010-progress]]`. PR #52 (merged).
- 2026-08-18 — **Phase 2 done.** Added `scripts/budget-frontmatter.sh` — read-only, idempotent,
  content-stable; ~tokens = content-bytes/4 (the file's own `tokens:` line excluded ⇒ the value
  converges), refreshes a **generated** `tokens:` field, and `--check` fails CI on stale tokens or a
  missing summary. Documented the `summary`/`trigger`/generated-`tokens` schema in
  `docs/conventions/docs.md` (the authoritative home) `[testable]`. Backfilled authored `summary:`
  (+ `trigger:` on runbooks) across the 27-file on-demand corpus (design + conventions spokes,
  runbooks + dr). Corpus ≈ 27.1K tok; always-loaded baseline reconfirmed at 2303. Also regenerated the
  roadmap (the #51/#52 merge had dropped SKY-011's row). Progress: memory `[[SKY-010-progress]]`. PR #53 (merged).
- 2026-08-18 — **Phase 3 done.** Added `scripts/render-context-map.sh` (twin of `render-digest.sh`):
  deterministic, content-stable, ~tokens computed at render time (self-fresh; never edits an authored
  file). Emits `docs/generated/07-context-map.md` — one row per on-demand artifact (path · tier ·
  trigger · ~tokens · summary) across runbooks, design + conventions spokes, catalogs, generated
  views, plus an episodic pointer (journal is retrieved by topic, not browsed). Wired into **both**
  nightly paths (`scripts/nightly.sh` + `bin/ops` engine prompt + `runbooks/nightly.md`). Pointed the
  cold-boot flow at it (`AGENTS.md` cold-boot bullet + the digest footer). **Relocated** the P1 movable
  blocks off the baseline: `AGENTS.md` §4 loop-mechanics → gitops-loop/secrets, §5 planning-lifecycle
  → planning/README.md (detail already lived there — pure de-dup + a pointer). **Baseline 2303 → 2223
  tok (−80)** with the detail now trigger-loaded. Progress: memory `[[SKY-010-progress]]`. PR: _pending_.
