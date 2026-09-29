---
date: 2026-09-29
time: 16:16:10            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: PR 282 fourth review: computed fields in overlap, planned host stop, adoption order, nested unknowns, never-started tofu
tier_touched: []        # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-025, PR #282, ADR 0008, VM 10015]
thread_status: open     # none | open | resolved | unknown; digest shows only explicit open
---

# 2026-09-29 · session · PR 282 fourth review: computed fields in overlap, planned host stop, adoption order, nested unknowns, never-started tofu

## What happened
Ali pasted a max-effort review of #282 at 36e85ba: 10 findings, unverified by the reviewer. Each was
checked against the code, all 10 held, and all 10 were fixed. There were no live reads or writes;
every result comes from the offline suite.

1. `_touched` counted computed-only attributes. A bpg VM update marks ipv4_addresses and
   network_interface_names unknown, so a perpetual diff on the same VM "overlapped" the approved
   change → NOT_LANDED → a rollback of a change that landed. → `_touched`/`overlaps` take
   `readonly` (the schema set already fetched for `reversible`); verify passes `state_.readonly`.
   An update whose delta is only outputs touches nothing. The "created anew" check now uses every
   approved address, not only the touched ones.
2. An approved `started = false` on a Docker host waited 600 s, then HOST_DOWN → a restore that
   powered it back on. → `fences()` returns context → Guest. Verify waits only for hosts the change
   does not stop (`stopping()`: after.started is False); the restore proof waits only for hosts
   that were running before.
3. `adopt()` ran at the top of snapshot(), before the pending-config refusal and the prehold. A
   refused run left base=`absent`, and the next sync pushed the unproven state. → adopt() is the
   last line of snapshot(), after `_prehold`.
4. `_delta` reduced any partly unknown attribute to {after: UNKNOWN}, so a hand edit elsewhere in
   network_interface/disk left the hash unchanged. → `_known()`: a wholly unknown attribute stays
   bound by name (address lists churn); a partly unknown one keeps its `before` plus every known
   leaf of `after`.
5. `_settle` alarmed rollback-failed and held, and the same pass's `_held` pushed "held" as well. →
   `_settle` marks the hold announced when its alarm went out (a failed alarm still leaves `_held`
   to alert).
6. A Popen OSError was INDETERMINATE → held + alarm. → `_tofu` raises NOT_STARTED;
   Workspace.apply re-raises it. rollback() releases this operation's own prehold (via
   write_branch, only if held.json is revision+PREHOLD+this op id), prunes the snapshots, and
   returns `writepath.NOT_STARTED`. writepath maps that recovery to outcome `unavailable`
   (UNAVAILABLE), so `_count` backs off and retries it.
7. `skynet withdraw --help` still said "and public CNAME". Fixed.
8. The tofu/cloudflare-dns/records.tf comment still said deletes are refused. Fixed. This changes
   that stack's inputs; its plan stays empty, so no approval is needed.
9. With tofu-state deleted on origin, fetch_state left the old remote-tracking ref and every reader
   used stale holds/records. → fetch_state `update-ref -d` the local copy. The first version of the
   test deleted the branch by `git push :ref` from the same clone, which also deletes that clone's
   tracking ref, so it passed on old code; it now deletes the branch in the bare origin.
10. There were 8–10 ls-remote+fetch per apply. → `fetch_state(fresh=False)` reuses this process's
    last fetch (`_FETCHED`). `state_head` uses it; sync_state, _state_copy and pending's pass start
    stay fresh. The ff-only push still catches a race
    (test_a_cached_parent_still_never_overwrites_a_branch_that_moved).
    test_a_record_fetches_once... now asserts zero round-trips inside the section.

## Actions & outcomes
- New tests run against 36e85ba's src (git stash of src/) → all 13 fail; on the new src they pass.
- `nix develop --command bin/check` → OK, 493 passed, all gates.

## Graveyard — tried & abandoned
- Reclassifying NOT_STARTED in apply() after writepath returns → abandoned: the final ledger
  record would already say `failed`. A `not-started` recovery in writepath keeps the record true.

## Follow-ups / open threads
- Carried over: the Technitium record-delete confirmation on the first vhost removal; the fenced
  docker-dmz drill; the `mac_addresses` schema gap (fails safe).
