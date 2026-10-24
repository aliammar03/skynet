# backup

- **Purpose:** every night at 04:30, `/opt/appdata` goes to Google Drive as an encrypted restic
  snapshot, taken cold: doco-cd holds the stateful services stopped while it runs (`compose.yaml`,
  `x-stateful`: every stack whose README classes data as `data`). Sundays at 10:00 `check` prunes,
  then reads 5% of the data back, with nothing stopped. `restore` runs only from `skynet-restore`.
- **URL / auth:** none (not routed).
- **Repository:** `rclone:gdrive:skynet/restic/docker-dmz`, 64 MiB packs. Keeps 7 daily, 4 weekly
  and 12 monthly snapshots; snapshot host `docker-dmz`.
- **Backed up:** all of `/opt/appdata` except `excludes.txt`: the paths the stacks' READMEs class as
  cache, the door's certificates, and this stack's own folder.
- **Data:** `/opt/appdata/backup/` (backup class: cache): restic's cache (`cache/`) and, for a
  moment, `restore.request`.
- **Secrets:** `secret.sops.env`: `RESTIC_PASSWORD` (agent-generated; survival kit) and
  `HC_PING_URL` (healthchecks.io check `backup docker-dmz`: daily, grace 3 h). `rclone.sops.conf`:
  Ali's rclone config with remote `gdrive` (`skynetv2.md` → P4 → Drive access).
- **Restore:** as root on the host (`modules/docker-host.nix`):
  - `skynet-restore <stack> [snapshot]` puts `/opt/appdata/<stack>` back exactly as in the
    snapshot (default `latest`). It writes `restore.request` and starts this stack's `restore` job,
    so doco-cd stops the stateful services, restic restores, and doco-cd starts them again. The
    stack's cache folders stay as they are;
  - `skynet-restore --all [snapshot]`: every stack in the snapshot, for a rebuilt host;
  - `skynet-restore --list [stack]`: the snapshots, and how many entries each one changed in
    `<stack>`;
  - `skynet-restore <stack> [snapshot] --to <dir>`: into `<dir>`, with nothing stopped (a drill, or
    one file).
- **Alerts:** healthchecks.io (start, success and failure pings, and a missed night) and doco-cd's
  `notify_on: failure` on each job, both to `#alerts`. Gatus row `docker-dmz backup` from the
  check's badge.
- **Upstream:** [restic](https://restic.readthedocs.io/) ·
  [resticprofile](https://creativeprojects.github.io/resticprofile/) ·
  [doco-cd job scheduling](https://doco.cd/latest/Advanced/Job-Scheduling/)
- **Gotchas:**
  - A new stack: a service writing `data` joins `x-stateful`, and a `cache` path joins
    `excludes.txt` (`runbooks/new-stack.md`).
  - `restore`'s schedule is `@every 87600h`: doco-cd needs one and refuses a date that never comes
    (`0 0 30 2 *` fails the deploy). Ten years from doco-cd's last start never arrives either, and
    the job refuses to run without a `restore.request` from the last 10 minutes.
  - A restore targets only `/opt/appdata/<stack>` (restic's `<snapshot>:<folder>` form), so
    `--delete` can't reach anything else.
  - `run.sh` is the same in both Docker hosts' backup stacks.
  - The first night uploads everything (about 6 GB), so the apps stay stopped longer that once.
