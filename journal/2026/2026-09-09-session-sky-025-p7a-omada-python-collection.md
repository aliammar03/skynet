---
date: 2026-09-09
time: 22:34:17            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: SKY-025 P7a Omada Python collection
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-025, planning/sky-025-map.md, scripts/collect-network-gear.sh]
thread_status: open
# resolves: [<episode-basename>, …]   # optional: close earlier episodes' open threads (append-only-safe)
---

# 2026-09-09 · session · SKY-025 P7a Omada Python collection

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (journal/README.md). Distillation happens at READ time, never here. -->

## What happened
Executed released SKY-025 P7a from clean worktree `/tmp/skynet-sky-025-p7a` at remote-main base
`23223d035a4e5cd8a4138ca28eb6368413f082a9`. `bin/agent lead ... --tier terra --dry-run` resolved
`gpt-5.6-terra` at high effort. A Luna Medium scout inspected the legacy collector, SQLite and
renderer consumers; a Luna High builder wrote only the synthetic Omada API tests and fixtures.

Added `src/skynet/omada.py`, `skynet collect omada`, receipt-bound default collection and
freshness status, a retained forwarding `collect-network-gear.sh`, Nix source inputs and hook
triggers. The controller was never contacted. The tests used fake HTTPS transport, synthetic
credentials and disposable output paths.

## Actions & outcomes

- First Nix package build failed because the new untracked module was absent from the staged
  fileset → staged `src/skynet/omada.py`; the package then contained the module.
- The next installed package run exposed default freshness failure because the Omada snapshot
  lacked a top-level `host` → added it while preserving `controller.host`; updated test stubs.
- The first type-check repair cast the wrong helper return → corrected `_integer` and `_number`;
  direct mypy reported `Success: no issues found in 11 source files`.
- `nix build --no-write-lock-file --no-link .#checks.x86_64-linux.skynet` → passed; package and
  installed checks each reported `229 passed`.
- `nix flake check --no-write-lock-file --no-build` → passed.

## Graveyard — tried & abandoned
- Folding the primary checkout's uncommitted cert/route artifacts into P7a → abandoned because
  P7a authorizes Omada only; those artifacts are P7b scope and the primary tree was preserved.
- Keeping Omada in the legacy shell-reader list → abandoned because P7a requires a shared receipt,
  marker hash/time and default freshness refusal.

## Follow-ups / open threads

- P7b certificate probes and static Caddy route parsing remain the next same-phase slice after
  this authored PR is human-merged; P7c recon then follows. P7 has no independent acceptance until
  every slice is merged and reviewed together.
- Live Omada authentication/read, production inventory replacement, timer/service activation,
  credential/pin change and recovery checks remain unperformed.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
