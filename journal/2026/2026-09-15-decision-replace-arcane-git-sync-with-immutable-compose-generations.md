---
date: 2026-09-15
time: 10:29:41
kind: decision
title: replace Arcane Git Sync with immutable Compose generations
tier_touched: [T1]
grants: []
refs: [SKY-025, PR #259, ADR 0007, docker-dmz]
thread_status: open
---

# 2026-09-15 · decision · replace Arcane Git Sync with immutable Compose generations

## What happened

Ali directed the existing P11 construction session to rework PR #259 in place. The old head
`7fca6d307f5684316eb9fd42e8f0572c5810fdd2` and current `main`
`f8072b390c10957a572eda4aa112da0583e46796` were resolved from GitHub and fetched.
The old PR body described branch repointing, manual Arcane source-sync POST, `lastSyncAt` retry,
and Git-revert rollback preparation. Ali explicitly replaced that deployment authority with exact
Git revision, immutable generation, direct Compose activation, independent verification, and stable
promotion. The old external ACCEPT is bound to the old design/head and will not be used for closeout.

A read-only `ssh svc-ops@10.10.100.15` probe returned UID 1002, Docker group membership, installed
Docker Compose v5.4.0, and Debian 13 ext4 persistence. `/home/svc-ops` is owned by `svc-ops` and mode
`0700`. A live `librespeed` container's Compose labels included `project=librespeed`, config file
`/opt/docker/arcane-projects/librespeed/compose.yaml`, and matching working directory. Those labels
still need a disposable OLD/NEW activation proof before they become authoritative.

## Actions & outcomes

- Fetched current main and existing P11 head; preserved unrelated generated inventory worktree files.
- Updated the active P11 packet and disposition map to keep accepted numbered progress at P10.
- Selected `/home/svc-ops/.local/state/skynet-deploy` as the protected persistent state root.
- Assigned bounded generation, activation, and P10-verification adaptation implementation packages.

## Graveyard — tried & abandoned

- Arcane branch repoint/manual source-sync as P11 authority: abandoned by Ali's architectural
  direction because source/environment coherence and ambiguous operation recovery need stronger
  boundaries than Arcane's available sync metadata.

## Follow-ups / open threads

- Prove Docker label identity and coherent generation activation in disposable fixtures.
- Finish implementation and independent focused verification; publish the same PR #259 for a
  completely fresh external review. Do not enter accepted closeout on the old ACCEPT.
