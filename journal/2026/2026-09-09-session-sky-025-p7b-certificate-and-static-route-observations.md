---
date: 2026-09-09
time: 23:11:05            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: SKY-025 P7b certificate and static route observations
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-025, planning/sky-025-map.md, scripts/collect-certs.sh, scripts/collect-routes.sh]
thread_status: open
# resolves: [<episode-basename>, …]   # optional: close earlier episodes' open threads (append-only-safe)
---

# 2026-09-09 · session · SKY-025 P7b certificate and static route observations

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (journal/README.md). Distillation happens at READ time, never here. -->

## What happened
Recreated the deleted `phase/sky-025-p7b` worktree at remote-main
`b173e74142f6e57635a6b4f2a2e64b48800f2974`. Replaced the TLS and static Caddy shell readers with
Python collectors, forwarder shims, receipt markers and freshness requirements. One Luna worker
authored only synthetic certificate/route tests and fixtures; the lead integrated and re-ran them.

## Actions & outcomes
- `nix build --no-write-lock-file --no-link .#checks.x86_64-linux.skynet` → 239 installed tests,
  Ruff and mypy passed.
- `nix flake check --no-write-lock-file --no-build` → passed with existing system/app/deploy warnings.
- `bin/skynet collect omada --output /tmp/skynet-p7b-live.ll1uEw/network-gear.json --json` →
  T1 Viewer read succeeded: 1 site, 3 devices.
- `bin/skynet collect certs --output /tmp/skynet-p7b-live.ll1uEw/certs.json --json` → T1 probe
  succeeded: 7 declared endpoints, 7 reachable.
- `bin/skynet collect routes --repo /tmp/skynet-sky-025-p7b --output
  /tmp/skynet-p7b-live.ll1uEw/routes.json --json` → static checkout parse succeeded: 9 routes.
- `bin/skynet collect-status --repo /tmp/skynet-p7b-live.ll1uEw --json` → exit 3 as expected;
  isolated direct observations do not create whole-collection freshness evidence.

## Graveyard — tried & abandoned
Negative results are memory too. Anything attempted that did NOT work — and *why* — so a future
cold agent doesn't re-walk the dead end. Leave a single "— nothing abandoned —" line only if the
episode genuinely tried no path it dropped.

- Treating the isolated direct observations as a full default collection → abandoned because that
  would contact unrelated P4–P6 endpoints and write receipt-bound inventory outside this slice.

## Follow-ups / open threads
- P7b must be human-merged before the lead details P7c recon. P7 remains unaccepted at 6/24;
  P7c and the independent merged-result review are still required.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
