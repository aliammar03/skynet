---
date: 2026-10-03
time: 09:18:37            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: SKY-025 P15 live write-back drill: timer-applied creates, F3 restore reboot timeout, forced-restart re-run passes
tier_touched: [T1, T2]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-025, PR #299, PR #300, PR #301, PR #302, PR #303, PR #304, VM 10099, VM 10098, ADR 0008]
thread_status: open     # none | open | resolved | unknown; digest shows only explicit open
---

# 2026-10-03 · session · SKY-025 P15 live write-back drill: timer-applied creates, F3 restore reboot timeout, forced-restart re-run passes

## What happened
Ali merged #299 (F1/F2) and #300 (promotion) and rebuilt the ops VM. Checks 09:18 PKT: installed
/nix/store/3yzjp3c…-skynet-0.1.0 writepath.py/watch.py == main; `skynet-tofu.timer` enabled,
ticking each minute; no tofu record since 10-01 (neither merge touched a stack). F1 re-drill
09:18:47: `SKYNET_TOFU=/nonexistent skynet tofu apply proxmox-core` → exit 3
"unavailable — tofu could not be started", no hold, failures 0.

Ali asked to run the live write-back (the open item from the promotion PR: every earlier rejected
value was refused before Proxmox wrote, so the restore had nothing to write back). Plan approved:
two throwaway VMs; one PR lands a change on A while B's value is rejected, so the failed apply
must write A back; A = vm-drill 10099 cores 1→2 with bpg's default reboot_after_update (the change
goes live by a bpg restart, so the write-back is left pending and forces the restart branch);
B = vm-drill2 10098 balloon 2048 > memory 1024. Ali also approved the end-of-drill API destroy of
both. Every apply this session was the timer's, not a hand-run pass.

## Actions & outcomes
- #301 (two creates, hash c5068e78…) merged 09:23:35 → timer applied it 09:24:04 (38 s): success,
  post_apply_plan clean; both running, no snapshot. First unattended production Tofu apply.
- #302 (land-then-fail, hash a4d9bee5…) merged 09:26:58. Poller (0.5 s) on 10099:
  09:27:30 snapshot skynet-efe1871712b0; 09:27:39 cores=2 pending (1→2) then qmstop+qmstart by
  bpg → 2 cpus live; 09:27:41 cores=1 pending (2→1): the executor's write-back PUT (digest CAS)
  accepted. Then `status/reboot` → task log "TASK ERROR: VM quit/powerdown failed - got timeout"
  (qmreboot 09:27:41–09:28:41; VM uptime 1 s, no agent, ACPI ignored). 09:28:44 record:
  "rollback-failed — tofu apply failed; rollback: guest rollback failed: qemu/10099: Proxmox task
  failed (snapshots skynet-efe1871712b0 kept)"; steps execute failed → state ok → rollback failed
  → alert ok; hold f68ab26 on tofu-state. FINDING F3. Hard stop, reported.
- Recovery (Ali: yes) 09:31:20: identity check, POST stop + start on 10099 → cpus 1, pending [],
  cores 1; pve.delete skynet-efe1871712b0 on both; both configs equal the pre-apply copies
  (digest aside); _cleanup [].
- F3 design: Ali first chose "graceful reboot, then force". The literal reboot→stop→start costs
  two more power tasks per guest: STACK_BUDGET 22 590 s > 21 300 s and FENCED_SECONDS 19 890 s >
  the 5 h watch grace. Ali then chose shutdown(forceStop, 120 s) + start: same behavior (Proxmox's
  reboot is a shutdown + start), budget 19 890 s / 17 190 s with OBSERVE_SECONDS 60 for the state
  check after a finished power task. #303: pve.restore restarts via _set_power(stopped) then
  _set_power(running); test_a_guest_that_ignores_acpi_never_fails_the_restore fails on main's src
  with "Proxmox task failed". Ali merged and rebuilt; installed pve.py == main.
- #304 (re-run: comment change moves main past the #302 hold; same hash a4d9bee5…) merged
  09:40:00. Poller: 09:41:00 snapshot skynet-1f3b75ccf9b6; 09:41:09 bpg stop/start, 2 cpus;
  09:41:11 write-back cores=1 pending; 09:41:11–09:43:12 qmshutdown 121 s (ACPI ignored again,
  forced at 120 s); pending applied at stop; 09:43:15 qmstart; 09:43:16 running, 1 cpu, nothing
  pending, snapshots gone. 09:43:20 record "rolled-back — tofu apply failed (recovery:
  rolled-back)"; steps execute failed → rollback ok; both VMs' configs equal the pre-apply copies;
  hold 1749011 on tofu-state; one new hold-alert key.

## Graveyard — tried & abandoned
- A plain `status/reboot` for the restore's restart → abandoned (F3): it times out, and fails the
  rollback, on any guest that ignores ACPI (booting, hung, no handler).
- Literal reboot → forced stop → start → abandoned: over the 6 h unit and the 5 h fence grace.

## Follow-ups / open threads
- Cleanup PR: both declarations removed (deferred, one alert), exceptions removed; then the
  Ali-approved API destroy of 10098 and 10099.
- vm-drill2's rejected balloon never reached Proxmox's config, so its restore wrote nothing; the
  write-back is proven on vm-drill only, which is the case that matters.
