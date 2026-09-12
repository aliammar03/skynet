---
date: 2026-09-13
time: 03:11:35            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: SKY-025 P8 entity spine and query cache implementation
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-025]         # SKY-###, PR #NNN, ADR NNNN, hosts — anything to cross-link
thread_status: none     # none | open | resolved | unknown; digest shows only explicit open
# resolves: [<episode-basename>, …]   # optional: close earlier episodes' open threads (append-only-safe)
---

# 2026-09-13 · session · SKY-025 P8 entity spine and query cache implementation

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (journal/README.md). Distillation happens at READ time, never here. -->

## What happened
Started from remote `main` at `5bd34e1c163e1c5e08019c69dafa8eac3ceb2548` in the separate
`/home/aliammar/skynet-sky025-p8` worktree because the normal checkout contained uncommitted generated
inventory and documentation. Created `phase/sky-025-p8`; no host or live endpoint was contacted.

The Heavy construction route used one Companion, one cache Investigator, two bounded Executors, and
one independent Tester. P8A moved entity derivation/audit into `src/skynet/entities.py` and removed the
shell implementation bodies. P8B moved the 14-table disposable cache and queries into
`src/skynet/cache.py`, then wired `bin/ops query` through the packaged CLI.

The first independent packaged check failed with exit 126 because `scripts/render-docs.sh` executed
`scripts/build-db.sh` directly inside the Nix sandbox and `/usr/bin/env bash` was unavailable there.
The cache Executor changed that internal call to `bash scripts/build-db.sh`; the repeated packaged Nix
build passed. Main also found that the first cache draft read declared VLANs from `lab.json`; the repair
made it use `entities.conventions(repo)` so `invariants.json` remains the declared-VLAN authority.

The P8 opening bookkeeping changed the phase from prepared to active. Two `AgentDocsContractTests`
still asserted the prepared/blocked transition and were updated. A later temporal-hygiene check caught
numeric phase prose added to current `agent_docs`; Main rewrote those new lines without numeric
directive provenance and the independent diff scan found no P8-added temporal violation.

## Actions & outcomes
- `nix develop --no-write-lock-file -c pytest -q` → 324 passed after the repairs.
- `nix build --no-write-lock-file --no-link .#checks.x86_64-linux.skynet` → passed after the
  renderer interpreter repair.
- Focused entity/cache/route/CLI checks → passed, including ambiguous VMID resolution, liveness-only
  annotation, malformed-source refusal, atomic cache retention, recovery, query failure, and installed
  console execution.
- Ruff, strict mypy, hard invariants, construction, entity, repository-surface, and `git diff --check`
  → passed.
- Original `/home/aliammar/skynet` dirty generated/inventory files → left untouched.

## Graveyard — tried & abandoned
- Directly executing the forwarding shell script from the packaged renderer → abandoned because
  `/usr/bin/env bash` does not exist inside the Nix test sandbox; invoke it with the available `bash`.
- Deriving cache VLAN conventions from `lab.json` alone → abandoned because it could disagree with
  the entity audit and the `invariants.json` declared set.

## Follow-ups / open threads
- The repository baseline still has temporal-hygiene matches in unchanged current-authority text and a
  pre-existing runbook-catalog renderer divergence; P8 added neither condition.
- External acceptance review and human merge remain pending after the authored PR is published.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
