# backup

- **Purpose:** every night at 04:30, `/opt/appdata` goes to Google Drive as an encrypted restic
  snapshot, copied hot, with nothing stopped. The one database here is Authelia's small SQLite
  file, read in milliseconds while nobody logs in. Sundays at 10:00 `check` prunes, then reads 5% of
  the data back.
- **URL / auth:** none (not routed).
- **Repository:** `rclone:gdrive:skynet/restic/docker-admin`, 64 MiB packs. Keeps 7 daily, 4 weekly
  and 12 monthly snapshots; snapshot host `docker-admin`.
- **Backed up:** all of `/opt/appdata` except `excludes.txt`: the paths the stacks' READMEs class as
  cache or disposable (Gatus's history, the metrics and logs stores), and the door's certificates.
- **Source:** `/opt/appdata`, read-only. `run.sh` refuses it with no app data (the marker doesn't
  count), or without `.data-ready` (a restore under way or failed). This host keeps ext4: no
  snapshots, so no local restores (docker-dmz has both).
- **Data:** none of its own. restic's cache is the host's `/var/cache/restic-appdata`.
  `/opt/appdata/backup/` holds its old cache, excluded; it can go.
- **Secrets:** `secret.sops.env`: `RESTIC_PASSWORD` (agent-generated; survival kit) and
  `HC_PING_URL` (healthchecks.io check `backup docker-admin`: daily, grace 3 h). `rclone.sops.conf`:
  Ali's rclone config with remote `gdrive` (`skynetv2.md` → P4 → Drive access). The host reads
  both too, through sops-nix, for `skynet-restore`.
- **Restore:** as root on the host, `skynet-restore` (`modules/docker-host.nix`):
  - `skynet-restore list [<stack>]`: the Drive snapshots;
  - `skynet-restore drive <stack> [<snapshot>]`: from Drive (default `latest`);
  - `--to <dir>`: into a folder, with nothing stopped (a drill, or one file); `--all` in place of a
    stack: every stack (a rebuilt host).

  In place, it holds doco-cd (it takes `/opt/appdata/.data-ready` away), stops the stack, puts
  `/opt/appdata/<stack>` back exactly as in the snapshot (its cache folders stay as they are), then
  puts the marker back and starts the stack and doco-cd again. Failing halfway, it leaves the stack
  stopped and doco-cd held until the same restore or `--all` succeeds (`skynetv2.md` → P4 →
  Restores).
- **Alerts:** healthchecks.io (start, success and failure pings, and a missed night) and doco-cd's
  `notify_on: failure` on each job, both to `#alerts`. Gatus row `docker-admin backup` from the
  check's badge.
- **Metrics:** each backup writes resticprofile's `resticprofile_backup_*` (status, time,
  duration, bytes added) to the host's `/var/lib/node-exporter/restic-appdata.prom`, which
  VictoriaMetrics scrapes through node-exporter (`stacks/admin/metrics`).
- **Upstream:** [restic](https://restic.readthedocs.io/) ·
  [resticprofile](https://creativeprojects.github.io/resticprofile/) ·
  [doco-cd job scheduling](https://doco.cd/latest/Advanced/Job-Scheduling/)
- **Gotchas:**
  - A new stack: a `cache` path joins `excludes.txt` (`runbooks/new-stack.md`); nothing else.
  - `run.sh` is the same in both Docker hosts' backup stacks.
