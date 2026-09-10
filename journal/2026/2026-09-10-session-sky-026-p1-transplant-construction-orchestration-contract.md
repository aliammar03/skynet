---
date: 2026-09-10
time: 16:51:30            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: SKY-026 P1 transplant construction orchestration contract
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-026, SKY-022, SKY-025]
thread_status: open     # none | open | resolved | unknown; digest shows only explicit open
---

# 2026-09-10 · session · SKY-026 P1 transplant construction orchestration contract

<!-- RAW EPISODE. -->

## What happened
Executed SKY-026 Phase 1 (Transplant the orchestration contract). Re-read the pinned donor
`viettran-edgeAI/codex_workflow@6d9b06f73bee7f899001b0bb102c70529a24313f`. The raw doctrine files
sit under `codex_workflow/` (not the repo root) — `AGENTS.md`, `heavy_route.md`, `medium_route.md`,
`archivist.md`. WebFetch's summarizer 404'd the root paths and then refused `heavy_route.md`
(misfired "internal Anthropic doc" heuristic), so I pulled raw content via
`gh api repos/.../contents/codex_workflow/<f>?ref=<sha> --jq .content | base64 -d`. Donor deltas
vs the directive's decisions: none material — Decisions C/D/F/G/H/I/J and the Main boundary already
match donor `heavy_route.md`/`medium_route.md`/`archivist.md` verbatim in intent. The agent TOMLs and
`deployment-token-report` skill are Phase 2/4 surfaces, not read this phase.

Rewrote `docs/conventions/construction.md` from the SKY-022 lead+≤2-helper model to the SKY-026
Main-directed swarm: Light/Medium/Heavy routes, Main-as-decision-owner boundary, the six roles with
Skynet model/effort/sandbox defaults, Direct/Companion/Investigator context routing, Task-ID capsules,
batching, the Executor→Tester→Executor repair loop, no-workflow-cap concurrency (semantic limits only),
fresh-session review that returns a paste-ready fix prompt instead of repairing, and the Skynet
continuity map (no `agent_docs/` — system-design/directive/journal/generated own the facts).

Migrated the other authoritative present-behavior surfaces: `AGENTS.md` §4 construction paragraph,
`docs/conventions.md` hub (invariant line + spoke row), `docs/system-design.md` constitution line 110,
and `runbooks/construction-delegation.md` (kept required frontmatter/sections; re-rendered
`runbooks/README.md` via `render-runbook-catalog.sh`). Regenerated `docs/generated/07-context-map.md`
via `render-context-map.sh`. Migrated SKY-025's three optional-worker phase notes off Scout/
Builder/"at most two helpers" vocabulary onto Investigator/Default Executor + non-overlapping ownership.

## Actions & outcomes
- Rewrote construction.md around donor semantics → one canonical current construction doctrine.
- AGENTS.md / conventions.md / system-design.md / runbook migrated off lead+two-helper wording → done.
- `render-runbook-catalog.sh` + `render-context-map.sh` re-rendered generated outputs (not hand-edited).
- SKY-025 optional-worker notes migrated to SKY-026 roles.
- Gates: check-invariants OK; construction-test 8/0; documentation-drift 8/0; agent-test 84/0;
  provisioning-truth 12/0; digest-test 11/0; gitignore 3/0. All green.

## Graveyard — tried & abandoned
- WebFetch on donor raw files → abandoned: root-path 404 (files live under `codex_workflow/`), and
  its summarizer refused verbatim reproduction of `heavy_route.md`. Used `gh api` blob decode instead.
- Rewriting SKY-025's whole inline execution-model block (Terra/Sol/Astra "leads", "at most two
  active workers") in P1 → deferred: that is a sibling directive's self-imposed framing and the
  directive's exhaustive migrate/delete sweep is explicitly Phase 5 (§4 P5 step 4). Only the clearly
  construction-vocabulary optional-worker notes were migrated now.
- Adding a new deterministic assertion for role vocabulary in P1 → not added: the runtime surface
  (`.codex/agents/*`, `.codex/config.toml`, `invariants.json`, tests) is still the SKY-022 set until
  Phase 2, so any role/cap assertion now would be inconsistent. Machine enforcement lands with the
  config swap in Phase 2 (P1 step 7 = "only rules the machine can actually prove").

## Follow-ups / open threads
- Phase 2 owns the runtime swap: replace `.codex/agents/{builder,mechanic,scout}.toml` with the six
  SKY-026 roles, remove `max_concurrent_threads_per_session` doctrine cap, adapt `bin/agent`, and
  update `construction-test.sh`/`agent-test.sh`/`invariants.json` to match. Until then, construction.md
  (doctrine) intentionally leads the `.codex/*` wiring.
- Phase 5 owns the exhaustive sweep: SKY-025 §"Execution and review" inline model (lines ~76–133,
  execution-lead/two-worker/Astra framing) still uses the old vocabulary and must be migrated then.
- construction-test.sh / agent-test.sh header comments still name SKY-022 as provenance (descriptive,
  not authority) — clean up when those tests are rewritten in Phase 2.
