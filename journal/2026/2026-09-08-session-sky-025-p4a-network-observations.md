---
date: 2026-09-08
time: 22:58:51            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: SKY-025 P4a network observations
tier_touched: [T1]
grants: []
refs: [SKY-025, planning/sky-025-map.md, nix/README.md, runbooks/nightly.md]
thread_status: open
---

# 2026-09-08 · session · SKY-025 P4a network observations

## What happened

Executed the authorized SKY-025 §5 P4a packet in `/tmp/skynet-sky-025-p4a` from
`origin/main` `d2bbedc649e2b4226a2f1b1721a35febbb6148cd`. The worktree was clean before edits.
No live credential path was opened and no network endpoint, host, profile, service, timer, root,
pool, ACL, state, or payload was contacted or changed.

The packet moved the network Proxmox observation from `scripts/collect-proxmox.sh` into the Python
CLI. The shell file now forwards `core|network` only. `collect all` records one local attempted
receipt, collects core then network once, and publishes separate core/network markers with the same
attempted time and each snapshot's SHA-256 and collected time. `collect-status` now requires both.

## Actions & outcomes

- Added `collect proxmox network`, its `/opt/skynet-ops/secrets/proxmox-network.env` default,
  target-labelled report/snapshot, and shared literal credential parser/read-only TLS transport.
- Added synthetic network endpoint fixtures for a distinct `network-node`, protected guests VM 5001
  and CTs 635/837, and valid empty pool/job/task observations.
- Added behavioral coverage for synthetic network read-token selection, operate-token non-use and
  redaction, paired default markers, failed network retention/status refusal, late network marker
  publication refusal, and a later successful recovery.
- Ran a stdlib synthetic explicit-CLI probe with fake HTTPS: core and network reports succeeded;
  network reported 3 guests and 0 pools. Ran a stdlib default-pass probe: paired status succeeded,
  a synthetic network timeout retained the previous network snapshot and made status exit 3, then a
  restored response recovered status to 0.
- Ran `PYTHONPATH=src python -m skynet doctor --json`; it returned a runtime-only report. Ran the
  network CLI with a nonexistent synthetic credential file; it returned unavailable/exit 3 and did
  not create an output file. `python -m compileall -q src tests`, `bash -n` over changed callers,
  and `git diff --check` returned 0.
- Ran the staged pre-commit hook against a workspace-local temporary index/object directory because
  this registered worktree's Git metadata is mounted read-only. Secret scan, invariants, entity
  (47), digest (10), DNS revert (14), compose rollback (11), cert selector (4), tofu rollback
  (22), PVE snapshot (2), provisioning truth (12), PBS collector (14), construction (8), agent
  (82), gitignore (3), nightly automerge (10), and nightly sequence (10) all passed. The hook then
  reached the staged Python check and failed at Nix daemon access with exit 1.
- Updated the package/runtime, observability and nightly documentation plus the SKY-025 map and
  directive. P4b ACL readers and operate-token work were not changed.

## Graveyard — tried & abandoned

- `nix develop --no-write-lock-file -c pytest -q tests/test_proxmox.py tests/test_collection.py tests/test_cli.py`
  → did not start: the inherited Nix fetcher cache was read-only. Retrying with workspace-local
  `XDG_CACHE_HOME` reached the Nix daemon boundary and failed with `Operation not permitted` on
  `/nix/var/nix/daemon-socket/socket`; no lockfile was written.
- Direct `PYTHONPATH=src python -m pytest ...` → unavailable because the host Python has no
  `pytest` module. Ruff, mypy, package build/check, flake evaluation, installed launcher smoke, and
  the Python portion of the staged hook remain unverified for the same unavailable Nix environment.
- Ordinary `git add` → blocked before staging because
  `/home/aliammar/skynet/.git/worktrees/skynet-sky-025-p4a/index.lock` is on a read-only mount.
  The temporary staged index is evidence-only; it cannot publish an authored commit or PR.

## Follow-ups / open threads

- After this P4a PR is human-merged, execute only P4b: both ACL snapshots, operate-token
  self-introspection, paired ACL freshness and removal of their shell implementation; then obtain
  one fresh Astra Medium review for all of P4.
- The map's live API parity, independent workstation access, state/payload recovery, and first live
  transition prerequisites remain unverified.

## Actions & outcomes
- <action> → <result>

## Graveyard — tried & abandoned
Negative results are memory too. Anything attempted that did NOT work — and *why* — so a future
cold agent doesn't re-walk the dead end. Leave a single "— nothing abandoned —" line only if the
episode genuinely tried no path it dropped.

- <approach> → abandoned because <reason>

## Follow-ups / open threads
- <thing left undone, or a question raised>

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
