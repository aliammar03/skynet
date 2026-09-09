---
date: 2026-09-09
time: 23:24:31            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: SKY-025 P7c bounded Python reconnaissance
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-025, planning/sky-025-map.md, scripts/recon.sh, runbooks/recon.md]
thread_status: open
# resolves: [<episode-basename>, …]   # optional: close earlier episodes' open threads (append-only-safe)
---

# 2026-09-09 · session · SKY-025 P7c bounded Python reconnaissance

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (journal/README.md). Distillation happens at READ time, never here. -->

## What happened
Replaced the T1 reconnaissance shell implementation with `skynet recon`. The Python command passes
one fixed marker-producing read-only probe to local bash or to a remote `svc-ops` session; it does
not interpolate the target into a shell command. A Luna worker wrote only fake-subprocess tests and
fixtures. The initial installed test run showed that a marker stream with metadata and one section
was accepted; the lead changed the parser to require every fixed section boundary.

## Actions & outcomes
- `nix build --no-write-lock-file --no-link .#checks.x86_64-linux.skynet` → 249 installed tests,
  Ruff and mypy passed.
- `bin/skynet recon local --json > /tmp/skynet-p7c-live.QVa2ai/local.json` → exit 0, nine sections,
  local unprivileged `aliammar@vm-skynet-ops` observation.
- `bin/skynet recon docker-dmz --json > /tmp/skynet-p7c-live.QVa2ai/docker-dmz.json` → exit 0,
  nine sections, remote `svc-ops@vm-docker-dmz` observation.

## Graveyard — tried & abandoned
Negative results are memory too. Anything attempted that did NOT work — and *why* — so a future
cold agent doesn't re-walk the dead end. Leave a single "— nothing abandoned —" line only if the
episode genuinely tried no path it dropped.

- Accepting a truncated marker stream as a partial healthy observation → abandoned because an
  interrupted remote script must be unavailable; only individual command results may be partial.

## Follow-ups / open threads
- P7c must be human-merged, then a fresh review covers P7a #235, P7b #236 and this P7c PR.
  Accepted progress remains 6/24 until that reviewer accepts the complete numbered phase.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
