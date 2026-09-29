---
date: 2026-09-29
time: 18:47:07            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: PR 282 fifth review: deferred re-plan, pass isolation, ignore-hold restore, adopt cleanup, state ref CAS, fsync, DNS guards
tier_touched: []        # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-025, PR #282, ADR 0008]
thread_status: open     # none | open | resolved | unknown; digest shows only explicit open
---

# 2026-09-29 · session · PR 282 fifth review: deferred re-plan, pass isolation, ignore-hold restore, adopt cleanup, state ref CAS, fsync, DNS guards

## What happened
Ali asked for an extensive review of #282 at 270e7b0. `/code-review 282 max` returned 10 findings.
#1 was verified against the code by hand; the rest were confirmed while fixing. Ali then said "fix
them please". There were no live reads or writes. The evidence is the offline suite plus local
`tofu` 1.11.8 experiments in the session scratchpad.

1. `Workspace.clean()` re-planned without the deferred `-exclude`s. Any apply that deferred a guest
   delete saw the delete again → no overlap → DRIFTED → UNSETTLED → rollback-failed, held, alarm, on
   every merge to the stack. FakeSpace.clean returned `host.drift` only, so the suite missed it.
   → `clean(exclude=state_.deferred)`. FakeSpace.clean now returns every un-excluded deferrable
   change, as real tofu would. The deferral test asserts `excluded_at_verify`, and it failed with
   the one line reverted.
2. `pending()` caught only OSError per stack. A WriteError from `held`/`is_held`/`input_revision`
   escaped, and `run_apply` replaced every collected result with one "unavailable" (losing an
   earlier stack's exit 4). → The per-stack try now covers input_revision + applied + _pending_stack
   and catches WriteError too, counting under the target (or "unknown"). `_pending_stack`'s
   post-apply `is_held`/`_announced` is wrapped too, so it cannot replace the apply's own result.
3. `--ignore-hold` + tofu not starting: `_prehold` overwrote the failure hold with PREHOLD, and
   `_release_prehold` deleted held.json, so the timer would re-apply a rolled-back revision.
   → `_prehold` returns the hold it replaced (None = git refused). `_release_prehold` writes it back
   and keeps the local hold when it covers the revision.
4. `adopt()` raising after the snapshots + prehold → `_stop` "refused". The snapshots were orphaned
   (`_drop_intents` dropped their intents) and PREHOLD was left. → `_undo_snapshot` (release the
   prehold, prune), shared by an adopt failure and the NotStarted rollback.
5. `fetch_state` force-fetched into STATE_REF outside the tofu lock (drift, plan, pending's
   start). → It fetches into `refs/skynet/fetch/tofu-state-<pid>` and moves STATE_REF with
   `git update-ref STATE_REF new old` (compare-and-swap). A ref that moved meanwhile is left alone.
   The branch-gone delete is a CAS too. A swap refused while the ref still sits at `old` is a git
   failure and raises "state branch unreadable". Verified in a scratch repo: a stale old value is
   refused, and an empty old value means "must not exist". `_state_copy` re-reads the branch under
   the lock before hydrating.
   First attempt was wrong: `git fetch origin +refs/heads/tofu-state:<private>` ALSO updates
   refs/remotes/origin/tofu-state through the remote's configured refspec (git's opportunistic
   tracking-ref update), so the fetch still wrote STATE_REF directly and the CAS saw new == old.
   The swap-failure test caught it ("DID NOT RAISE"). → `git fetch --refmap= ...`. Both ref tests
   fail with `--refmap=` removed and pass with it; the race test moves the ref during the fetch.
6. `_write` had no fsync and leaked its temp file on error. → `common.atomic_write_bytes`
   (`atomic_write_text` now delegates to it; mkstemp 0600 as before).
7. `check` blocks only warn. In a scratch dir, tofu 1.11.8 gave `check` assert false → exit 0 +
   "Warning: Check block assertion failed", and output precondition false → exit 1 "Module output
   value precondition failed". → Both DNS stacks now use `output "<x>_parsed" { precondition }`.
   A scratch run confirmed that an apply with `-exclude` still records the output, so the verify
   re-plan exits 0. `tofu validate` passes on both stacks. No stack carries an approved-plan.json,
   so no approval went stale.
8. `_announce_deferred` also ran for refused/unavailable outcomes, marking addresses announced
   before any run left them pending. → Only outcomes other than refused/unavailable announce.
9. `all_docker_hosts`/`main_excluded` ran a `git archive` of main for one JSON file. → `git show
   origin/main:<file>` (`_main_file`). `_blob` went from ls-tree + cat-file to one `cat-file --batch`
   (plus the existing ref check, which keeps the non-repo test fixtures' "no branch" behavior).
10. writepath's `recovery == "not-started"` sentinel → `writepath.NotStarted(WriteError)`. `_run_locked`
    maps it to `unavailable` only when execute itself raised it and the rollback succeeded. tofu's
    rollback returns "not-needed".

## Actions & outcomes
- 9 new regression tests (6 tofu, 2 writepath, 1 common), plus the reworked deferral assertion.
  With the src changes stashed, the new tofu tests fail against the old code.
- `nix develop --command bin/check` → 502 passed, ruff + mypy clean, all gates OK.
- actuators.md: the deferred set is excluded from the verify re-plan and announced by the first
  run that applies the rest; `--ignore-hold` never-started puts the old hold back.

## Graveyard — tried & abandoned
- `_blob` as a single `cat-file --batch` with no ref check → the fake-repo tests (tmp_path not a
  git repo) turned "no branch" into "state branch unreadable". Kept `_has_state_ref` first.
- A `lifecycle { precondition }` on the record resources for #7 → dropped: with zero parsed hosts
  the for_each is empty, so no instance exists to evaluate it. A `terraform_data` guard → dropped:
  it is a type outside the stack's allowlist, and `refuse()` would reject it.

## Follow-ups / open threads
- The first merge after this change plans an output-only diff on both DNS stacks (no resource
  changes → success with no apply). The output is recorded on the next real apply.
- Still open from earlier rounds: the drills after merge + ops VM rebuild.
