---
date: 2026-09-15
time: 11:17:44            # local HH:MM:SS; orders same-day episodes in the digest
kind: incident         # session | incident | decision
title: P11 immutable generation implementation and premature librespeed prepare
tier_touched: [T1, T2]  # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-025, PR #259, docker-dmz, librespeed]
thread_status: open     # none | open | resolved | unknown; digest shows only explicit open
# resolves: [<episode-basename>, …]   # optional: close earlier episodes' open threads (append-only-safe)
---

# 2026-09-15 · incident · P11 immutable generation implementation and premature librespeed prepare

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (journal/README.md). Distillation happens at READ time, never here. -->

## What happened
During P11 CLI executor smoke work, `skynet deploy service librespeed --branch main` reached the
standing `svc-ops@10.10.100.15` path before the disposable integration suite was sealed. Generation
preparation published or reused
`/home/svc-ops/.local/state/skynet-deploy/librespeed/generations/f8072b390c10957a572eda4aa112da0583e46796`.
The next activation boundary observed the existing Arcane Git Sync with `autoSync=true` and refused
before Docker Compose mutation.

Main inspected the host immediately. The generation directory contained only `.env`,
`compose.yaml`, and `release.json`; each file was owned by `svc-ops:svc-ops` with mode `0600`, and
the directory chain was mode `0700`. There was no `active`, stable metadata, operation record, or
held deployment lock. Arcane still reported auto-sync enabled and the current project revision as
`f8072b390c10957a572eda4aa112da0583e46796`. Docker still showed the pre-existing container ID
`983d9d2a2458` running healthy from `/opt/docker/arcane-projects/librespeed`.

That read also exposed a real-Docker parser defect: the activation probe used `\\t` in a Go
template, but Docker emitted literal backslash-t bytes. The parser classified the healthy legacy
container as stopped. Main sent the defect to the activation executor and held all further live
mutation pending repair and independent disposable verification.

## Actions & outcomes
- Exact-revision prepare over bounded SSH stdin → generation became visible on docker-dmz early;
  no Compose activation or state promotion occurred.
- Arcane pre-write guard → refused activation because the service still had `autoSync=true`.
- Direct Docker label and state inspection → old Arcane working directory, same container ID,
  running state, and healthy healthcheck remained intact.
- Filesystem state inspection → no active/stable/previous pointer and no operation record existed.
- Real Docker activation status probe → found literal-delimiter incompatibility and routed it for
  repair before the canary.

## Graveyard — tried & abandoned
Negative results are memory too. Anything attempted that did NOT work — and *why* — so a future
cold agent doesn't re-walk the dead end. Leave a single "— nothing abandoned —" line only if the
episode genuinely tried no path it dropped.

- Treating `\\t` inside the Docker inspect Go format as a real tab → abandoned because Docker
  v29 emitted literal `\\t` bytes; the fixed-format parser needs an actual safe delimiter.

## Follow-ups / open threads
- Re-run the full generation preparation verification after the independent tester's four defects
  are repaired.
- Independently verify activation and reconciliation against disposable Docker state, including
  the exact real label parser contract.
- Only after those checks pass, continue the authorized `librespeed` disable-and-drain canary from
  the already-prepared exact revision.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
