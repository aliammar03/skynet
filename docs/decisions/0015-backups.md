---
status: accepted
date: 2026-11-15
decision-makers: Ali
---

# Backups: restic from btrfs snapshots, PBS's datastore to Drive, and Unraid's copies out of reach

## Context and Problem Statement

App data has to come back one stack at a time, a guest as a whole, and all of it after losing the
house, with no app stopped for a backup. The agent is root on PBS and both Docker hosts hold
Drive's token, so the copies there are within its reach: one copy has to be one it can read and
can't delete.

## Considered Options

- **Backup engine:** restic; Kopia (younger); Borg (no Drive); Duplicati (a history of corrupt
  databases); tarball tools such as offen/docker-volume-backup (no dedup: a full upload every
  night).
- **Runner:** resticprofile in doco-cd `one_off` jobs; Backrest; autorestic; NixOS
  `services.restic` (would fit now that nothing stops, but the job carries the pings, retention
  and Gatus rows).
- **A consistent copy:** a btrbk snapshot; holding the apps stopped through doco-cd's
  `stop_services` (doco-cd 0.129.1 redeployed held stacks mid-job when a poll saw them stopped); a
  dump per database (code and an import step per app); snapper (built for OS rollback, keeps its
  snapshots inside the data); LVM-thin snapshots (more steps); a plain hot copy (MongoDB's files
  can't be copied live).
- **Restores:** `skynet-restore`, a program of our own; restores through doco-cd's job (the same
  mid-job redeploy); httm (it restores one file at a time).
- **PBS's copy:** `rclone sync` of the datastore; a second PBS; PBS 4's S3 datastores (Drive isn't
  S3); restic over the datastore (re-deduplicating PBS's chunks); an rclone `crypt` layer (a second
  key for nothing).
- **PBS itself:** a fresh VM from Proxmox's automated installer; PBS on NixOS (nixpkgs has only the
  client); v1's PBS cleaned in place.

## Decision Outcome

Chosen option:
- **restic**, run by resticprofile in doco-cd `one_off` jobs, copies `/opt/appdata` **hot** each
  night at 04:30, on both Docker hosts from the read-only **btrfs snapshot** that **btrbk** takes at
  04:20;
- **PBS** (VM 2040, installed by Proxmox's automated installer, its config in git) keeps both
  nodes' guest backups, and **rclone** copies its datastore to Drive at 06:00 (PVE encrypts the
  chunks first);
- **`skynet-restore`** puts a stack back from a local snapshot or from Drive, with doco-cd held;
- a **third copy** the lab can read and can't delete: Unraid's nightly dated copies of `pbs` and
  `Storage`, 14 kept (`hosts/unraid/undo.sh`), read-only at `/mnt/undo` on PBS and docker-dmz.

Because a snapshot holds every app's files at one instant, which databases restart from as after a
power cut, so there are no dumps, no stopped apps and no stop lists; and because the pieces are
battle-tested.

### Consequences

- Good, because nothing stops for a backup, and a restore is the files put back.
- Good, because the worst an agent's mistake leaves is an outage and a restore.
- Bad, because `skynet-restore` is a program of our own.
- Bad, because the third copy holds nothing newer than 04:00, and nothing of the apps' data newer
  than the night's guest backup.

## More Information

- 2026-10-24, Ali, with the backups plan (#72): restic and PBS's datastore to Drive, PBS rebuilt
  greenfield (#75), one-command restores.
- 2026-10-25 (#79): hot backups from btrfs snapshots, docker-dmz rebuilt onto btrfs (#81).
- 2026-11-12, Ali, with the autonomy plan: the third copy (#185, #190, live 2026-11-15).
- 2026-11-15: docker-admin's data on a btrfs disk of its own, backed up from btrbk's snapshot too
  (#195, #198).

How each copy is restored: `runbooks/restore.md`.
