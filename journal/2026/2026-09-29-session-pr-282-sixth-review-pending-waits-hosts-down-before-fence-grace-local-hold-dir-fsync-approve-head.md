---
date: 2026-09-29
time: 19:13:18            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: PR 282 sixth review: pending waits, hosts down before, fence grace, local hold, dir fsync, approve HEAD
tier_touched: []        # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-025, PR #282, ADR 0008]
thread_status: open     # none | open | resolved | unknown; digest shows only explicit open
---

# 2026-09-29 · session · PR 282 sixth review: pending waits, hosts down before, fence grace, local hold, dir fsync, approve HEAD

## What happened
After the fifth-review commit 0c478be was pushed, Ali asked for another independent review.
`/code-review 282 max` (a fresh background run) returned 10 unverified findings. Each was checked
against the code, and all 10 held (#3 is partly by design). Ali said "fix again"; all 10 were fixed.
There were no live reads or writes.

1. `pve.pending(guest)` in snapshot() raised USAGE → refused → `_hold` held the revision until main
   moved, even after the operator cleared the pending change. Verify never looked for changes an
   apply left pending (a no-hotplug VM cores change), so a successful apply could block the next
   merge. → PENDING constant, UNAVAILABLE (backoff, alerts on the 3rd pass, never held); the snapshot
   except-branch prunes and re-raises it like USAGE. verify's `_pending_after` notes and alerts
   (priority 1) the guests left with pending keys, and a pending read error there is ignored.
2. Every fenced host had to answer after the apply, even one already down (a PR that raises
   docker-dmz's memory to fix an OOM → HOST_DOWN → restore to the broken sizing → held). →
   snapshot() probes `_answers` for each fenced context after taking the locks
   (`saved.answering`, with a "down before" note). verify and the restore proof wait only for hosts
   that answered before.
3. watch skipped the whole pass and pinged healthy for as long as a fence was held (up to the 6 h
   unit limit). → watch.json `_fence: {since}`. Past FENCE_GRACE_SECONDS (45 min), the pass
   observes as if unfenced, so an unreachable Docker host goes monitor → two strikes → alert + /fail.
   `since` is kept while the fence is held and dropped once it is released.
4. My fifth-review fix restored only the git hold. A revision held only in pending.json (git had
   refused the hold), then an `--ignore-hold` run that never started → `_clear_local_hold` removed
   the only hold. → `saved.held_locally` (`_held_locally`, also used by is_held), and
   `_release_prehold(keep_local=…)`.
5. atomic_write_bytes never fsynced the parent directory, so the rename was not durable. → open
   the directory O_RDONLY, fsync, close. The test records that fsync hits a regular file and then a
   directory.
6. `_hold` runs after writepath.run released the tofu lock but built on the cached STATE_REF
   (`state_head(fresh=False)`). → `fetch_state(repo)` before `set_hold`, inside the same try.
7. `plan --approve --ref X` wrote X's approval into the working tree of whatever was checked out.
   → Refuse with USAGE unless `resolve(ref) == resolve("HEAD")`.
8. `retry_cleanup` re-read operations.jsonl once per queued intent. → `_recorded_ids` read once
   per pass. `_recorded` uses it.
9. A long deploy made every 1-min pass run the full plan + schema, then hit LOCK_BUSY in
   snapshot(). → pending.json `_write_busy: {stack: revision}` is set when the snapshot step failed
   on LOCK_BUSY. The next pass returns `deferred` without planning while `ledger.busy()` still
   holds, and clears the mark once a pass gets through.
10. pve.py duplicated the secrets dir. → `common.SECRETS` + `common.secrets_dir()`. tofu `_secrets`
    and both SECRETS constants removed, along with pve's now-unused os/Path imports.

## Actions & outcomes
- 10 new or reworked tests (tofu: pending waits, pending-after alert, host down before, write-lock
  wait plans once, local-only hold kept, fresh fetch before a hold, approve HEAD only; watch: fence
  grace; common: directory fsync). With src stashed, all fail against 0c478be.
- Existing tests adjusted: the pending refusal now expects UNAVAILABLE + no hold; the planned-stop
  test allows the pre-apply probe; the running-deploy test expects one plan, then `deferred`.
- actuators.md updated (pending waits, host judged only if it answered, 45 min fence bound,
  approve HEAD). The SKY-025 status block gained a sixth-review sentence.
- `nix develop --command bin/check` → 509 passed, ruff + mypy clean, all gates OK.

## Graveyard — tried & abandoned
- For #1, failing verify when an apply leaves changes pending → rejected: the change is in the
  config and a rollback would undo a good change. Alert-only instead.
- For #3, timestamping the fence inside the lock file → not needed. Watch's own state records
  when it first saw the fence.

## Follow-ups / open threads
- Still open from earlier rounds: the drills after merge + ops VM rebuild. The VM drill should
  exercise the "host down before" path (a fenced docker-dmz update with dockerd stopped).
