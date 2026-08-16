---
id: SKY-001
title: Ongoing backup strategy for CT 240 (PBS host)
status: draft
horizon: short
created: 2026-08-16
updated: 2026-08-16
phases: 1
current_phase: 0
tier_touched: [T2, T2+]   # T2 vzdump (operate token) + a T2+ grant to set up restic on the host
related: [docs/deployment-plan.md, runbooks/backup.md, "[[skynet-backups]]"]
---

# SKY-001 · Ongoing backup strategy for CT 240 (PBS host)

> Give the PBS-hosting container a real, recurring, off-site backup — it currently has none,
> and it's the one guest that can't be snapshotted.

## 1. Problem / motivation
Surfaced by the A6 update-guests drill (2026-08-16). CT 240 (`lxc-proxmox-backup-server`) is special:
- **Can't be snapshotted** — its `mp0` bind-mounts the NFS datastore (`/mnt/datastore/unraid`), and
  LXC snapshots require *every* mountpoint on snapshot-capable storage.
- **Isn't in any backup job** — it's the PBS host, so it can't sensibly back up *into its own*
  datastore. `ns/core/ct/240` is empty. Before A6 it had **zero** restore point of any kind.
- We patched it under a one-off `vzdump` to `local` (`vzdump-lxc-240-2026_08_16-*.tar.zst`, 364 MiB),
  but that's manual + on-node (dies with the node) — not a strategy.

Its valuable state is small: rootfs 1.3 GiB used — PBS config (`/etc/proxmox-backup`), the gdrive
sync unit + `pbs-gdrive.env`, `/opt/skynet-ops`, `/root`. The datastore itself (mp0) is separately
protected (NFS + gdrive L5) and must stay excluded.

## 2. Brainstorm — options considered
- **Option A — scheduled `vzdump` to `local`, then sync that dir to gdrive.** Gives a clean full-CT
  restore (`pct restore`, like CT 101 got). But `local` is on the core node (not off-site until
  synced), and scheduling a vzdump job is a node/T3 action. `vzdump` itself is now T2 (operate token).
- **Option B — restic file-level of the config paths → `gdrive:Skynet/Backups/restic/pbs-host`.**
  Same pattern as docker-dmz L3 (`provision-restic.sh`), off-site, incremental/dedup, nightly timer,
  **agent-run under a grant, no downtime**. Directly feeds the DR-core-node "restore PBS config" step.
  Downside: file-level, not a bootable image — restore = rebuild CT / fresh PBS + `restic restore`.
- **Decision (proposed, confirm in-session):** **Option B as the primary off-site strategy** (Skynet-
  native, off-site, no T3, no downtime), optionally + a periodic `vzdump` (now T2) for a full-image
  restore. B is what the DR runbook actually needs.

## 3. The plan
- **Scope / non-goals:** back up CT 240's *config/rootfs paths*, off-site, on a timer. NOT the
  datastore (mp0 — already protected, must stay excluded).
- **Hosts & tiers touched:** CT 240 (`lxc-proxmox-backup-server`). T2+ grant to run
  `provision-restic.sh` on the host; T2 for any vzdump. No blast-radius change → likely no
  `deployment-plan.md` PR, but record the new repo in `docs/backup-strategy.md`.
- **Rollback posture:** disable the timer / `git revert`; nothing destructive.
- **Grants / human actions:** one `gr lxc-proxmox-backup-server`. The initial restic seed *initiates
  an external upload* → the safety classifier may block it → Ali runs the one seed command; the
  nightly timer carries it after.

### Phase 1 — restic-to-gdrive for CT 240 config  (~1–2h)   `[ ]` not started
Steps:
1. `scripts/provision-restic.sh pbs-host root@10.10.20.40 --path /etc/proxmox-backup --path /etc
   --path /opt --path /root` (confirm path list; exclude nothing datastore-y — mp0 lives under
   `/mnt`, not listed).
2. Verify the repo + first snapshot (`restic snapshots`); confirm the nightly timer is enabled.
3. Prove a restore: restore `/etc/proxmox-backup` to a scratch dir, diff against live.
4. Record the new repo in `docs/backup-strategy.md` + `runbooks/backup.md`.
5. (Optional) also silence the PBS `enterprise.proxmox.com` 401 by switching to the
   `pbs-no-subscription` apt repo.

Exit criteria: CT 240 config has an off-site restic repo on gdrive with a verified restore, nightly
timer live, docs updated.
Grants / human actions: one `gr lxc-proxmox-backup-server`; Ali runs the seed upload if the classifier blocks it.

## 4. ▶ Execute prompt
> Paste into a fresh Skynet session to run this directive. Swap `<N>` for the phase to run.
```
Read planning/projects/SKY-001-ongoing-backup-strategy-for-ct-240-pbs-host.md and execute Phase <N>.
Follow AGENTS.md: plan loudly then run quietly, never merge your own PRs, request the
narrowest host / shortest grant the phase needs, and checkpoint at the listed human/grant
steps. When the phase's exit criteria are met, do the "Phase close-out" at the bottom.
```

## 5. Phase close-out (resume material)
Run this every time a phase finishes successfully — it's what makes the next session cold-startable:
- [ ] Land the work via **PR** (agent never merges its own).
- [ ] Write/refresh a memory `SKY-001-progress` (what shipped, what's next, gotchas) + a MEMORY.md pointer.
- [ ] Bump this file's frontmatter (`current_phase`, `status`, `updated`) and flip the phase box to `[x]`.
- [ ] `bin/plan list` to refresh the roadmap index.
- [ ] Paste the **Continue prompt** below to resume in a fresh session:
```
Continue planning/projects/SKY-001-ongoing-backup-strategy-for-ct-240-pbs-host.md at Phase <N+1>.
Prereqs carried from the last phase: <…>. Resume context from memory [[SKY-001-progress]].
Follow AGENTS.md as above.
```

## 6. Status log
- 2026-08-16 — created (draft) from the A6 update-guests drill finding: CT 240 has no ongoing backup
  and can't be snapshotted. Proposed restic-to-gdrive (Option B). See [[skynet-backups]], [[skynet-a6-next]].
