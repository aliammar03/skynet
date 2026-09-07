---
date: 2026-09-07
time: 13:26:29            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: SKY-025 P2 package local CLI
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-025]
thread_status: open
---

# 2026-09-07 · session · SKY-025 P2 package local CLI

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (journal/README.md). Distillation happens at READ time, never here. -->

## What happened
Executed the released SKY-025 P2 packet in `/tmp/skynet-sky-025-p2`, branch
`phase/sky-025-p2`, from `cdac8f98a3ea6f4326034b428be67df283e7ac3f`. The packet stayed T1: no
host activation, services, timers, collectors, credentials, grants, or production calls. Added the
minimal Python package, source-filtered Nix package/checks, CI/hook checks, and runtime-only doctor.

## Actions & outcomes
- `git fetch --unshallow origin` → restored commits referenced by the local flake graph; initial
  Nix evaluation could not read object `4d68f2f42067c253dadf7f7c16ce1f9730a8902d` from the shallow checkout.
- `nix build --no-write-lock-file --no-link --print-out-paths .#skynet` → built
  `/nix/store/v15z0mzh2aq43asbcvm2xy82i9h85p4f-skynet-0.1.0`.
- From a temporary directory with `PYTHONPATH` unset, the packaged `--help`, `--version`, `doctor`,
  and `doctor --json` exited 0; `collect` exited 2 with argparse's invalid-command diagnostic.
- `nix develop --no-write-lock-file -c pytest -q` → 10 passed.
- `nix develop --no-write-lock-file -c ruff check src tests/test_cli.py` → all checks passed.
- `nix develop --no-write-lock-file -c mypy src/skynet` → no issues in 4 source files.
- `nix build --no-write-lock-file --no-link .#checks.x86_64-linux.skynet` and
  `nix flake check --no-write-lock-file --no-build` → passed; evaluation emitted the existing
  `system` rename and unrecognised `deploy` output warnings.

## Graveyard — tried & abandoned
- First package check ran both entry-point variants while the build-stage `skynet` console script
  was not yet on `PATH` → abandoned; package build now tests the module variant and the aggregate
  Nix check tests the installed console variant outside the source checkout.

## Follow-ups / open threads
- Ali merges the authored P2 implementation PR, then a fresh Astra Medium session reviews that
  merged result with `planning/prompts/review.md`; P3 is not authorized before that acceptance.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
