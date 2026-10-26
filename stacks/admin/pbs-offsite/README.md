# pbs-offsite

- **Purpose:** PBS's datastore, every guest's backups, mirrored to Google Drive every night at 06:00
  (`sync`), after both nodes' backups and the prune. Wednesdays at 10:00 `check` confirms that Drive
  holds every datastore file, unchanged (`rclone check --one-way`, by hash). Both are doco-cd
  `one_off` jobs.
- **URL / auth:** none (not routed).
- **Source:** `/mnt/pbs-datastore`, docker-admin's read-only automount of Unraid's share `pbs`
  (`hosts/docker-admin`). All of it except PBS's `.lock`, `.gc-status` and the temporary files it
  renames into place (`*.tmp`, `*.tmp_*`).
- **Destination:** `gdrive:skynet/pbs`. PVE encrypts every guest's disks, config and log before PBS
  stores them. Each snapshot's manifest is only signed, so Drive sees the guests' IDs, names (their
  notes), sizes and times, and the keys' fingerprints. Files the datastore drops (prune, then GC)
  go to Drive's trash, which keeps them 30 days.
- **Data:** none on the host.
- **Secrets:** `secret.sops.env`: `HC_PING_URL` (healthchecks.io check `pbs-offsite`: daily, grace
  6 h). `rclone.sops.conf`: Ali's rclone config with remote `gdrive`, the same file as the backup
  stacks' (`skynetv2.md` → P4 → Drive access).
- **Restore (a guest from Drive):** copy the datastore back into a scratch datastore
  (`rclone copy gdrive:skynet/pbs <dir>`), verify it on PBS, then restore the guest from PVE with
  its node's key (`skynetv2.md` → P4 → PBS offsite).
- **Alerts:** healthchecks.io (start, success and failure pings, and a missed night) and doco-cd's
  `notify_on: failure` on both jobs, to `#alerts`. Gatus row `pbs-offsite` from the check's badge.
- **Metrics:** each sync ends by writing `skynet_pbs_offsite_end_timestamp_seconds` and
  `skynet_pbs_offsite_exit_code` to the host's `/var/lib/node-exporter/pbs-offsite.prom`
  (`stacks/admin/metrics`).
- **Upstream:** [rclone sync](https://rclone.org/commands/rclone_sync/) ·
  [rclone's Drive backend](https://rclone.org/drive/) ·
  [doco-cd job scheduling](https://doco.cd/latest/Advanced/Job-Scheduling/)
- **Gotchas:**
  - `run.sh` refuses to run unless the source holds `.chunks/0000`. An unmounted share is an empty
    folder, and syncing an empty folder would empty Drive's copy.
  - Unraid's export maps this host's reads to uid 34, PBS's `backup`: the datastore's folders are
    `750` and its own.
  - Drive creates about 2 files a second, so the first sync runs for hours: about 6 for the
    41,202 files (86.8 GiB) of 2026-10-25 (`skip_running` keeps the next night's from starting
    beside it). Later nights send only new chunks. A night that reaches
    `--max-transfer 700G` (Drive takes 750 GiB a day) stops cleanly, counts as a success, and the
    next night carries on.
  - The image is the backup stacks' (resticprofile's), which ships rclone and curl.
