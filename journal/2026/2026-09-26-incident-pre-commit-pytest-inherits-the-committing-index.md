---
date: 2026-09-26
time: 16:30:50            # local HH:MM:SS; orders same-day episodes in the digest
kind: incident          # session | incident | decision
title: Pre-commit pytest inherits the committing index
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: []                # SKY-###, PR #NNN, ADR NNNN, hosts — anything to cross-link
thread_status: open
# resolves: [<episode-basename>, …]   # optional: close earlier episodes' open threads (append-only-safe)
---

# 2026-09-26 · incident · Pre-commit pytest inherits the committing index

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (journal/README.md). Distillation happens at READ time, never here. -->

## What happened
The Claude 2.1.283 update in `/home/aliammar/skynet-claude-update` passed 67 tests.
Committing through `.githooks/pre-commit` produced local commit `56c28d7` with 343
changed files instead of the two staged package files, including deletions and the
test fixture's `compose/leak.txt`. Nothing was pushed; working files stayed intact.
`tests/test_gates.py` runs `git -C <fixture> add -A`. Git hook environment inheritance
can make this target the committing index despite the changed directory.

## Actions & outcomes
- Restored this task's index with `git read-tree HEAD^`, staged the package files,
  and verified the two-file diff against the parent.
- Moved only the unpublished task branch back to its parent with `git update-ref`.
  The original checkout and dirty lockfile were untouched. The malformed commit is
  recoverable by its hash/reflog.
- Ran the pre-commit script outside Git's hook environment. Commit will use that
  checked index without rerunning the unsafe hook inside Git.

## Graveyard — tried & abandoned
Negative results are memory too. Anything attempted that did NOT work — and *why* — so a future
cold agent doesn't re-walk the dead end. Leave a single "— nothing abandoned —" line only if the
episode genuinely tried no path it dropped.

- First commit outside `nix develop` failed because system Python lacked pytest.
- Running the hook against the malformed HEAD scanned restored baseline files and
  flagged `tofu/provider.tf`. Restoring the task branch parent corrected that diff.

## Follow-ups / open threads
- Fix fixture Git environment isolation in a separate reviewed change; fixture Git
  must not inherit the caller's Git directory, worktree, or index settings.
- Claude activation awaits review, human merge, and a NixOS rebuild.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
