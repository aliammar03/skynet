---
date: 2026-09-15
time: 18:12:37            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: P11 librespeed canary recovery and implementation-ready handoff
tier_touched: [T1, T2]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-025, PR #259, docker-dmz, librespeed, ADR 0007]                # SKY-###, PR #NNN, ADR NNNN, hosts — anything to cross-link
thread_status: resolved     # none | open | resolved | unknown; digest shows only explicit open
resolves: [2026-09-15-session-p11-immutable-generation-implementation-and-premature-librespeed-prepare.md]
---

# 2026-09-15 · session · P11 librespeed canary recovery and implementation-ready handoff

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (journal/README.md). Distillation happens at READ time, never here. -->

## What happened
The earlier P11 prepare reached the live host before disposable evidence was sealed and was refused
at the Arcane auto-sync guard. This session resolved that open episode and completed the authorized
single-service canary on `docker-dmz` (`10.10.100.15`) through the documented `svc-ops` T2 path.

The host provided UID 1002 `svc-ops`, membership in the `docker` group, Docker Compose v5.4.0, and
persistent ext4 storage. The selected protected state root is
`/home/svc-ops/.local/state/skynet-deploy`; the existing `/home/svc-ops` directory is owned by
`svc-ops` and mode `0700`. No new Docker or root grant was added.

## Actions & outcomes
- Disposable generation and activation probes passed exact Git materialization, failed preparation
  atomicity, secret custody, idempotent prepare, path/symlink/archive safety, Compose validation,
  lock exclusion, enabled-auto-sync refusal, OLD/OLD → NEW/NEW coherence, ambiguous transport
  refusal, same-generation recovery, Docker generation identity, complete health/route verification,
  promotion, failed-candidate retention, runtime rollback without Git mutation, compatibility
  forwarders, and source/installed package smoke surfaces.
- The initial live health check observed one container still starting, so verification withheld
  promotion. Same-generation reconciliation was run after the prior lock was gone; the container
  then became running and healthy, and the candidate was independently verified and promoted.
- Arcane Git Sync for `librespeed` was disabled and drained before direct activation. The old exact
  revision was verified before takeover. Arcane remained able to display the externally Compose-managed
  project as running, which is retained as observation only.
- The canary prepared and directly activated exact full revision
  `f8072b390c10957a572eda4aa112da0583e46796`. Docker generation labels identified that revision;
  one expected container was running and healthy; `speed.aliammar.net` passed the DMZ probe with
  HTTP 200 and TLS verification result 0.
- Remote state ended truthfully at `active=stable=f8072b390c10957a572eda4aa112da0583e46796` and
  `previous=null`. The effective remote `.env` was mode `0600`. A subsequent same-generation
  deployment reused the retained generation without changing the container ID or release manifest
  modification time.
- The corrected implementation reports no stable rollback candidate when none exists; it does not
  invent one after a first successful promotion. P11 remains implementation-ready on PR #259 and
  awaits a completely fresh external review; accepted numbered progress remains P10.

## Graveyard — tried & abandoned
- Claiming the first health-starting observation was a failed deployment → abandoned because the
  operation had to remain candidate-active until the independent health check passed; same-generation
  recovery was the truthful next step.
- Reporting a previous stable rollback candidate for a first promotion → abandoned because
  `previous=null` is the correct state when no earlier verified generation exists.

## Follow-ups / open threads
- Start a completely fresh external review of open PR #259. Do not use the stale ACCEPT for the former
  Arcane Git Sync design, merge, or enter accepted closeout.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
