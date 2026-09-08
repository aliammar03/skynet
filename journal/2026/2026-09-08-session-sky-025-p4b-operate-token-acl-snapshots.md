---
date: 2026-09-08
time: 23:36:41            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: SKY-025 P4b operate-token ACL snapshots
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-025, "#220", planning/sky-025-map.md]
thread_status: open
---

# 2026-09-08 · session · SKY-025 P4b operate-token ACL snapshots

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (journal/README.md). Distillation happens at READ time, never here. -->

## What happened
Started from merged P4a commit `67e1471987eb14f2f209db0d6ee4bed57386bd1f` in
`/tmp/skynet-sky-025-p4b`. Replaced the two shell `/access/permissions` readers with Python
explicit-output ACL collectors. The shared literal credential parser selects only
`PVE_TOKEN_OPERATE` for this endpoint; it validates the path/privilege shape before atomic output.
Default collection records two ACL markers under the existing receipt and status now rejects any
missing, failed or stale core/network observation or ACL marker.

## Actions & outcomes
- `nix develop --no-write-lock-file -c pytest -q` → 104 passed before the final ACL-failure test;
  final full validation is pending.
- Used fake HTTPS, synthetic tokens and temporary paths only; no live endpoint, credential file,
  ACL/pool mutation, grant, root, timer or service action occurred.

## Graveyard — tried & abandoned
Negative results are memory too. Anything attempted that did NOT work — and *why* — so a future
cold agent doesn't re-walk the dead end. Leave a single "— nothing abandoned —" line only if the
episode genuinely tried no path it dropped.

- Keep `collect-proxmox-acl.sh` as a parser/client → abandoned because P4b owns removing that shell
  implementation; the retained file is a packaged-command forwarding shim.

## Follow-ups / open threads
- Run full checks, regenerate digest/context, commit/push/open the P4b PR. After Ali merges it,
  request one fresh Astra Medium review covering both P4 slices before P5.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
