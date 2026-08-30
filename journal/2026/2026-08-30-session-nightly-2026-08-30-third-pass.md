---
date: 2026-08-30
kind: session          # session | incident | decision
title: nightly 2026-08-30 third pass
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [runbooks/nightly.md, "inventory/2026-08-30", "PR #118", "PR #119", server-proxmox-core, server-proxmox-network, vm-docker-dmz]
---

# 2026-08-30 · session · nightly 2026-08-30 third pass

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (SKY-006 / journal/README.md). Distillation happens at READ time, never here. -->

## What happened
Started on `main` at `fe214aa` (PR #119), with local `main == origin/main`. The worktree already
contained an uncommitted edit to
`journal/2026/2026-08-28-session-seed-jikan-anime-index-for-aiometadata.md`; it predates this run,
was not edited by the nightly, and is excluded from the nightly commit and PR.

Created branch `inventory/2026-08-30`. This is the third report-only pass on 2026-08-30; the two
earlier passes are already on `main` via PR #116 and PR #118. No branch or open PR with the exact
nightly branch name existed before creation.

Ran `bin/ops collect`. The Proxmox core and network collectors, Docker collector, Technitium zone
collector, and firewall mirror collector wrote inventory. The PBS collector printed
`no creds yet (/opt/skynet-ops/secrets/pbs.env) — collector idle until A2/A4`. The collector's
inline docs render completed at 2026-08-30T13:26:48+05:00.

Checked for active root grants before audit harvest: neither `~/.ssh/certs/*-cert.pub` nor files
under `/opt/skynet-ops/grants/` existed. No root SSH connection was made and no grant audit was
harvested.

Ran `scripts/envsync.sh`. All ten tracked services printed `skip ...: no project.env on host` and
the script ended `no env changes`. No encrypted env file changed.

Ran `scripts/render-docs.sh`, `scripts/render-digest.sh`, and `scripts/render-context-map.sh`
explicitly. The deterministic digest caught up to the second-pass journal entry already present on
`main`; the context map recalculated token counts and journal totals. Rewrote
`docs/generated/05-state-of-the-lab.md` for this pass after comparing collected data with `main`.

## Actions & outcomes
- Proxmox semantic comparison used sorted `{vmid,type,name,status,pool,template,node}` records for
  every QEMU VM and LXC on both nodes → no guest add/remove, rename, pool, template, node, or power
  state change versus `main`. Core CT 240 remains `stopped`; network CT 240 remains `running`;
  VMID 999 remains `running`; VMID 9090 remains `running`; VMIDs 9091 and 9000 remain `stopped`.
- Docker comparison used sorted `{Names,State,Image,Status}` records → 18 containers, all
  `running`, with no image or state change. Raw JSON changed only one size string (`6.55MB` to
  `6.56MB`) and the display order of Arcane's mount list.
- DNS comparison removed collection/use/modify/expiry timestamps before sorting → byte-identical
  semantic zone/record data. Three `lastUsedOn` timestamps and the collection time advanced.
- Firewall inventory → mirror HEAD remains `aba7911` (2026-08-26 15:10:13 +0500), with 41
  aliases, 29 rules, and 6 reservations; only the collection timestamp changed.
- `scripts/envsync.sh` → no `project.env` found for any tracked Arcane project; no `.env.sops`
  changes staged.
- Root-grant audit → skipped because no grant was active.
- Generated factual pages → refreshed timestamps/live values. `06-agent-digest.md` now includes
  the already-merged second-pass episode and its current open-thread bullets.

## Graveyard — tried & abandoned
- `bin/new journal session "nightly 2026-08-30"` was not attempted because the exact append-only
  entry already exists, and `nightly 2026-08-30 second pass` also exists. Used the distinct title
  `nightly 2026-08-30 third pass` rather than collide with or rewrite either episode.
- No collection, render, envsync, or comparison command failed; no diagnostic path was abandoned.

## Follow-ups / open threads
- Core-node PBS CT 240 (`ops-managed`) is still stopped; network-node PBS CT 240 is running. The
  stopped core instance still needs a human decision. No guest-power action was taken.
- Legacy VMID 999 remains running and unexplained. No guest-power action was taken.
- The pre-existing uncommitted 2026-08-28 Jikan journal correction remains local and excluded from
  this nightly commit/PR.
- SKY-008 Phase 3 remains open according to the generated digest.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
