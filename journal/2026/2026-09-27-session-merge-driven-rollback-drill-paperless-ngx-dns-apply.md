---
date: 2026-09-27
time: 10:13:37            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: merge-driven rollback drill, paperless-ngx, DNS apply
tier_touched: [T1, T2]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-025, PR #270, PR #271, PR #272, PR #273, PR #274]                # SKY-###, PR #NNN, ADR NNNN, hosts — anything to cross-link
thread_status: open     # none | open | resolved | unknown; digest shows only explicit open
# resolves: [<episode-basename>, …]   # optional: close earlier episodes' open threads (append-only-safe)
---

# 2026-09-27 · session · merge-driven rollback drill, paperless-ngx, DNS apply

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (journal/README.md). Distillation happens at READ time, never here. -->

## What happened
After P13 merged + ops-VM rebuild, repeated the rollback drill through the real path (merge →
skynet-deploy timer → `skynet deploy --pending`) and deployed paperless-ngx as the first new service.

## Actions & outcomes
- #270 merged (paperless-ngx 3.2.1 + redis broker @10.10.100.78, skynet-drill, Caddyfile route) →
  09:38 tick: caddy-apps, paperless-ngx, skynet-drill all `success`; paperless created superuser
  "aliammar"; probe paperless.aliammar.net 302 → /accounts/login/. `skynet publish paperless-ngx` →
  success, 0 created.
- Saved DNS plan (full) wanted to REPLACE core_ct["athena"] (CT 10030): #206 changed the template
  and core_ct lacked ignore_changes=[operating_system]; the pool_ct→core_ct `moved` block pulls it
  into every plan, even targeted ("Moved resource instances excluded by targeting" → must also
  target `pool_ct`). Nothing applied. #271 added the lifecycle + sorted tags → plan 0 destroy.
- #272 merged (drill healthcheck `false`) → 09:45 tick: `rolled-back — compose up failed`,
  rollback-target ok running 050293c, revert-pr ok #273 (opened by aliammar-skynet). 10:05/10:09
  ticks: `held`. #273 merged → 10:12 tick `success`, hold released.
- DNS: saved plan from main 4c7d9b1, targets pool_ct + core_ct["athena"] + 2 records → create
  paperless + homeassistant A → 10.10.100.35 (no-op athena/adguard-core). Ali approved.
  `TOFU_APPLY_SCOPE=technitium-dns scripts/tofu-apply.sh` → "2 added"; its post-apply verify said
  `tofu plan exit 1` because it plans the whole root with only technitium creds ("No value for
  required variable proxmox_endpoint"). Full-cred plan after: only pbs + ubuntu_2404_base in-place
  drift. .51 resolver lagged the new paperless record by ~1 min.
- Dry-run missed Caddyfile-only changes (bind-mounted files aren't in the compose model) → fixed
  in #270 (`(files) | changed: …`).
- My `git commit -a` swept the checkout's uncommitted nightly inventory/docs into the drill commit;
  reset before push. A heredoc also broke an `&&` chain and committed this episode as an empty
  template first.

## Graveyard — tried & abandoned
- `-target` the two DNS records only → refused: moved instances must be targeted too.
- GitHub webhook for merge-to-deploy → declined: an internet-facing path toward the ops VM widens the
  agent's reach; chosen instead: 30 s `git ls-remote` poll (Phase 14).

## Follow-ups / open threads
- skynet-drill containers + /opt/docker/services/skynet-drill after #274 merges (manual; Phase 14
  item 7 automates retirement).
- tofu-apply.sh post-apply verification false-negative on scoped applies until Phase 15.
- Host fact `failed=4c7d9b1…` for skynet-drill stays until retirement (commit clears `failed` only
  when it equals the new target).

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
