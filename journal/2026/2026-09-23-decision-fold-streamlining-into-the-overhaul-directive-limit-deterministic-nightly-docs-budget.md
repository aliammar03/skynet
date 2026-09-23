---
date: 2026-09-23
time: 18:25:44            # local HH:MM:SS; orders same-day episodes in the digest
kind: decision          # session | incident | decision
title: Fold streamlining into the overhaul: directive limit, deterministic nightly, docs budget
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-025, SKY-023, SKY-005, SKY-006, SKY-018, SKY-020, SKY-024, PR #260]  # SKY-###, PR #NNN, ADR NNNN, hosts — anything to cross-link
thread_status: none     # none | open | resolved | unknown; digest shows only explicit open
# resolves: [<episode-basename>, …]   # optional: close earlier episodes' open threads (append-only-safe)
---

# 2026-09-23 · decision · Fold streamlining into the overhaul: directive limit, deterministic nightly, docs budget

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (journal/README.md). Distillation happens at READ time, never here. -->

## What happened
After the process overhaul (PR #260), Ali asked for further streamlining and approved folding all of
it into the same PR. Findings that drove each change:

- 7 directives were `in-progress` at once. SKY-023 sat at 10/10 phases, its P10 never accepted; the
  only live residue was the `lxc-proof` identity on the production LXC bootstrap artifact (the
  `.codex/` and pre-commit residue it listed was already deleted by #260).
- The nightly routes through `bin/ops` (Codex primary, Claude fallback via `OPS_ENGINE*`) although the
  sequence itself is deterministic.
- Every committed inventory snapshot carries a `collected` timestamp, so every nightly produces a diff
  and a PR that needs a human merge.
- `scripts/hygiene.sh` current-authority budget (200k tokens) counted every non-history text file:
  `src/skynet/*.py`, `flake.lock`, compose YAML. Measured ~208k. Markdown alone: 237,324 bytes ≈ 59k
  tokens. `docs/history/` and `planning/` were already excluded (my earlier suggestion to delete
  history for budget reasons was wrong).
- The hygiene delta printf lines passed four args to a two-`%s` format, printing each line twice
  with swapped labels.
- 58 of 134 journal files were SKY-025/026 session logs from three weeks.
- `renovate.json` allowed 5 concurrent PRs, one per image.
- `AGENTS.md` §5, `planning/projects/README.md`, `docs/conventions/metadata.md` and `TEMPLATE.md`
  still described 1–2h phases, close-outs, Continue prompts and state-memory files (missed in #260's
  first commit).

## Actions & outcomes
- `bin/plan archive SKY-023` (note added: identity rename moved to SKY-025 Phase 11);
  `bin/plan promote <id> backlog` for SKY-005, 006, 018, 020, 024 → `projects/` holds only SKY-025.
- planning/README: at most two active directives; `tests/test_planning.py` enforces it and requires a
  Status block + sane `current_phase` → 67 tests pass.
- hygiene budget now Markdown-only, limit 65000 tokens → "hygiene: clean" (59,331). Delta printf fixed.
- journal/README: "When to write one" rule.
- renovate.json: docker digest/pin/patch/minor grouped into one weekly PR; vulnerability alerts unchanged.
- SKY-025: Phase 11 gains `skynet plan`/`skynet new`, the `lxc-proof` rename, scratchpad triage;
  Phase 17 spelled out (deterministic nightly with no AI engine, PR only on non-timestamp change,
  nightly `bin/check` on `main`, hygiene port); new "Done means" box and F12.
- Stale lifecycle wording fixed in AGENTS.md §5, projects/README, metadata spoke, TEMPLATE.

## Graveyard — tried & abandoned
- Deleting `docs/history/` to meet the context budget → abandoned: already excluded from the budget.
- Doing the nightly changes now → deferred to Phase 17; they rewrite `nightly.sh`/`bin/ops`, which
  that phase ports anyway.

## Follow-ups / open threads
- — none beyond the directive's Phase 11 and Phase 17 steps —
