---
date: 2026-09-10
time: 19:49:04            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: SKY-026 Phase 3 Heavy orchestration dogfood
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-026]         # SKY-###, PR #NNN, ADR NNNN, hosts — anything to cross-link
thread_status: none     # none | open | resolved | unknown; digest shows only explicit open
# resolves: [<episode-basename>, …]   # optional: close earlier episodes' open threads (append-only-safe)
---

# 2026-09-10 · session · SKY-026 Phase 3 Heavy orchestration dogfood

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (journal/README.md). Distillation happens at READ time, never here. -->

## What happened
Ali released SKY-026 Phase 3 only. Main selected the directive's Heavy route and used deployment Task
ID `sky026-p3-20260910`. The Direct lane was the Phase 3 exits, current runtime/gates, and integration
decisions. One persistent Companion started without inherited turns and read the bounded Skynet
surface. One Investigator read the pinned donor source and current upstream in parallel. Main waited
for both completed reports and synthesized once; it did not ask either worker for status.

The donor comparison reported pinned `6d9b06f73bee7f899001b0bb102c70529a24313f` and upstream `main`
identical. Its reusable Phase 3 implementation was source contracts and contract-test patterns, not a
dispatcher. Main therefore assigned `tests/construction-test.sh` as one bounded package to a Default
Executor, using the exact Implementation capsule. No Senior Executor was started because the bounded
shell/TOML contract package did not require exceptional cross-cutting reasoning. Main did not edit the
Executor-owned file or run the Tester's verification.

The Executor added a TOML-aware source-contract check and disposable drift fixtures. An independent
Tester received acceptance intent, risks and gates rather than an implementation-shaped test script.
Its first run found a real fail-open defect: changing the Tester contract to `Workers orchestrate other
workers.` or capitalizing the Investigator's `Coordinate another worker` still returned 40/40. Main
sent only that changed evidence back to the same Executor. The Executor repaired the negative-context
checks and added both regressions. Main then sent only the repair delta to the same Tester, which
reported 42/42 and both bypass mutations rejected. The persistent Companion was reused for a final
delta-only conflict check and found no scope, authority, or unrelated-state conflict.

## Actions & outcomes
- Spawned one Companion and one Investigator as a single intake batch → bounded repo context and
  donor evidence returned once; no current SKY-022 guidance was used.
- Assigned `tests/construction-test.sh` to one Default Executor → capsule, Task-ID/delta,
  no-child-orchestration, repair ownership, semantic quantity, and retired-architecture drift gained
  fail-closed fixtures.
- Assigned independent verification to one Tester → baseline passed but two imperative-wording
  bypasses reproduced with exit 0.
- Returned the focused defect to the owning Executor, then the repair to the same Tester → final
  `bash tests/construction-test.sh` reported 42 passed, 0 failed; both bypass copies exited 1;
  `./scripts/check-invariants.sh`, `bash -n tests/construction-test.sh scripts/check-invariants.sh`,
  and `git diff --check` passed.
- Kept all work at T1 repository scope → no host, credential, secret, T2/T3 action, generated-file
  hand-edit, custom workflow runtime, or worker child spawn occurred.
- Preserved the pre-existing untracked `inventory/tofu-drift.txt` throughout.

## Graveyard — tried & abandoned
Negative results are memory too. Anything attempted that did NOT work — and *why* — so a future
cold agent doesn't re-walk the dead end. Leave a single "— nothing abandoned —" line only if the
episode genuinely tried no path it dropped.

- Substring-only `non_orchestration_marker` plus a modal-verb regex → abandoned after the independent
  Tester proved positive imperative orchestration wording could contain the marker and still pass.

## Follow-ups / open threads
- Phase 4 remains: adapt continuity, Archivist closure, and honest token accounting without a second
  truth tree.
- Exact prose matching in the contract test is deliberate donor-style enforcement but requires test
  updates when authoritative wording changes.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
