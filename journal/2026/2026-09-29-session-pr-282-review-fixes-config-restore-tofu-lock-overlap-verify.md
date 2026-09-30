---
date: 2026-09-29
time: 11:59:49            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: PR 282 review fixes: config restore, tofu lock, overlap verify
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-025, PR #282, ADR 0008]
thread_status: open     # none | open | resolved | unknown; digest shows only explicit open
---

# 2026-09-29 · session · PR 282 review fixes: config restore, tofu lock, overlap verify

## What happened
Ali pasted an external review of PR #282 (branch sky-025-p15-tofu, HEAD 6e73cfe) with 10 findings.
All 10 were confirmed against the branch code. Ali made the three design calls:
- #3: Tofu gets its own lock.
- #4: Rollback becomes a config restore, not a snapshot rollback.
- #7: A dirty post-apply plan rolls back only when it overlaps the approved change.

Everything was fixed as follow-up commits on the same branch.

Live, read-only evidence (ops VM, worktree code, scratch copies of state, nothing applied):
- Scratch plan of proxmox-core with athena cores 4→6 and docker-dmz tags +drilltest:
  - `after_unknown` was `{}` for both updates, so finding #1 (`[{}]` nested blocks) did NOT
    reproduce on these resources with tofu + bpg 0.111. Fixed anyway (`_has_unknown`) and
    tested synthetically.
  - Deltas: athena `['cpu']`, docker-dmz `['tags']`. Both are restore-covered.
- #2 on that real plan JSON: docker-dmz `after` carries the full agent `ipv4_addresses`,
  `mac_addresses` and `network_interface_names` (lo, eth0, docker0, br-*, veth MACs). Appending one
  Docker network to both sides:
  - old hash: `1d91b79fe134` → `5254e8948249` (would be MISMATCH-held at merge);
  - new hash: `7a30e5c470df` → `7a30e5c470df`.
- #9: planned the cloudflare-dns stack with `SSL_CERT_FILE` = the proxmox-core pin:
  - no `SSL_CERT_DIR` (old code): exit 0. It reached Cloudflare through the system CAs in
    `/etc/ssl/certs`, so the pin was never exclusive;
  - with `SSL_CERT_DIR` = an empty dir (new code): exit 1, x509.
- All three stacks via `python -m skynet tofu plan <stack> --ref HEAD` from the worktree: init OK
  (registry env, no pin) and 0 changes each.
- `pve.status` / `pve.pending` / `pve.config` GETs against lxc/10030 and qemu/10015: both running,
  pending [], 18 and 30 config keys.

## Actions & outcomes
- writepath: `Ledger.lock(name)` and `run(lock=...)`. Tofu uses `tofu.lock`, and `busy()` stays
  on `write` → a deploy, a revert auto-merge and watch are never blocked by an apply.
- pve.py:
  - `restore()`: minimal PUT with a digest compare-and-swap and `delete=` for added keys; stop
    first when the target power is stopped; reboot only if changes are pending on a running
    guest.
  - Also: `pending()`; disk-only `create` (no vmstate); `create`/`delete`/`restore` refuse
    excluded VMIDs themselves; snapshot `rollback` removed.
- tofu.py:
  - The hash covers only (address, previous_address, type, actions, importing, delta). An unknown
    key is recorded as `(known after apply)` without its refreshed `before`.
  - `RESTORE_COVERS` replaces `SNAPSHOT_COVERS`. A guest with pending changes before the apply is
    refused (USAGE, held). The rollback proof is now whole config + no pending.
  - Verify saves a plan and diffs it. Overlap → `NOT_LANDED` (rollback). Otherwise `DRIFTED`
    (UNSETTLED: state recorded, snapshots kept, held, alert).
  - Every hold alerts once (`_hold_alerts` keys in `pending.json`), covering an unreadable
    held.json and an orphan prehold. `record_state` clears a `"*"` hold on a success.
  - `retry_cleanup(repo, ...)` checks `origin/main`'s invariants and drops and alerts on an
    excluded entry.
  - The state branch is fetched once per pass. `write_branch(expect=)` uses `expect` as the parent
    and a rejected push is `STATE_MOVED`.
  - `GUEST_SECONDS` was recomputed; 5×guests still fits the 5 h unit.
- tests: one test per finding. Reverting each of #1, #2, #7, #8 and #10 makes its test fail.
  `bin/check` green.
- Docs: actuators.md, AGENTS.md §4, system-design §1a line, ADR 0008 steps 3–4, timers.nix
  comment, SKY-025 status block (the drills now prove the config restore).

## Graveyard — tried & abandoned
- Moving the pre-apply hold into `execute` so the `started` record precedes it → abandoned: a
  transient git failure would become a held rolled-back run instead of a retried refusal.
  Alert-once on any hold covers the orphan case.
- Auto-clearing an orphan prehold when the ledger has no line for its operation → abandoned: a
  wiped ledger (rebuild without the persisted state) cannot prove nothing executed. It alerts
  instead; the operator uses `--ignore-hold`.
- Keeping the snapshot rollback but refusing it on data guests → not chosen (Ali: config restore).

## Follow-ups / open threads
- `pve.restore` is unit-tested against a fake API only. Its first live run is the post-merge
  athena drill (LXC) and the vm-drill (VM: pending-change reboot path).
- The drills must include a no-overlap dirty re-plan → held, not rolled back.
- PR #282 needs a fresh-session review verdict (Full tier) before Ali merges.
