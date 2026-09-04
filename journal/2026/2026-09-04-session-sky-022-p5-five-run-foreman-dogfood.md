---
date: 2026-09-04
kind: session
title: SKY-022 P5 — five-run foreman dogfood
tier_touched: [T1]
grants: []
refs: [SKY-022, "PR (phase/sky-022-p5)", bin/agent, tests/agent-test.sh]
---

# 2026-09-04 · session · SKY-022 P5 — five-run foreman dogfood

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used. -->

## What happened

Phase 5 reused three already-recorded real construction runs and executed the two missing routing
shapes. The five tasks were:

1. **Single Terra lead:** P3's cold `bin/agent lead` completed the runbook milestone from the
   disposable checkpoint without delegating; raw run in the P3 journal episode.
2. **Luna Mechanic:** this run delegated one file, `tests/agent-test.sh`, to add deterministic
   regression assertions for P4's `bin/agent --cwd` feature. The Mechanic changed only that file,
   did not commit, and returned 36/36 agent assertions plus 8/8 construction assertions green.
3. **Read-only Scout:** P2's Scout located the construction enforcement gap without writing; raw run
   in the P2 journal episode. This session also used a read-only Scout to select the two missing P5
   tasks and reject work already present on unmerged branches.
4. **Hard lead + Terra Builder:** the Scout found a concrete trust-boundary defect while the
   Mechanic was running: `bin/agent --cwd /tmp` passed because the launcher checked only that the
   directory existed. The lead decided the policy — accept only an exact registered worktree root
   sharing Skynet's Git common directory — and delegated only `bin/agent` implementation to a Terra
   Builder. The Builder touched only that file and did not commit. The lead owned the policy,
   boundary tests, doctrine/runbook edits, integration, and final verification.
5. **Two parallel writer worktrees:** P4 ran two concurrent Terra Builders in separate Git
   worktrees, then the lead resolved their intentional registry conflict; raw run in the P4 journal
   episode.

The Mechanic's patch was correct when returned, but its temporary-directory success assertion became
wrong after the concurrently running Scout exposed the unsafe policy. After the Builder hardened the
launcher, the test reported 33 passes and 3 failures exactly in that old assertion block. The lead
adapted it to prove: main registered root succeeds and renders canonical `cwd`/`-C`; nonexistent,
plain-directory, worktree-subdirectory, and unrelated-repository roots fail. Final result: 39/39.

The Builder's linked-worktree proof used an existing registered nightly worktree. The lead repeated
that proof against `/tmp/skynet-nightly-2026-09-01-1735.CumEcC`: `bin/agent builder noop --cwd ...
--dry-run` resolved the linked root and launched nothing. No production credential or operation was
used by any helper.

## Actions & outcomes

- Luna Mechanic → `tests/agent-test.sh` only; initial 36/36 + construction 8/8; no rework before the
  lead changed the accepted policy.
- Read-only Scout → rejected its first hard-task candidate because it belonged to SKY-018 P7;
  second report found the in-scope arbitrary-`--cwd` construction-leash defect.
- Terra Builder → `bin/agent` only; exact-root/common-Git-dir/registered-worktree validation; main
  and linked roots accepted, subdirectory rejected; no commit.
- Lead → revised the Mechanic test for the safe policy, added plain/unrelated/subdirectory negative
  cases, updated construction doctrine + runbook, and reran all repository tests and invariants.
- Ownership stayed unambiguous: helpers reported bounded subtasks; the lead rejected scope creep,
  made the policy decision, integrated, verified, committed, and owned the PR.

## Graveyard — tried & abandoned

- Scout's first hard-task candidate was the first Rego policy for SKY-018 P7. Rejected because it
  would start a separate directive phase and bundle another unit of work into the SKY-022 P5 PR.
- The Mechanic's original arbitrary-temporary-directory success assertion was abandoned after it
  demonstrated the unsafe pre-hardening behavior. It was not a model failure; the accepted policy
  changed while two independent investigations were running.
- No queue, scheduler, persistent run ledger, worktree manager, retry framework, or wider helper cap
  was added. Five runs produced no failure that would justify one.

## Follow-ups / open threads

- P6 may compare a tiny Codex App Server adapter against native/manual delegation for only the two
  repeated standalone-process frictions: structured progress/final-result capture and timely clean
  interrupt/resume. If the adapter adds indirection without removing those frictions, leave the
  native path primary and do not grow it.
