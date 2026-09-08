---
date: 2026-09-08
time: 10:35:29            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: SKY-025 P3b default collection and freshness
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-025, "PR #215"]
thread_status: open
---

# 2026-09-08 · session · SKY-025 P3b default collection and freshness

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (journal/README.md). Distillation happens at READ time, never here. -->

## What happened
Ali requested continuing P3b after correcting independent review to cover complete numbered
phases. `gh pr view 215` showed it merged at `05b6326c46506b1c936fbaae724a083d8a218954`.
Created `/tmp/skynet-sky-025-p3b`, branch `phase/sky-025-p3b`, from that remote main. Cherry-picked
the unpublished workflow correction `be9573322c2ff8d8d72622ea2cb6a8db276919a9` as `1969b0b`.
Correction to the preceding review-boundary episode: #215 had merged before its handoff edit
could be published; the directive/prompts correction therefore travels in this P3b PR.

The Astra Medium lead detailed P3b in directive §5 before implementation. No worker was used
for P3b. Inspected default dispatch, nightly prepare, renderer/cache reuse, historical invariant
and entity/SQLite consumers, Nix package filtering and tests. Kept the shell readers for network,
ACLs and other collectors; moved only the core collector plus the default coordination to Python.

Chose `inventory/collection-core.json` for an attempted/result/timestamp/hash record. The local
nonblocking lock protects paired publication. An unavailable marker precedes reads; snapshot
publication precedes a successful marker. Consumers reject incomplete/mismatched records.
If the initial marker cannot be written, no remote reads start; nightly's precise attempt cutoff
rejects prior successes for this pass. The 36-hour freshness ceiling accommodates the nightly
cadence plus scheduling margin; it is observation freshness, not service-health verification.

`bin/skynet` invokes offline Nix against tracked Git source. No direct-source Python fallback,
profile install or host activation. `bin/ops query|entities` and rendering check core freshness;
the renderer no longer reuses an old SQLite cache when rebuilding fails. Historical repository
checks remain available independently and retain the VMID 9000 template assertion.

Ali then requested removing stale gates until the directive completes. Suspended only the
automatic Obsidian/documentation-drift/temporal/repo-surface/hygiene suites in hook and CI.
The tests remain callable manually. Secret, privilege/pool, construction, rollback, provisioning,
nightly safety and Python correctness gates remain. P24 must restore maintained documentation,
style and context checks before archive, with obsolete assertion dispositions recorded in P21–22.

## Actions & outcomes
- `nix develop --no-write-lock-file -c pytest -q` → 87 passed. Covers actual CLI/default shell
  chain with fake HTTPS, remaining-reader subprocess exits/timeouts, incomplete/crash markers,
  final-marker publication failure, marker setup failure with same-pass cutoff, missing/corrupt/
  hash-mismatched/stale/future evidence, overlap refusal and stale-cache non-reuse.
- `nix build --no-write-lock-file --no-link .#checks.x86_64-linux.skynet` → passed source and
  installed package tests, Ruff and mypy. Tests use writable temporary fixture copies and a
  writable pytest cache outside the Nix store.
- `nix flake check --no-write-lock-file --no-build` → all checks passed. Existing system-rename,
  missing app-meta and custom deploy-output warnings remain. Concurrent evaluations emitted an
  ignored SQLite cache-busy diagnostic; successful invocations still exited 0.
- `bin/skynet doctor --json` → exit 0, version 0.1.0, Python 3.13.15 through actual offline
  Nix launcher. `bin/skynet collect-status --repo /tmp/skynet-sky-025-p3b --json` → exit 3,
  unavailable because the worktree has no refresh marker. No credential or lab API read.
- Full pre-commit passed before the optional documentation checks were paused. The final
  automatic check set also runs Python behavioral/lint/type checks for the changed paths;
  the five paused suites are explicitly deferred, not counted as passing by the new policy.
- `git fetch origin main` before close-out still resolved the same P3b base; no intervening
  main changes were found. No inventory or production checkout files were written by this work.

## Graveyard — tried & abandoned
- Initial Nix build ran before the new collection module was staged: module import failed.
  Staged the new file so Nix's tracked Git source included it; no source fallback added.
- First shell-launch tests: five failed, 69 passed in the build phase because `/usr/bin/env`
  is absent in the sandbox. Temporary copies use the discovered Nix Bash shebang; script
  bodies remain the actual caller code. Installed-source copies also needed owner-write
  permission before adjusting their shebangs; fixed fixture permissions, not production code.
- Shared fixture imports triggered Ruff F811 when test parameters used the same names.
  Registered the existing synthetic fixture module as a pytest plugin instead.
- First full hook: entity suite 46 passed/1 failed because its stored-template assertion
  invoked the newly freshness-gated `bin/ops entities`. Pointed that assertion at the
  historical snapshot audit; default consumer refusal stays separately tested. No assertion removed.

## Follow-ups / open threads
- After Ali merges P3b, one fresh Astra Medium review must cover all P3 implementation:
  #215 and the P3b PR. P4 is not authorized; accepted progress remains 2/24.
- Before using the merged default path live, the map's independent workstation/state/payload
  recovery evidence remains required and unverified. No production API parity, recovery drill,
  credentials, profile install, root grant, host activation or timer/service change is claimed.
- Restore maintained documentation/style/context checks in hook and CI before completing
  SKY-025; obsolete checks need an explicit disposition. The user-authorized pause is temporary.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
