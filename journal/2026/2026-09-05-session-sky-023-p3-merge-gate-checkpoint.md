---
date: 2026-09-05
kind: session
title: SKY-023 P3 merge-gate checkpoint
tier_touched: [T1]
grants: []
refs: [SKY-023]
---

# 2026-09-05 · session · SKY-023 P3 merge-gate checkpoint

## What happened

Synced local `main` to `5a61997`, then created
`fix/sky-023-p3-nightly-merge-gate` for the first bounded Phase 3 batch. This was T1 repository
work only: no infrastructure command, credential read, T2 write, or root grant ran.

The old `scripts/nightly-automerge.sh` accepted a failed `gh pr diff --name-only` as an empty
allowlisted file list because its pipeline ended in `|| true`. The new gate requires an explicit
PR or branch, verifies an open `inventory/<date>` nightly and the exact `OPS_NIGHTLY_BRANCH` when
provided, rejects failed or empty file-list retrieval, requires a non-empty all-pass CI readback,
re-reads the PR head before mutation, and supplies `--match-head-commit` to `gh pr merge`.
`bin/ops nightly` now supplies its exact timestamped branch to that gate rather than asking it to
discover a same-day PR.

Added `tests/nightly-automerge-test.sh`, using a PATH-stubbed `gh`. It proves file-list failure,
empty file list, authored path, failed/pending/missing checks, changed head, and wrong branch
identity do not call merge; the matching generated-only CI-green head does call the pinned merge.
`bash -n`, the new targeted test, `scripts/check-invariants.sh`, every `tests/*-test.sh`, and
`git diff --check` passed.

## Follow-ups / open threads

- This separate merge-gate fix needs normal human review and merge. The agent must not merge it.
- After it merges, resume SKY-023 Phase 3 at the documentation/editor-cleanup batch. The Luna
  audit found the publish split baseline is currently 4,910 rendered tokens and that the existing
  context-map renderer omits `runbooks/diagnose/`.

## Graveyard — tried & abandoned

- Selecting the newest same-day `inventory/` PR when no exact identity exists was removed: it can
  choose a different nightly run and is not a safe fallback.
