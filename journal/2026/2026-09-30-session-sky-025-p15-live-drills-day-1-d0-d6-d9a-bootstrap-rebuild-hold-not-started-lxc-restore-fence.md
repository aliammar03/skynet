---
date: 2026-09-30
time: 15:29:02            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: SKY-025 P15 live drills day 1: D0-D6 + D9a (bootstrap, rebuild, hold, not-started, LXC restore, fence)
tier_touched: [T1, T2]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-025, PR #282, PR #286, PR #287, PR #288, PR #289, PR #290, CT 10030, VM 10015, ADR 0008]
thread_status: open     # none | open | resolved | unknown; digest shows only explicit open
---

# 2026-09-30 · session · SKY-025 P15 live drills day 1: D0-D6 + D9a (bootstrap, rebuild, hold, not-started, LXC restore, fence)

## What happened
Ali pasted the P15 drill prompt. One AGENTS.md §2 plan for the whole campaign was posted; Ali
approved it with "fewer PRs" (folds: D7b's revert into D7c, D7c's waiting PR = D8's killed apply,
the technitium-network re-add into the cleanup PR), vm-drill = VLAN 100 .99 → VMID 10099, athena
D5 "any time". The `skynet-tofu` timer stayed inactive throughout; every pass was a hand-run
`skynet tofu apply --pending`. Drill PRs were built in the worktree ~/skynet-drill (the main
checkout holds the nightly's uncommitted inventory). Every merge was Ali's; GitHub records all
merges (#282 onward) under `aliammar-skynet`, the same account the agent's gh uses.

D0 (read-only): main 9c08420 contains #282. The installed package
(/nix/store/65d26ff…-skynet-0.1.0) tofu.py/pve.py/watch.py/writepath.py/common.py are byte-identical
to main. skynet-tofu.timer `linked`, `inactive (dead)`; the service runs `--pending --if-moved`,
TimeoutStartSec=6h. bin/check OK. The four secrets are sops-nix symlinks; targets 0400 aliammar
(stat -L; contents never read). `git ls-remote origin tofu-state` empty. Technitium
zones/permissions/get?zone=aliammar.net → group ops canView/canModify/canDelete all true.
Before facts: core node 12 threads (i7-8700K 6c); athena running, cores 4, tags
nixos;obsidian;skynet, no snapshot, digest cac0d0ab74c8; vm-docker-dmz running, tags
community-script, pre-existing snapshot pre-update-20260816-1358 (left alone), digest
b1adee699e79; 9000 stopped. Local state sha256: proxmox-core 903f7d5b…, technitium-dns fcb78fa1…,
cloudflare-dns 81738d87….

## Actions & outcomes
- D1 15:29 PKT: `skynet tofu drift` → 3× "no changes" (32 s). `apply --pending` (36 s) →
  proxmox-core/technitium-dns/cloudflare-dns @9c084200ec53: success. tofu-state created, head
  c04ed50: `<stack>/applied.json` + `<stack>/terraform.tfstate` each. Branch blob == local file
  for all three. Blob top keys: encrypted_data, encryption_version (v0), lineage, meta, serial —
  no `resources` array; grep for `"resources"|"instances"|aliammar.net|10.10.` → 0 hits each.
  Second pass: no output, no ledger line, branch unchanged.
- D2 15:30: renamed state/tofu → tofu.d2-aside. `--pending` (2.9 s) → "success — local state
  rebuilt from tofu-state" ×3; operations.jsonl stayed 79 lines (no apply). cmp: rebuilt ==
  branch == aside for all three; .base files identical; mode 0600. Moved legacy/ and plugins/
  back, kept a copy of the aside pending.json in the scratchpad, removed the aside dir.
- D9a (read-only, scratch commits never pushed): empty Caddyfile → `plan technitium-dns` exit 2
  "merged source does not validate (tofu validate)". A hand `tofu validate -json` on the same tree:
  "Module output value precondition failed | No app vhosts parsed …". Same for an empty
  cloudflared config.yml ("No hostnames parsed … refusing to wipe public CNAMEs"). The output
  precondition fires at validate (file() is static), so under apply it is USAGE (held, alert
  once), not a retried failure.
- Value probes (scratch plans): athena cores=8193 → "tofu plan failed" (bpg validator). cores=16
  rejected as a drill value (Proxmox caps an LXC's cpuset, it does not reject). athena
  features.keyctl and docker_dmz memory.floating > dedicated + reboot_after_update plan fine.
- D3 #286 (athena tag `drill`, hash replaced by 64 zeros) merged ac41790. 17:56 → "refused — plan
  differs from the approved plan …", "hold: ok". tofu-state 3f4cfd0 hold ac41790. athena config
  byte-identical, no snapshot. pending.json _hold_alerts has 1 key. Two more passes: "held —
  revision refused or failed; awaiting a new merge", exit 0, no new alert key.
- D4 #287 (correct approval, hash 8e541944…) merged 5bd7501.
  - 18:05 `SKYNET_TOFU=/nonexistent` → "refused — tofu could not be started"; failures 1 + backoff,
    no hold, no snapshot (it died at `tofu init` in preflight). FINDING F1. Stopped and reported;
    Ali: exercise the real path, fix permanently before production.
  - 18:21 race: SKYNET_TOFU = symlink to the real tofu; a watcher polled athena's snapshot list
    every 0.15 s and unlinked the symlink at 18:21:21 when skynet-89fb35059f3b appeared →
    "unavailable — tofu could not be started", "prehold: ok", "prehold: released — nothing ran";
    tofu-state b3759fd hold → 38efbbd release (it restored the older ac41790 hold it replaced);
    snapshot pruned; athena unchanged; failures 2, no alert.
  - 18:23 normal pass (after the backoff) → success, 27 s; post_apply_plan clean; changed keys
    [digest, tags]; held.json gone; applied.json 5bd7501.
- D5 #288 (athena keyctl=true, hash 574ec208…) merged 92d0ecd. 18:35 (28 s) → "rolled-back — tofu
  apply failed (recovery: rolled-back)"; steps execute failed → rollback ok; athena running, whole
  config + digest 832cc2a2ecba identical, features nesting=1; snapshot pruned; hold e86f694; one
  new hold-alert key. Proxmox refused the PUT outright, so the restore wrote nothing back.
- bin/check on the D5 revert branch: 1 failed / 517 passed once, then green ×3. 15 more pytest runs
  → tests/test_watch.py::test_a_fence_held_past_its_grace_no_longer_hides_an_outage failed once.
  FINDING F2.
- D5 revert #289 (empty-plan approval 9651eeb1…) merged df91033. 19:04 (14 s) → success. The D5
  hold (92d0ecd) stayed on the branch: an empty plan never preholds, so nothing replaced or
  cleared it (O3; it only blocks its own revision). The next real apply (D6) cleared it.
- D6 #290 (docker-dmz tag `drill`, hash b0a6c5fc…) merged edd4ac8.
  - 19:10 `flock write.lock sleep 150` → pass 1 "refused — another write holds the lock",
    _write_busy recorded, failures 0; pass 2 "deferred — a deploy holds the write lock; planned
    again once it is free" in 2.9 s.
  - First fenced attempt invalid: `kill` hit flock, but its child `sleep` (pid 2189936) kept the
    inherited lock, so the "apply" only deferred again. pkill'd the sleep.
  - 19:13 fenced apply (30 s): lslocks showed pid 2193409 (.skynet-wrapped) holding write.lock and
    fence-docker-dmz.lock; `skynet watch` → "host/docker-dmz: skipped — a guest write is changing
    the Docker host", watch.json _fence {since: …}; `skynet deploy --pending` returned in 6 s
    (nothing pending, so it never asked for the lock; the lock is non-blocking: a contended deploy
    gets LOCK_BUSY and the 30 s timer retries it). Outcome success, "hosts: ok — docker-dmz",
    post_apply_plan clean, changed keys [digest, tags], no snapshot left. Next watch: no fence, all
    healthy.

## Graveyard — tried & abandoned
- `respond "ok" 200` for the D9b throwaway vhost → abandoned: deployment.route_vhosts requires a
  host:port backend for every route, so the whole route observation would be malformed and the
  caddy-apps deploy would fail verification (auto-rollback + self-merging revert PR). Used
  librespeed's backend instead.
- cores above the node count as the LXC rejected value → abandoned (capped, not rejected).
- Holding write.lock with `flock … sleep` then `kill $!` → the child keeps the lock; kill the
  holder process group or the sleep itself.

## Follow-ups / open threads
- F1, F2: fix before the promotion PR (Ali). O3 recorded.
- The restore's write-back of differing keys and its "reboot only if pending" branch have not run
  live (Proxmox rejected each bad value before writing).
- Merge identity: GitHub cannot tell Ali's merges from the agent's.
