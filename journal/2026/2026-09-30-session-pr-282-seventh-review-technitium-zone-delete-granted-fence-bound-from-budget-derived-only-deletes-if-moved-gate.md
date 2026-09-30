---
date: 2026-09-30
time: 11:18:39            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: PR 282 seventh review: technitium zone delete granted, fence bound from budget, derived-only deletes, if-moved gate
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-025, PR #282, SKY-008, ADR 0008]
thread_status: open     # none | open | resolved | unknown; digest shows only explicit open
---

# 2026-09-30 · session · PR 282 seventh review: technitium zone delete granted, fence bound from budget, derived-only deletes, if-moved gate

## What happened
d763b58 was pushed and another `/code-review 282 max` ran: 9 unverified findings. Ali asked
whether the phase is production-ready; the answer was "stop reviewing after this round, merge,
drill". Ali then said: check the token's delete permission, fix the fence limit, fix the rest.

Live T1 read (read-only GETs through `skynet.dns`, token never printed):
- `user/session/get`: user `svc-ops`, token name `ops`, section Zones
  {canView, canModify, canDelete} all true.
- `zones/permissions/get?zone=aliammar.net`: group `ops` canDelete **false** (Administrators, DNS
  Administrators, and user admin all true). The zone-level flag is the narrower one; it matches
  SKY-008's live observation that the token could not delete records. No delete was attempted.
- Ali then updated the zone permissions in the Technitium UI (a human T3 admin action). Re-read:
  group `ops` on aliammar.net is canView/canModify/canDelete **true**. Note: zone-level Delete in
  Technitium may also permit deleting the zone itself, not only records; tofu never manages the
  zone object (records only).

Fixes, one per finding:
1. retry_cleanup and _drop_intents treated an unreadable operations.jsonl as "recorded", dropping
   crash-left snapshot intents (this predates the PR). → Unreadable (ids None) keeps the intent
   and skips it. `_recorded` stays True-on-unknown only for `_held`'s message.
2. The fence bound (45 min) was shorter than a legitimate fenced write. →
   `tofu.FENCED_SECONDS = STACK_BUDGET − 120 − pre-lock tofu steps` = 16120 s (4.48 h).
   `watch.FENCE_GRACE_SECONDS = 5 h`. A test pins grace ≥ FENCED_SECONDS. Trade-off: an unrelated
   outage on a fenced host stays quiet up to 5 h; the executor's own timeouts and OnFailure cover
   a hang.
3. technitium-dns `deletable` covered every technitium_record, including the 10 hand-listed
   `aliammar_net` vanity records. → `Stack.deletable` is now address prefixes:
   `technitium_record.apps_service`, `cloudflare_dns_record.tunnel`. `deferrable` matches
   `address == p or startswith(p + "[")`.
4. `_announce_deferred` marked addresses before the push. → Compute unseen addresses from facts,
   send, and mark only when the push went out.
5. A stale `_unrecorded` record could overwrite a newer applied.json. → commit() calls
   `_forget_unrecorded` after a recorded success. `persist_pending` also drops a stored record
   whose revision is a strict ancestor of the branch's applied revision (`_superseded`, git
   merge-base --is-ancestor).
6. dns-failure.md still said the token cannot delete records. → Rewritten: the executor deletes a
   removed vhost's derived record; a hand-listed record's removal is deferred.
7. The directory fsync, after the rename, raised OSError, so a completed write was reported as a
   failure. → Best effort: swallowed once the bytes are in place.
8. `plan --approve` into an unwritable tree gave a traceback. → "not approved: … unwritable", exit 3.
9. The timer fetched main + tofu-state every minute. → `skynet tofu apply --pending --if-moved`
   (timers.nix). `_quiet` does `deploy.remote_main` (ls-remote); it skips while head equals
   main-seen.json and now < due. due = now + 15 min only after a pass with zero results; any
   result (held, backoff, success) means the next tick runs.

## Actions & outcomes
- 10 new tests, plus the unit-string test now expecting `--if-moved`. With src + nix stashed,
  all 10 fail against d763b58.
- First version of the if-moved test was wrong: it expected ticks to run when main had not moved
  but a stack became pending. That cannot happen live (pending work arrives by a merge). The
  test was rewritten; the gate was not changed.
- actuators.md: fence bound 5 h, the if-moved gate, derived-delete scope. The SKY-025 status
  block gained a seventh-review sentence.

## Graveyard — tried & abandoned
- A 45 min fence grace (the sixth review) → too short for a slow fenced rollback; replaced by the
  budget-derived bound.
- Proving the token's delete by deleting a record → not done (a write); the zone permission read
  was enough.

## Follow-ups / open threads
- With delete granted, the records SKY-008 retired (the `*.aliammar.net` wildcard and the tofu-test
  record) can now be removed, by a human or a PR. Not done here.
- The drill prompt's D0 should confirm group `ops` canDelete on aliammar.net (now true).
