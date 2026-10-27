# backup

- **Purpose:** every night at 04:30, `/opt/appdata` goes to Google Drive as an encrypted restic
  snapshot, copied hot from btrbk's newest snapshot of it (04:20, `modules/docker-host.nix`): every
  app's files at one instant, with nothing stopped. Sundays at 10:00 `check` prunes, then reads 5%
  of the data back.
- **URL / auth:** none (not routed).
- **Repository:** `rclone:gdrive:skynet/restic/docker-dmz`, 64 MiB packs. Keeps 7 daily, 4 weekly
  and 12 monthly snapshots; snapshot host `docker-dmz`.
- **Backed up:** all of `/opt/appdata` except `excludes.txt`: the paths the stacks' READMEs class as
  cache, and the door's certificates.
- **Source:** `/mnt/appdata-pool/@snapshots/latest`, mounted read-only at `/opt/appdata` in the job,
  so restic's paths are the live ones. `run.sh` refuses a source with no app data (the stamp and
  the marker don't count), one without `.data-ready` (a restore under way or failed), or a snapshot
  more than an hour old (its `.snapshot-stamp`).
- **Data:** none of its own. restic's cache is the host's `/var/cache/restic-appdata` (ext4,
  outside the snapshots).
- **Secrets:** `secret.sops.env`: `RESTIC_PASSWORD` (agent-generated; survival kit) and
  `HC_PING_URL` (healthchecks.io check `backup docker-dmz`: daily, grace 3 h). `rclone.sops.conf`:
  Ali's rclone config with remote `gdrive` (`skynetv2.md` → P4 → Drive access). The host reads
  both too, through sops-nix, for `skynet-restore`.
- **Restore:** as root on the host, `skynet-restore` (`modules/docker-host.nix`):
  - `skynet-restore list [<stack>]`: the local snapshots and the Drive snapshots;
  - `skynet-restore local <stack> <snapshot>`: from a local snapshot, in seconds;
  - `skynet-restore drive <stack> [<snapshot>]`: from Drive (default `latest`);
  - `--to <dir>`: into a folder, with nothing stopped (a drill, or one file); `--all` in place of a
    stack: every stack (a rebuilt host).

  In place, it takes an undo snapshot, holds doco-cd (it takes `/opt/appdata/.data-ready` away),
  stops the stack, puts `/opt/appdata/<stack>` back exactly as in the snapshot (its cache folders
  stay as they are), then puts the marker back and starts the stack and doco-cd again. Failing
  halfway, it leaves the stack stopped and doco-cd held until the same restore, its undo or
  `--all` succeeds (`skynetv2.md` → P4 → Restores).
- **Alerts:** healthchecks.io (start, success and failure pings, and a missed night) and doco-cd's
  `notify_on: failure` on each job, both to `#alerts`. Gatus row `docker-dmz backup` from the
  check's badge. A failed snapshot shows as a failed backup (the snapshot's age).
- **Metrics:** each backup writes resticprofile's `resticprofile_backup_*` (status, time,
  duration, bytes added) to the host's `/var/lib/node-exporter/restic-appdata.prom`; btrbk's hook
  writes the newest snapshot's time (`appdata-snapshot.prom`). VictoriaMetrics scrapes both through
  node-exporter (`stacks/admin/metrics`).
- **Upstream:** [restic](https://restic.readthedocs.io/) ·
  [resticprofile](https://creativeprojects.github.io/resticprofile/) ·
  [btrbk](https://digint.ch/btrbk/) ·
  [doco-cd job scheduling](https://doco.cd/latest/Advanced/Job-Scheduling/)
- **Gotchas:**
  - A new stack: a `cache` path joins `excludes.txt` (`runbooks/new-stack.md`); nothing else.
  - `create_host_path: false` on the source: with no snapshot yet, the job fails rather than back up
    an empty folder. A fresh host takes its first snapshot before doco-cd's release
    (`runbooks/new-vm.md`, step 6, or `skynet-restore … --all`).
  - `run.sh` is the same in both Docker hosts' backup stacks.
