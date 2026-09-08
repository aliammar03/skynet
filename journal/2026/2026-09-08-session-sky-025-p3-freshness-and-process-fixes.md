---
date: 2026-09-08
time: 17:12:17            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: SKY-025 P3 freshness and process fixes
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-025, "PR #215", "PR #216", "PR #217"]
thread_status: open
---

# 2026-09-08 · session · SKY-025 P3 freshness and process fixes

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (journal/README.md). Distillation happens at READ time, never here. -->

## What happened
Ali requested `planning/prompts/execute.md` and SKY-025 Phase 3 fixes from §5. I read the
cold-boot digest/map, AGENTS, planning workflow, merged directive/map and relevant construction,
code, git and documentation conventions. `git fetch origin main` resolved
`89a1dee3f497df7c8609c8639298f4d3db66d505`; GitHub confirmed #217 merged on 2026-09-08 at
05:58:13Z. #215 and #216 were merged, and no existing P3 fix PR appeared. #214 records P2 ACCEPT.
The rollout's filtered turn-context metadata showed `gpt-6-astra`, `medium`; the installed model
catalog and `bin/agent lead 'SKY-025 Phase 3 fixes' --tier astra --dry-run` agreed.

The main checkout contained pre-existing generated inventory/docs changes and untracked
`inventory/tofu-drift.txt`. I created `fix/sky-025-p3` at the remote base in
`/tmp/skynet-sky-025-p3-fix`. No timer, service, host, profile or production collection was changed.
All collector tests use synthetic credentials and fake HTTPS; child processes/output files are
temporary local fixtures. No production credential file, lab API or protected state was read.

R1's old success marker survived a failed initial atomic replacement. I made the existing lock
file hold the new attempt timestamp before publishing that marker, using truncate/flush/fsync
and then write/flush/fsync independently of rename. Status requires matching receipt/marker
timestamps and the existing hash/time checks. It locks and reaffirms only the existing receipt
so inability to persist invalidation also returns unavailable. Missing receipts require a full
refresh; they are deliberately local, so copying Git inventory alone does not establish freshness.
If storage cannot persist any failure, no durable diagnosis is possible; status refuses while
that same storage operation fails, and the documented recovery requires storage repair plus refresh.

R2 used `subprocess.run(timeout=120)`, which killed only the immediate shell. I added an isolated
session/process group per reader, temporary Linux subreaper ownership, and kill/reap cleanup
before returning, including after an early leader exit. SIGINT/SIGTERM are blocked across spawn
and cleanup so an interruption cannot lose a child handle or skip cleanup. Reader runtime is
120 seconds; cleanup is bounded at five seconds. Unconfirmed cleanup stops the workflow and
persists `recovery-required`, blocking a subsequent collection before remote reads. The parent
does not signal its own process group. Other reader results still mean process exits only.

After the interface edits I assigned one Luna High builder only `tests/test_collection.py` in
the isolated worktree, with no production/credential/module/commit/push/helper authority. The
worker instead edited `/home/aliammar/skynet/tests/test_collection.py` and tested the old module
there (reported 78 passed and five implementation-dependent failures). I inspected its exact
diff, applied it to the specified worktree and reversed only that same diff in main using
`apply_patch`. Final main status matched the original unrelated dirty paths; its test file had
no diff. No worker result was accepted as validation of the isolated implementation.

Ali then requested an end-of-work review and next-phase packet. I prepared a draft P4a network
observations packet with bounded P4b ACL ownership. It retains the merged-result acceptance gate,
does not release/implement P4 and keeps accepted progress at 2/24.

## Actions & outcomes
- Integrated regressions cover successful synthetic refresh → failed initial marker replacement
  → unchanged snapshot/no additional HTTPS requests → ordinary status, query, entity and renderer
  refusal without `--since` → unchanged factual page → successful later refresh.
- Added real shell/child timeout tests, a next-reader PID check, lock-held-during-cleanup assertion,
  no post-deadline child write, normal leader-exit cleanup, KeyboardInterrupt, and actual SIGINT
  and SIGTERM sent to a temporary runner. Subsequent collection proves the lock is usable.
  Cleanup refusal tests preserve quarantine and stop further readers/remote attempts.
- `nix develop --no-write-lock-file -c pytest -q` → 94 passed in 16.96s. Earlier integrated
  version passed 92 cases before the two actual-signal cases were added.
- `nix develop --no-write-lock-file -c ruff check src tests/test_*.py` → all checks passed.
- `nix develop --no-write-lock-file -c mypy src/skynet` → no issues in six source files.
- Final `nix build --no-write-lock-file --no-link .#checks.x86_64-linux.skynet` → exit 0;
  source package checks passed and the installed-module suite passed 86 cases in 17.23s.
  The installed suite excludes the checkout-only CLI metadata cases by design.
- `.githooks/pre-commit` with implementation paths staged → exit 0, including 94 Python cases,
  lint/types, secret scan, invariants, entity/SQLite assertions, rollback/provisioning,
  construction/routing and nightly sequence/merge-safety suites. No safety gate changed.
- `nix flake check --no-write-lock-file --no-build` → exit 0. Existing system-rename,
  app-meta and custom deploy-output warnings remain; this does not claim a host-closure build.
- `bin/skynet doctor --json` → exit 0, runtime version 0.1.0/Python 3.13.15.
  `bin/skynet collect-status --repo /tmp/skynet-sky-025-p3-fix --json` → exit 3/unavailable
  without a local receipt. Both used the real offline package launcher without credentials.
- `git diff --cached --check` → exit 0. Remote main rechecked at the same base SHA.
- Self-review inspected the complete collection diff, callers and P3 transport/publication
  contracts. R1 evidence now fails ordinary gates; R2 cleans under the held lock and stops on
  uncertainty. Existing explicit-output validation, TLS/redaction, snapshot retention, 36-hour
  ceiling and nightly cutoff are preserved. This is an implementing lead's review, not fresh
  merged-result acceptance. P3/G2 remains review-pending after this fix; P4 is only drafted.

## Graveyard — tried & abandoned
Negative results are memory too. Anything attempted that did NOT work — and *why* — so a future
cold agent doesn't re-walk the dead end. Leave a single "— nothing abandoned —" line only if the
episode genuinely tried no path it dropped.

- The initial `nix develop ... -c mypy src/skynet` never reached mypy: its package dependency
  correctly failed the obsolete mock-`subprocess.run` timeout test (1 failed, 78 passed).
  Replaced that mock-only proof with actual descendant processes.
- Worker tests used `monkeypatch.undo()`, which also undid the HTTPS fixture. Replaced those
  calls with targeted restores, corrected expected reader logs, and made subprocess launchers
  preserve the test interpreter's import path so installed checks exercise the installed module.
- The first installed check (`nix build --no-write-lock-file --no-link
  .#checks.x86_64-linux.skynet`) returned 1: 85 passed, one fixture failed with PermissionError
  rewriting copied `repo/bin/ops`. `shutil.copy` retained the Nix store's read-only mode.
  Set executable/writable fixture mode before adapting the shebang, matching the existing test
  pattern; this changes only temporary test files, not package or production permissions.
- Concurrent Nix commands printed an ignored eval-cache SQLite busy warning. No dependency
  refresh or cache deletion was attempted.

## Follow-ups / open threads
- After Ali merges the P3 fix PR, use a fresh Astra Medium session to review all P3 implementation
  (#215, #216 and this fix) via `planning/prompts/review.md`. Review the draft P4a/P4b boundaries
  before releasing the next packet. Accepted progress remains 2/24 until acceptance.
- Independent workstation/state/payload recovery, live API/TLS parity and activation remain
  unverified and outside this packet. No grant or live transition is released.
- Ali's five paused documentation/style/context suites were not run or counted as passing;
  their maintained replacements must return to hook/CI by P24.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
