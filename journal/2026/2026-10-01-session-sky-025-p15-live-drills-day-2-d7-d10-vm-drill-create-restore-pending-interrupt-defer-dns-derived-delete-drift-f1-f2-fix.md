---
date: 2026-10-01
time: 20:47:50            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: SKY-025 P15 live drills day 2: D7-D10 (vm-drill create/restore/pending/interrupt/defer, DNS derived delete, drift) + F1/F2 fix
tier_touched: [T1, T2]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-025, PR #291, PR #292, PR #293, PR #294, PR #295, PR #296, PR #297, PR #298, PR #299, VM 10099, CT 10030, VM 10015, ADR 0008]
thread_status: open     # none | open | resolved | unknown; digest shows only explicit open
resolves: []
---

# 2026-10-01 · session · SKY-025 P15 live drills day 2: D7-D10 + F1/F2 fix

## What happened
Continued the campaign from day 1 (2026-09-30 episode) after a session restart; the scratchpad
evidence and the ~/skynet-drill worktree survived. Timer still inactive. vm-drill was declared
as tofu/proxmox-core/vm-drill.tf: full clone of 9000, VMID 10099, pool ops-managed, 1 core, 1 GiB,
VLAN 100, 10.10.100.99/24, pinned MAC BC:24:11:64:63:00, agent off, on_boot false,
reboot_after_update = false, plus an entity exception in invariants.json (first commit missed the
exception — the Edit was rejected for an unread file — so the approval was re-run on the final
commit). Ali approved the D8 kill ("You may kill") and, asked whether the agent could destroy
10099, chose "Yes, destroy 10099" (one-off API destroy, not an executor action).

## Actions & outcomes
- D7a #291 merged 893930c. 20:47 (39 s) → success, create, post_apply_plan clean. 10099 running in
  ops-managed, net0 virtio=BC:24:11:64:63:00,tag=100, ipconfig0 10.10.100.99/24 gw .1, onboot 0,
  balloon 0. No snapshot on it; 10030/10015/9000 snapshot lists unchanged.
- D7b #292 (memory.floating 2048 > dedicated 1024, hash 10ca0bb6…) merged a056a9d. 20:55 (27 s) →
  "rolled-back — tofu apply failed (recovery: rolled-back)"; running; digest ae722fa362a7
  unchanged; snapshot pruned; hold c9f71fb; one new hold-alert key. Proxmox refused before
  writing; nothing to write back.
- bin/check while building D7c: 1 failed / 517 passed, green on rerun (name not captured; F2 rate).
- D7c #293 (cores 1→2, floating dropped, hash 11f5b44c…) merged 731d4bd. 23:21 (28 s) → success,
  "pending: left — qemu/10099@server-proxmox-core (cores)", "alert ok", post_apply_plan clean.
  /pending: {key: cores, value 1, pending 2}; status cpus 1.
- D8 #294 (vm-drill description, hash 090b0788…) merged ef1562d.
  - 23:26 `--pending` → "refused — qemu/10099@server-proxmox-core has pending config changes; apply
    or revert them (retried each pass)", failures 1, due +60 s, no hold, no snapshot (F1 class).
  - 23:26:37 POST qemu/10099/status/reboot (timeout 120) → task OK 23:26:41; cpus 2, pending [].
  - 23:27:28 d8-kill.sh: `skynet tofu apply --pending &`, poll `pgrep -f "tofu -chdir=.* apply
    -no-color"` every 50 ms → tofu pid 2964802, parent 2963500 (.skynet-wrapped) seen
    23:27:45.976; `kill -9 2963500` at 23:27:45.979; orphaned tofu exited 23:27:47.814. Ledger:
    dangling `started` b5fe4142b6b2; tofu-state 550b09a PREHOLD; snapshot skynet-b5fe4142b6b2
    kept; local state digest unchanged. Live description still the template's ("SKY-008 base
    cloud-init template …"); the config digest moved only because the snapshot adds `parent`.
    tofu died with its pipe before writing anything.
  - 23:28:02 `--pending` → exit 4 "rollback-failed — interrupted tofu apply; state recorded as tofu
    wrote it; snapshots skynet-b5fe4142b6b2 kept; check by hand", alert ok, hold "interrupted
    apply" (0f3909d), then "held — revision refused or failed".
  - 23:28:40 `skynet tofu apply proxmox-core --ignore-hold` → success; description live;
    applied.json ef1562d; hold cleared; its own snapshot pruned. 23:29:27 pve.delete of
    skynet-b5fe4142b6b2 (excluded set passed) → snapshots ['current'], pending [], _cleanup [].
- D9b-1 #295 (vhost tofu-drill.aliammar.net → 10.10.100.72:8080 i.e. svc/librespeed; one derived
  create, hash faa96b30…; plan also showed `+ apps_hosts_parsed = 12`) merged a6a6959. caddy-apps
  deploy success 18:33:39 UTC (timer). 23:33 technitium-dns (21 s) → success. dig @10.10.70.51
  before: empty; right after: empty; +30 s: NOERROR A 10.10.100.35 (the write goes to TECH_HOST
  10.10.70.50; zones/records/get showed the record at once). curl --resolve …:10.10.100.35 → 200
  ssl_verify=0. watch: caddy-apps, librespeed healthy.
- D9b-2 #296 (vhost removed + hand-listed technitium-network removed; 1 delete, 1 deferred, hash
  66c16edf…) merged 59fed4e. caddy-apps deploy success 18:38:01 UTC. 23:38 (25 s) → success,
  "deferred: announced — technitium_record.aliammar_net["technitium-network"]", post_apply_plan
  clean, applied.json lists the deferred address. dig: tofu-drill gone; technitium-network still
  10.10.60.35. Second pass silent. drift: "technitium-network: deferred (hard checkpoint)".
- D7d #297 (vm-drill.tf deleted + athena tag `drill` removed; 1 update, 1 deferred, hash
  ad24be82…) merged cb30aa0. 23:43 (32 s) → success, "deferred: announced —
  proxmox_virtual_environment_vm.vm_drill", post_apply_plan clean; athena digest back to
  cac0d0ab74c8; vm-drill untouched, running. drift listed vm_drill deferred.
- Destroy (Ali-approved, 23:45:04): identity check (10099 vm-drill, pool ops-managed, template 0,
  not in {635, 837, 2020, 5001}) → POST status/stop → DELETE qemu/10099?purge=1&destroy-
  unreferenced-disks=1 → task OK 23:45:08. Guests now [240, 731, 751, 2020, 3050, 9000, 9090,
  10015, 10030] (the D0 set). drift no longer lists vm_drill.
- Cleanup #298 (exception removed, docker-dmz tag removed, technitium-network restored; files
  byte-identical to the pre-drill blobs) merged 0a3e797. 23:51 (38 s) → proxmox-core success
  (fenced, "hosts: ok — docker-dmz", digest back to b1adee699e79), technitium-dns success (empty,
  hash c1ae0622… = D1's). tofu-state holds only applied.json + terraform.tfstate per stack.
- D10 23:51: `skynet tofu drift` → inventory/tofu-drift.txt "# tofu drift at 0a3e7971ff5a",
  proxmox-core/technitium-dns/cloudflare-dns: no changes; nothing deferred; idle --pending exit 0.
- Fix PR #299 (Full): writepath maps a NotStarted raised by preflight/snapshot to `unavailable`;
  tofu raises NotStarted for a pending guest; watch judges the fence at the pass start (`begun =
  now`). 5 new/reworked tests fail on main's src (stash of src/ only) and pass; 50/50 full-suite
  runs clean (F2 had failed ~1 in 17).

## Graveyard — tried & abandoned
- `begun = wall()` for the watch fix → still carried the jitter between two clock() reads; used the
  scheduled `now` (or time.time()) itself.
- invariants.json rewrite via json.dumps → reformatted the whole file; reverted and edited the one
  line.

## Follow-ups / open threads
- After #299 merges and the ops VM is rebuilt: `SKYNET_TOFU=/nonexistent skynet tofu apply
  proxmox-core` must record `unavailable` (fails at init, changes nothing).
- Not exercised live: the restore actually writing differing keys back, and its reboot-if-pending
  branch (every bad value was refused before Proxmox wrote anything); a deploy contending with a
  fenced apply (none was pending).
- O3: a superseded hold stays on tofu-state after an empty-plan success until the next real apply.
- O4: killing `skynet` mid-apply took tofu down with it via the closed pipe (~1.8 s), before any
  write.
