---
date: 2026-09-26
time: 17:08:47            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: SKY-025 P11 purge and live collect findings
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-025, SKY-028, docker-dmz, pbs] # SKY-###, PR #NNN, ADR NNNN, hosts — anything to cross-link
thread_status: open     # none | open | resolved | unknown; digest shows only explicit open
# resolves: [<episode-basename>, …]   # optional: close earlier episodes' open threads (append-only-safe)
---

# 2026-09-26 · session · SKY-025 P11 purge and live collect findings

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (journal/README.md). Distillation happens at READ time, never here. -->

## What happened
SKY-025 Phase 11 (Light) on branch `phase/sky-025-p11-purge`, one Claude Code session, no
delegation. Deleted the 24 shell forwarders/stubs, added `src/skynet/common.py`, and made
`collect all` a single loop over `collection.COLLECTORS`. Ported `bin/plan`/`bin/new` to
`skynet plan`/`skynet new` and added `skynet` to the ops VM `environment.systemPackages`.

Live T1 exit evidence, `nix develop -c skynet collect all --repo .` at ~17:00 PKT → exit 3:
proxmox-core/network, both ACLs, dns, opnsense, network-gear, certs, routes = success;
`pbs: unavailable` (remote transport unavailable) and `docker-docker-dmz: unavailable` (Docker
context or command unavailable). `skynet collect-status --repo .` → exit 3. The same two collectors
from a `git worktree` of origin/main (`nix run .#skynet -- collect pbs|docker …`) fail
identically, so the refactor did not cause this.

Probes: `echo > /dev/tcp/10.10.20.40/8007` → unreachable. `/dev/tcp/10.10.100.15/22` → open, but
`docker --context docker-dmz ps` → ssh exit 255 with `WARNING: REMOTE HOST IDENTIFICATION HAS
CHANGED!` for 10.10.100.15. Did not touch known_hosts. Inventory churn from the run was reverted, not
committed.

Gotcha: `nix develop`/`nix run` build from the git tree, so new untracked `src/skynet/*.py` files
are invisible (ImportError: cannot import name 'common') until `git add`.

## Actions & outcomes
- `skynet plan list` vs old `bin/plan list` on the same tree → byte-identical planning/README.md.
- Scratchpad triage (Ali's choice): deleted 2026-08-17.md, lint-gate note → SKY-028 via
  `skynet plan idea <file>`, declarative-future + 7 research notes → journal/2026/*-session-*.md.
- `bin/check` → OK (ruff, mypy, pytest, invariants).

## Graveyard — tried & abandoned
- — nothing abandoned —

## Follow-ups / open threads
- docker-dmz (10.10.100.15) SSH host key changed: Ali must verify the new key out-of-band before
  anyone updates known_hosts. Until then Docker inventory is stale and `collect-status` is red.
- PBS 10.10.20.40:8007 unreachable from the ops VM (VLAN 90): check the PBS host (CT 240) and the
  firewall path.
- After merge, run `rebuild` on the ops VM before the 03:30 nightly (the nightly now calls `skynet`
  from PATH).

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
