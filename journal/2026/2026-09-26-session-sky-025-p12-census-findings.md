---
date: 2026-09-26
time: 18:33:24            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: SKY-025 P12 census findings
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-025, docker-dmz, CT 240]  # SKY-###, PR #NNN, ADR NNNN, hosts — anything to cross-link
thread_status: open     # none | open | resolved | unknown; digest shows only explicit open
# resolves: [<episode-basename>, …]   # optional: close earlier episodes' open threads (append-only-safe)
---

# 2026-09-26 · session · SKY-025 P12 census findings

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (journal/README.md). Distillation happens at READ time, never here. -->

## What happened
Phase 12 of SKY-025: ported check-invariants.sh + secret-scan.sh to `skynet check`
(src/skynet/gates.py), then a read-only census from vm-skynet-ops. All reads were Arcane API GETs
with the arcane.env key, svc-ops SSH to docker-dmz 10.10.100.15 (docker ps/inspect, systemctl
status, stat through a read-only busybox bind of /opt/docker/arcane-projects), and a local
`tofu state list` with only the state passphrase loaded.

## Actions & outcomes
- First `test -e` of /opt/docker/arcane-projects/*/.env as svc-ops → every file reported absent.
  False: the dirs are 1000:1000 0700, so svc-ops cannot traverse them. Re-read through the docker
  group; all ten .env files exist.
- stat via docker → aiostreams, calibre, karakeep, marinara .env are 0644, the other six 0600.
- docker inspect → librespeed-librespeed-1 has working_dir
  /home/svc-ops/.local/state/skynet-deploy/librespeed/generations/f8072b390c10957a572eda4aa112da0583e46796.
  `git log -S skynet-deploy` → b1b49b1 "feat(deploy): activate immutable compose generations"
  (2026-09-15), only on remotes/origin/phase/sky-025-p11-deploy, never merged. Arcane sync for
  librespeed has autoSync:false. The live state was activated from that branch.
- systemctl on docker-dmz → skynet-restic-backup@docker-dmz.service failed, 2026-09-26 02:37:12 PKT,
  status=1 after about 7 s. `journalctl -u` as svc-ops → "No entries" (needs adm/systemd-journal).
- sha256 of /opt/skynet-ops/scripts/backup-restic.sh on docker-dmz = 84a22d06…; the repo copy =
  d1a937c8…. The installed file dates from 2026-08-16.
- ssh svc-ops@10.10.20.40 (PBS CT 240) → "Host key verification failed". There is no pinned key, and
  none was added.
- tofu state list → 30 addresses. State still holds pool_ct["athena"], while code has a moved block
  to core_ct["athena"]. No resource on proxmox.network.
- Old regex parity: compose/aiometadata/jikan/mongo-init.js and scripts/backup-{restic,pbs-gdrive}.sh
  match the secret-assignment regex (a `Password` assigned from process.env, and a `secret` shell
  variable assigned a /opt/skynet-ops path).
  They trip only when staged, under both the shell and the Python versions.
- Ali chose Pushover as the Phase 14 alert channel.

## Graveyard — tried & abandoned
- Judging .env presence with `test -e` as svc-ops → abandoned. Permission denial reads as absence.
- Reading the PBS units over SSH → abandoned. No trusted host key and no standing path.

## Follow-ups / open threads
- Why did the docker-dmz restic backup fail? Last known success is unknown. Needs a root grant for
  docker-dmz to read the journal.
- Reconcile the installed backup-restic.sh with git.
- Four 0644 materialized .env files; Phase 13 rewrites env materialization.
- The librespeed generation deploy is not on main; Phase 13 adopts or retires it.
- Survival-kit proof and PBS L5 census are Phase 16 preconditions.
