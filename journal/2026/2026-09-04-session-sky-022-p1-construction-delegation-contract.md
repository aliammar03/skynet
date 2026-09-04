---
date: 2026-09-04
kind: session          # session | incident | decision
title: SKY-022 P1 construction delegation contract
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-022, "PR #172"]
---

# 2026-09-04 · session · SKY-022 P1 construction delegation contract

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (SKY-006 / journal/README.md). Distillation happens at READ time, never here. -->

## What happened
Executed SKY-022 Phase 1 (Role contract + tiny launcher). Ali added "research online too btw"
mid-turn, so I stopped guessing at the model tiers and actually looked them up — which turned out
to matter a lot.

Two research findings changed the shape of the deliverable:
1. **Terra/Sol/Luna are not codenames I had to invent — they're the real GPT-5.6 tiers.** Sol =
   flagship (hardest problems), Terra = balanced workhorse, Luna = fast/cheap for repeatable
   objective-check work. OpenAI's own subagent docs show `model = "gpt-5.6-terra"`. So the roles→tier
   table in the directive maps 1:1 onto real model IDs, and `bin/agent` defaults to `gpt-5.6-{sol,terra,luna}`.
2. **Codex already has native subagents** (GA March 2026): project-scoped `.codex/agents/*.toml`
   defs (`model`, `model_reasoning_effort`, `sandbox_mode` incl. `read-only`) + an `[agents]` block
   in `config.toml` with `max_concurrent_threads_per_session`. That is EXACTLY SKY-022's Decision E
   ("native tooling first"). So instead of only writing a `bin/agent` wrapper, I made the native
   config the primary mechanism and the wrapper the standalone mirror.

The nice consequence: two of SKY-022's rules stopped being "hold by vigilance" and became mechanical.
The ≤2-helper cap is `max_concurrent_threads_per_session = 2`. The scout's no-write contract is
`sandbox_mode = "read-only"`. Neither depends on an agent remembering the doctrine.

Also confirmed the Phase-6 target is real: Codex App Server exposes `thread/start` / `thread/resume`
/ `thread/fork` / `turn/start` / `turn/interrupt` over JSON-RPC (stdio), TS schema via
`codex app-server generate-ts`, no official TS SDK. Recorded that in the progress memory so P6
doesn't re-research it.

## Actions & outcomes
- research (WebSearch/WebFetch) → GPT-5.6 tier lineup + Codex native-subagent config surface + App Server methods, all pinned in [[SKY-022-progress]].
- `docs/conventions/construction.md` (new spoke) → roles table, BIV test, depth=1, ≤2 helpers, scout read-only, build-time trust boundary, complexity-must-be-earned. Wired into conventions hub (invariant + spoke row) + layout spoke.
- `.codex/config.toml` + `.codex/agents/{builder,mechanic,scout}.toml` → native mechanism; caps + read-only scout enforced by the platform.
- `bin/agent` (new, chmod +x) → role→tier→model launcher, `--dry-run`, writers `workspace-write`/scout `read-only`. Smoke-tested all four roles + `--hard` + guard rejections.
- `scripts/check-invariants.sh` → OK (green).
- Directive frontmatter → `current_phase: 1`, `status: in-progress`, P1 box flipped `[x]`. PR #172 opened against main (not self-merged).

## Graveyard — tried & abandoned
- Considered making `bin/agent` engine-agnostic (codex|claude switch, like `bin/ops`) → abandoned: construction delegation rides Codex's native subagents; a second engine path is complexity Phase 1 doesn't require. Kept it codex-focused, noted the contract itself is engine-neutral.
- Considered a single canonical role→model map to satisfy "one home per rule" → decided the doctrine spoke is the one *stated* home, and the native TOMLs + `bin/agent` are two *implementations* of it (same pattern as scripts.md ↔ bin/ops). Not a duplicate home.
- Did NOT add `.agent/` to `.gitignore` → that's a Phase 3 step; keeping phase boundaries clean.

## Follow-ups / open threads
- Phase 2: run native lead-driven delegation on one real T1 task with ≥2 subtasks (one scout + one builder/mechanic), integrate, own the PR.
- `gpt-5.6-{sol,terra,luna}` model IDs are my defaults from research — confirm they match whatever `codex` build is actually installed on the ops VM before a real (non-dry-run) `bin/agent` launch; override via `AGENT_MODEL_*` if not.
- Directive still lives in `planning/ideas/` while executing — leaving lifecycle move (ideas→projects) to Ali/`bin/plan`.
