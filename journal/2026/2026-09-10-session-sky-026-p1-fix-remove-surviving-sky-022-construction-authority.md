---
date: 2026-09-10
time: 18:20:00            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: SKY-026 P1 fix — remove surviving SKY-022 construction authority
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-026, SKY-025, PR #241]
thread_status: resolved     # none | open | resolved | unknown; digest shows only explicit open
resolves: [2026-09-10-session-sky-026-p1-transplant-construction-orchestration-contract]
---

# 2026-09-10 · session · SKY-026 P1 fix — remove surviving SKY-022 construction authority

<!-- RAW EPISODE. -->

## What happened
Independent fresh-session review of merged SKY-026 P1 (PR #241, merge 5035f44) returned FIX: P1 had
migrated the canonical doctrine (construction.md/AGENTS.md/conventions.md/system-design.md/runbook)
but left four current-authority surfaces still carrying the SKY-022 lead+two-helper / reviewer-repairs
model. I had wrongly deferred the SKY-025 prompt/directive migration to Phase 5 — but SKY-025's
execute/review prompts are *live* construction authority today, so the review was right that they
belong to P1's "current prompts supplying present behavior" scope.

Fixed from a fresh branch off current main (`fix/sky-026-p1-remove-surviving-sky-022-authority`):
- `runbooks/construction-delegation.md`: dropped the mandatory BIV eligibility gate and the
  lead-verifies-everything model. Now: Main owns architecture/decomposition/contracts/integration/
  acceptance/PR; Heavy Executors own production+ordinary repair; Testers independently design/run
  verification; Main evaluates returned evidence in Heavy (runs checks itself only in Light/Medium);
  dependent packages may be delegated sequentially when ownership is clear. Re-rendered the catalog.
- `planning/prompts/execute.md`: removed "at most two scoped Luna workers"; routes workers/capsules/
  ownership/batching/verification through construction.md; phase-table model stays a Main recommendation.
- `planning/prompts/review.md`: rewritten to the SKY-026 review model — reviewer never modifies the
  implementation and authors no repair commits. ACCEPT/BLOCKED publish a review PR; FIX emits ONLY one
  fenced paste-ready fix prompt to the original session, which lands a bounded fix PR, then fresh
  re-review until ACCEPT. Dropped the "Reviewer repairs" PR field and the Luna/two-helper repair scheme.
- `planning/prompts/README.md`: aligned the lifecycle bullets + table row (no reviewer repairs).
- SKY-025 directive §3 (was "Phase-specific leads and Luna workers") now "Main model recommendations":
  delegates route/role/capsule/batching/repair to construction.md, keeps only per-phase Main model recs
  (Terra High default / Sol Low rendering / Astra Medium foundational) + escalation + verify-identifiers.
  §4 review gate rewritten to the paste-ready-fix-prompt model; "execution lead" → "Main"; phase-table
  header "Execution lead" → "Recommended Main"; §8 FIX-vs-ACCEPT PR handling corrected.

Left untouched by design: SKY-025 status-log entries (≥ line 388) recording the *historical* P5/P6
"ACCEPT with reviewer repairs" — those are append-only records of what actually happened under the old
model, not current authority. Also left `.codex/agents/*`, `.codex/config.toml`, `bin/agent`,
`invariants.json`, `construction-test.sh`, `agent-test.sh` — the runtime surface is Phase 2 and its
declared-cap/sandbox mismatch is the intentionally-deferred P2 gap, not a P1 defect.

## Actions & outcomes
- Rewrote runbook + prompts + SKY-025 §3/§4/§5/§8 → one current orchestration authority (construction.md).
- Residual scan (current surfaces, pre-status-log) for "at most two"/Luna Med-High/reviewer-repairs/BIV → CLEAN.
- Gates: check-invariants OK; construction-test 8/0; documentation-drift 8/0; agent-test 84/0;
  provisioning-truth 12/0; digest-test 11/0; gitignore 3/0; `git diff --check` OK.

## Graveyard — tried & abandoned
- Editing SKY-025 status-log P5/P6 "reviewer repairs" entries to match the new model → abandoned:
  that is history, not current authority; the review explicitly forbade rewriting it.
- Including the pre-existing `planning/README.md` roadmap re-render in this PR → abandoned: it is not
  mine and carries unrelated horizon flips (SKY-010/011/024 long→short); kept out of the fix PR.

## Follow-ups / open threads
- Phase 2 still owns the runtime swap (six role TOMLs, drop the `max_concurrent_threads_per_session`
  cap, adapt `bin/agent` + `construction-test.sh`/`agent-test.sh`/`invariants.json`). Until then the
  declared-cap/sandbox invariant intentionally still reflects the SKY-022 runtime — deferred, not a defect.
- Phase 5 still owns the whole-repo exhaustive sweep and end-to-end dogfood.
