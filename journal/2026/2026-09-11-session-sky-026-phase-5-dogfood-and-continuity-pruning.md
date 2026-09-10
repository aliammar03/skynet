---
date: 2026-09-11
time: 00:11:01            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: SKY-026 Phase 5 dogfood and continuity pruning
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-026, docs/conventions/construction.md, agent_docs/] # SKY-###, PR #NNN, ADR NNNN, hosts — anything to cross-link
thread_status: none     # none | open | resolved | unknown; digest shows only explicit open
# resolves: [<episode-basename>, …]   # optional: close earlier episodes' open threads (append-only-safe)
---

# 2026-09-11 · session · SKY-026 Phase 5 dogfood and continuity pruning

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (journal/README.md). Distillation happens at READ time, never here. -->

## What happened

The session started on `main` at `9ba683a` in `/home/aliammar/skynet` and read all six
`agent_docs/` files plus SKY-026 before broad exploration. The derived handoff said PR #251 was
unmerged and the installed profile still used `OnRequest`; `git log` showed #251 merged and
`~/.codex/config.toml` contained `approval_policy = "never"` plus
`sandbox_mode = "danger-full-access"`. Main used Git and installed runtime as higher authority and
reserved the stale-memory repair for closure.

One persistent Companion inspected current repository context while one Investigator compared the
pinned `viettran-edgeAI/codex_workflow` source contracts. Their batched reports agreed that the donor
role/capsule/repair contracts were already represented, but current Skynet still prescribed the
generated digest as a second cold-start path. Main decided to retain the digest only for recent
activity, open-thread, and episode retrieval; retain the context map only for on-demand load-cost
routing; and remove `.agent/CHECKPOINT.md`, which had no caller beyond its ignore test.

Two Default Executors then edited non-overlapping packages concurrently. One owned the digest/map
renderers and their current docs/tests; the other owned checkpoint retirement and old construction
language in current prompts/planning/contracts. No Senior Executor was used because neither package
required exceptional architecture or cross-cutting reasoning. The first combined Tester pass found
three natural current-guidance defects: `.githooks/pre-commit` still said cold-boot digest,
`planning/prompts/` still assigned decomposition to an execution lead, and active SKY-006 still
mandated digest-first intake. Main returned those findings to the original legacy-surface Executor;
the same Tester rechecked the repair and passed it.

All work was local T1 construction. No production host, root grant, secret, deploy, merge, or live
infrastructure write was used. The unrelated untracked `inventory/tofu-drift.txt` present at intake
was left untouched.

## Actions & outcomes

- `git switch -c sky-026-phase-5` → opened one authored implementation branch from current `main`.
- Fresh `agent_docs/` + directive intake → recovered the phase with bounded reads and detected one
  real stale-memory conflict against merged Git/runtime evidence.
- Companion + Investigator batch → identified continuity duplication and confirmed donor source
  alignment without a second control plane.
- Two concurrent Default Executors → narrowed digest/map roles, removed checkpoint state, migrated
  current legacy guidance, regenerated owned views, and added regression coverage.
- Independent Tester first pass → focused repair findings returned to their original Executor.
- Same Executor repair + same Tester recheck → construction 44/44, continuity 3/3, digest 11/11,
  documentation drift 8/8, repo surface 12/12, nightly sequence 10/10, Nix build, renderer
  idempotence/source agreement, and `git diff --check` passed. Earlier unchanged evidence also
  covered 277 pytest tests, Ruff, mypy, other shell gates, and flake evaluation.
- Environment checks → `pre-commit` was absent in the host and Nix shell; hygiene retained two
  failures reproduced on clean `HEAD` (numeric provenance/current compatibility comments and a
  `root-session-id` false positive), so neither was attributed to this phase.

## Graveyard — tried & abandoned

- Treating the generated digest and context map as a second cold-start sequence → removed because
  `agent_docs/` plus the active directive now owns cross-session continuity; the generated views
  retained only their distinct retrieval/index consumers.
- Retaining `.agent/CHECKPOINT.md` as optional continuity → removed because repository search found
  no runtime consumer beyond the ignore rule and its self-referential test.
- First nightly-sequence verification attempt → hit temporary-directory capacity while copying the
  provider cache; the Executor removed only its disposable copies and the clean rerun passed.

## Follow-ups / open threads

- Open the one authored Phase-5 PR and obtain a fresh external `ACCEPT SKY-026` review.
- Only after ACCEPT: mark Phase 5 done, set `current_phase: 5`, archive SKY-026 through `bin/plan`,
  refresh the roadmap, and land the bounded final close-out without self-merging.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
