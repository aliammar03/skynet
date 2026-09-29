---
date: 2026-09-29
time: 12:41:14            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: PR 282 second review: bind-mount snapshot, bootstrap adoption, facts lock
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-025, PR #282, ADR 0008, CT 240]
thread_status: open     # none | open | resolved | unknown; digest shows only explicit open
---

# 2026-09-29 · session · PR 282 second review: bind-mount snapshot, bootstrap adoption, facts lock

## What happened
Ali asked for an extensive review of PR #282 (branch sky-025-p15-tofu, HEAD 7cec3f8). Claude Code
ran `/code-review 282 xhigh`, which returned 10 findings, all in `src/skynet/tofu.py`. Ali then asked
for all of them to be fixed on the PR branch, working in the `/home/aliammar/skynet-p15` worktree.
Nothing touched live infrastructure. The only T1 reads were `ls` of `/opt/skynet-ops/state/tofu/` and
the key names (not values) in three `/opt/skynet-ops/secrets/*.env` files, to confirm the stricter
credential parsing still accepts the live files: proxmox-core.env has PVE_HOST, PVE_TOKEN,
PVE_TOKEN_OPERATE, PVE_CACERT; technitium.env has TECH_HOST, TECH_TOKEN, TECH_CACERT; cloudflare-dns.env
has CF_DNS_TOKEN, CF_ZONE, TUNNEL_ID.

The findings and fixes:
1. CT 240 (PBS) has bind mount `mp0: /mnt/pbs-unraid`. Proxmox refuses to snapshot a CT with a bind
   mount ("snapshot feature is not available"), so every lxc-pbs.tf update would be refused as
   UNAVAILABLE, never held, and retried each minute. Ali chose (via AskUserQuestion) to skip only the
   fallback snapshot and record it. `pve.snapshottable(config)` detects an `mpN` whose volume is a
   host path. The guest's config is still saved and restored, and the rollback proof still runs.
   `_Saved.saved` is the restore list and `_Saved.taken` the snapshot list; the rollback now iterates
   `saved`.
2. A run that ended `unavailable` after `_prehold` (for example, the `started` ledger append failed)
   had its hold marked announced without any alert. `pending()` now marks a hold announced only
   when the result has a hold step (ok/failed) or an ALARMS outcome. Otherwise `_held` alerts on the
   next pass.
3. Bootstrap: `classify()` used to count "local file, no branch, no base" as pending and push it.
   The 09-27 journal notes that a leftover unmodified monolith copy was once at
   state/tofu/proxmox-core.tfstate; the live files there are now the split ones, from 19:46 on 09-27.
   The new kind `bootstrap` covers this. sync_state returns such a state unpushed, and `_record`
   refuses it (UNADOPTED). `adopt()` sets base=`absent` at the start of the snapshot step, which only
   runs after the plan passed the approval and every refusal; from then on it is ordinary pending
   state. A monolith plans deletes, which are refused, so it is never adopted.
4. Several pending.json read-modify-writes ran outside any lock (_set_failures, _local_hold,
   _announced, _pass_failures, _hold) and could clobber `_cleanup` intents written by a live apply.
   The fix is `_update_facts(ledger, change)` under its own `tofu-facts` flock, and every writer goes
   through it. retry_cleanup now removes only the entries it handled, so entries queued meanwhile
   survive.
5. `plan --approve` now runs `check()` (refuse + MAX_GUESTS), the same function the executor's
   preflight calls. It prints the plan, then "not approved: <reason>", and exits USAGE.
6. `run_drift` now rewrites inventory/tofu-drift.txt with "plan unavailable" when the fetch or
   resolve fails, instead of leaving yesterday's report to be committed.
7. The excluded guests are now `all_excluded()`, the union of the revision's invariants.json and
   main's, used by both apply and approve.
8. `apply(settle=False)` from pending: interrupted applies are settled once per pass, not once per
   stack.
9. Folded into 4.
10. The tofu credential readers now use `proxmox.assignments` / `dns.assignments` (split out of their
    `credentials()`) and `publish.cloudflare_credentials`. PVE_CACERT and TECH_CACERT are now
    required (there is no CERTS default any more), and tokens must be printable.

## Actions & outcomes
- 13 new failure-case tests. Run against the old `src/` (git stash), every one fails except
  `test_a_refused_plan_never_adopts_a_first_state`, a guard that holds on both versions.
- The first run of the new code broke `test_partial_failure_state_is_persisted_while_the_revision_stays_held`:
  a bootstrap state a real apply wrote was never pushed. That is what led to `adopt()`.
- `nix develop --command bin/check` → OK (442 passed, all gates).

## Graveyard — tried & abandoned
- Making `_record` accept `bootstrap` directly (push whenever an apply path records) → abandoned:
  persist_pending then could not tell an apply's unrecorded first state from a stray copy; adoption
  is what makes the two differ.
- A credential test with token "has space" → passed on the old code too: read_assignments already
  rejects unquoted spaces. Switched to a non-ASCII token, which only `printable` catches.

## Follow-ups / open threads
- The bind-mount skip should be exercised live on the first real lxc-pbs.tf change (a supervised run).
- The concurrency test only proves `_update_facts` serializes. It cannot fail on the old code
  (the helper did not exist there).
