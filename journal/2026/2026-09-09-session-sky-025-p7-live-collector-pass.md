---
date: 2026-09-09
time: 23:37:11            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: SKY-025 P7 live collector pass
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-025, "PR #235", "PR #236", "PR #237"]
thread_status: open     # none | open | resolved | unknown; digest shows only explicit open
# resolves: [<episode-basename>, …]   # optional: close earlier episodes' open threads (append-only-safe)
---

# 2026-09-09 · session · SKY-025 P7 live collector pass

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (journal/README.md). Distillation happens at READ time, never here. -->

## What happened
From the P7c checkout, created an isolated `/tmp/skynet-p7-live.*` directory and ran the three P7
collectors plus local and `docker-dmz` reconnaissance. Each collector was given only a temporary
`--output` file; no production inventory path was supplied or changed. The Omada command consumed
its already-materialized read credential without printing it. No root grant, write capability,
service/timer change, or remote mutation was used.

## Actions & outcomes
- `bin/skynet collect omada --output <temporary>/network-gear.json --json` → exit 0; one site,
  three devices, string controller version, and every device had a `net/` entity ID.
- `bin/skynet collect certs --output <temporary>/certs.json --json` → exit 0; seven endpoints
  probed and seven reachable.
- `bin/skynet collect routes --repo <P7c checkout> --output <temporary>/routes.json --json` →
  exit 0; nine routes.
- `bin/skynet recon local --json` → exit 0; nine sections as `aliammar@vm-skynet-ops`.
- `bin/skynet recon docker-dmz --json` → exit 0; nine sections as
  `svc-ops@vm-docker-dmz`.

## Graveyard — tried & abandoned
Negative results are memory too. Anything attempted that did NOT work — and *why* — so a future
cold agent doesn't re-walk the dead end. Leave a single "— nothing abandoned —" line only if the
episode genuinely tried no path it dropped.

- Query each route object for a `host` key as an extra local structural check → abandoned because
  route schema does not promise that key; its collection receipt and count are the P7 contract.

## Follow-ups / open threads
- Delete the temporary snapshot directory after the result is recorded. P7 still needs PR #237
  human merge and a fresh independent review of #235–#237 before acceptance.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
