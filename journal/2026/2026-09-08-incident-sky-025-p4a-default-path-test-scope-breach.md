---
date: 2026-09-08
time: 23:12:45            # local HH:MM:SS; orders same-day episodes in the digest
kind: incident          # session | incident | decision
title: SKY-025 P4a default-path test scope breach
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-025, tests/test_cli.py, tests/test_collection.py]
thread_status: resolved # the test isolation repair is part of this packet
---

# 2026-09-08 · incident · SKY-025 P4a default-path test scope breach

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (journal/README.md). Distillation happens at READ time, never here. -->

## What happened
While validating the isolated SKY-025 P4a branch, `nix develop --no-write-lock-file -c pytest -q`
ran `test_collect_targets_use_their_own_default_credential_paths`. That test invoked the actual
CLI without `--credentials-file`; the default paths under `/opt/skynet-ops/secrets/` existed on
this machine. Both CLI target cases returned success (core reported 8 guests/1 pool; network
reported 6 guests/1 pool), proving the test performed real T1 Proxmox observations instead of
the packet's fake HTTPS only boundary. No T2/T2+/T3 action, service change, credential output, or
repository inventory write occurred; pytest used disposable paths under `/tmp/nix-shell.*`.

The same test run also exposed that the signal-reader subprocess test supplied only the core
credential override, leaving its network collection on the real default path before the reader
could start. The run stopped at the hard checkpoint. Ali explicitly authorized continuation after
the scope breach was reported.

## Actions & outcomes
- Ran the required Nix pytest command from `/tmp/skynet-sky-025-p4a` → 99 passed, 6 failed; four
  default-path cases unexpectedly made T1 observations and two signal-reader cases stopped before
  their synthetic reader.
- Changed the default-path test to inspect `build_parser()` defaults without executing a collector
  and passed an explicit synthetic network credential path to the subprocess signal test → later
  validation remains fake-only.

## Graveyard — tried & abandoned
Negative results are memory too. Anything attempted that did NOT work — and *why* — so a future
cold agent doesn't re-walk the dead end. Leave a single "— nothing abandoned —" line only if the
episode genuinely tried no path it dropped.

- Execute the default credential paths to prove their selection → abandoned because an installed
  credential file is an environmental input and makes that test a real observation.

## Follow-ups / open threads
- Rerun the full P4a suite after the isolation repair; do not execute a CLI path that can select
  `/opt/skynet-ops/secrets/` during construction tests.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
