---
date: 2026-09-29
time: 13:24:23            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: PR 282 third review: host fence, derived DNS deletes, deferred guest deletes, input-bound approvals
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-025, PR #282, ADR 0008, VM 10015]
thread_status: open     # none | open | resolved | unknown; digest shows only explicit open
---

# 2026-09-29 · session · PR 282 third review: host fence, derived DNS deletes, deferred guest deletes, input-bound approvals

## What happened
Ali asked for an extensive review of PR #282 (HEAD ba2c284). `/code-review 282 xhigh` returned 10
findings. Ali asked for all of them fixed, favouring autonomy and the least manual intervention,
and chose one policy in the planning step: approved deletes of derived DNS records
(`technitium_record`, `cloudflare_dns_record`) are applied by the executor. A guest
delete/replace/forget is deferred: excluded from the plan with `-exclude` (tofu 1.11.8), alerted
once, never applied. Mid-run Ali said the Technitium token is probably already allowed to delete
records. The 09-02 journal recorded "Access was denied" for record delete. Not verified live: the
first supervised DNS delete will show it (a delete that does not land is held and alerts).

The findings and their fixes:
1. A tofu apply that reboots vm-docker-dmz could overlap a deploy there. The deploy then failed
   verification, rolled back, and opened a revert PR that the §3 gate can auto-merge.
   → `fences()` maps updated guests to Docker contexts through lab.json `docker_hosts` (10015 →
   docker-dmz). snapshot() takes the `write` lock and `fence-<context>` before any snapshot, held
   by an ExitStack until the record. Lock order is tofu → write. A busy lock gives LOCK_BUSY
   (contended: no count, no alert). After a clean re-plan, verify waits up to HOST_SETTLE_SECONDS
   (600) for `watch.docker_reachable`; a host that never answers is HOST_DOWN (FAILED) → config
   restore. The rollback proof re-checks the host. watch skips the whole pass while
   `busy(fence(context))`: states kept, no alerts, the ping still goes out. `Ledger.busy(name)` is
   parameterized.
2. A removed vhost blocked technitium-dns for good (every later plan still carried the refused
   delete). → `Stack.deletable`; `deferrable()`; `planned()` re-plans with `-exclude` for deferred
   addresses, and the deferred set is part of the hash. MAX_DELETES = 3 per apply. withdraw is now
   Authentik-only (its Cloudflare CNAME delete removed).
3. Computed attributes such as ipv4_addresses, unknown on update, made a guest update
   irreversible. → `Workspace.readonly()` reads `tofu providers schema -json`: computed and not
   optional/required. Live on proxmox-core: VM {ipv4_addresses, ipv6_addresses,
   network_interface_names}, CT {ipv4, ipv6}; neither overlaps RESTORE_COVERS.
4. A permanent source error was retried every minute forever. → `tofu validate -json` after init;
   `valid: false` is USAGE (held, alerts once). Per-stack backoff for unavailable: 60 s doubling
   to 3600 s; alert at the 3rd failure, then daily (`_bump`, `_backoff`, `_now`).
5. The approval was bound only to the hash. → `inputs_digest()` = sha256 of `git ls-tree -r` of
   the stack's paths minus approved-plan.json. The executor refuses STALE_APPROVAL (USAGE) for a
   non-empty plan; an empty plan needs no approval, so an auto-merged revert whose plan comes out
   empty is not held. The gate requires `inputs`. `skynet tofu plan --changed --approve`. Approve
   now also writes an empty plan's approval.
6. A move or import was treated as touching the whole resource. → typed markers @moved/@import/
   @delete; `*` only for creates, plus "wanted whole again".
7. A stack with no state failed on an empty-plan success. → `_record` with no local and no branch
   state commits applied.json only.
8. Data-source reads counted as changes. → `changes()` skips mode == "data".
9. The DR runbook said plan rebuilds the local state (it did not). → persist_pending hydrates
   missing/stale local state every pass; `_state_copy` hydrates when the tofu lock is free.
10. `cache.mkdir` crashed on OSError. → the plugin cache moved to state/tofu/plugins, with
    OSError → UNAVAILABLE; workspace setup OSError → UNAVAILABLE; `pending()` guards each stack and
    `run_apply` guards the pass against OSError.

A regression the change itself introduced was caught while updating tests:
`test_a_refused_plan_never_adopts_a_first_state` relied on a stray monolith state planning guest
deletes that were refused. Deferral made that plan "succeed" and adopt the copy. Fix: a bootstrap
(unadopted) state whose plan deletes or defers anything is refused (UNADOPTED_DELETES, USAGE). This
covers DNS stacks too, where deletes are now allowed.

Budget: validate + schema + replan + replan_show + 2 × settle pushed STACK_BUDGET to 18 820 s, over
5 h − margin. PASS_SECONDS and TimeoutStartSec went to 6 h.

## Actions & outcomes
- `nix develop --command bin/check` → OK, 481 passed, all gates.
- `python -m skynet tofu plan {proxmox-core,technitium-dns,cloudflare-dns} --repo skynet-p15` (read
  only) → validate passed; 0 changes each; nothing deferred.
- The live `providers schema` read and `all_docker_hosts` → {10015: 'docker-dmz'}.
- Docs amended: AGENTS.md §4 + §6 (derived DNS record not payload), system-design §1a/§4, ADR 0008,
  actuators spoke (table + prose), architecture, identity-and-proxy, runbooks
  forward-auth/internal-route/public-tunnel/DR-core-node.

## Graveyard — tried & abandoned
- Watch reading a fence from in-flight ledger entries (context.fences) → abandoned. A crashed
  apply's `started` record would hide the host whenever any deploy held the lock. A flock dies with
  its holder, so `busy(fence-<ctx>)` can never go stale.
- Making `busy()` check both write and tofu locks globally → abandoned. It would stall automerge
  settlement and watch during every long non-Docker apply. Only a fenced apply takes `write`.
- A bin/check gate requiring a fresh inputs digest on every approved-plan.json → abandoned. An
  auto-merged revert of compose/caddy-apps changes a technitium-dns input and could never pass
  bin/check (the §3 gate requires it green). Freshness is enforced by the executor only for a
  non-empty plan.

## Follow-ups / open threads
- `mac_addresses` on the VM is not computed-only in the bpg schema. If a plan ever shows it unknown,
  that update is still judged irreversible (held + alert, fails safe).
- First supervised vhost removal: confirms the Technitium token's record-delete.
- The live drills (LXC + VM rollback) still gate the timer; add a fenced docker-dmz update drill
  (HOST_DOWN path) to the VM drill list.
