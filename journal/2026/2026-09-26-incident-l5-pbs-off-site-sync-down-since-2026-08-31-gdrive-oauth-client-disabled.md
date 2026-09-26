---
date: 2026-09-26
time: 18:48:56            # local HH:MM:SS; orders same-day episodes in the digest
kind: incident          # session | incident | decision
title: L5 PBS off-site sync down since 2026-08-31 (gdrive OAuth client disabled)
tier_touched: [T1, T2+]  # tiers this episode ACTUALLY used (not what it could touch)
grants: ["lxc-proxmox-backup-server grant+lxc-proxmox-backup-server+2026-09-26T13:47:07+00:00+by-ali"]  # root grants used this episode: "host KeyID", else empty
refs: [SKY-025, PR #266, PR #267, CT 240, docker-dmz]  # SKY-###, PR #NNN, ADR NNNN, hosts — anything to cross-link
thread_status: open     # none | open | resolved | unknown; digest shows only explicit open
# resolves: [<episode-basename>, …]   # optional: close earlier episodes' open threads (append-only-safe)
---

# 2026-09-26 · incident · L5 PBS off-site sync down since 2026-08-31 (gdrive OAuth client disabled)

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (journal/README.md). Distillation happens at READ time, never here. -->

## What happened
SKY-025 P12 census of the PBS host (CT 240, 10.10.20.40), run as root under a 30 min grant issued
by Ali at 18:47 PKT. `gr` first failed on the workstation: its copied ~/bin/grant-root still targeted
ali@10.10.90.90. Fixed by PR #267 (grant-root is now a flake app). Ali verified the host key
SHA256:QFLLU9m9…jaU with `pct exec 240` before I used it.

Read-only commands only: systemctl show/list-timers, journalctl -u skynet-pbs-gdrive, sha256sum,
findmnt, proxmox-backup-manager version/datastore list/task list, grep of sshd_config.d. Nothing on
PBS was changed.

## Actions & outcomes
- journalctl -u skynet-pbs-gdrive → the last success was 2026-08-22T04:12 ("0 differences found").
  The first failure was 2026-08-31T04:13, and every run since fails the same way:
  `couldn't fetch token … oauth2: "disabled_client" "The OAuth client was disabled."` for
  gdrive:Skynet/Backups/pbs. The latest was 2026-09-26T17:31 (Persistent timer catch-up after boot).
- /opt/skynet-ops/secrets/rclone.conf on PBS has a `client_id` line (a custom Google OAuth client)
  and `type = drive`. Google disabled that client.
- journalctl --list-boots → the previous boot ended 2026-09-16 13:49, and the current one started
  2026-09-26 17:17. PBS was down for about 10 days. Task list: nothing between the 2026-09-16 05:15
  prunejob and the 2026-09-26 17:18 GC/verify/prune catch-up.
- Installed backup-pbs-gdrive.sh differs from git only in a header comment. The service and timer
  hashes equal scripts/systemd/.
- sshd: TrustedUserCAKeys /etc/ssh/skynet_ops_ca.pub and AuthorizedPrincipalsFile
  /etc/ssh/auth_principals/%u. The grant session was logged with KeyID grant+lxc-proxmox-backup-server+….
- Probably related, not confirmed: skynet-restic-backup@docker-dmz failed today at 02:37 after 7 s,
  also against gdrive. Same rclone remote family. I have no journal access there without a grant.

## Graveyard — tried & abandoned
- — nothing abandoned —

## Follow-ups / open threads
- Ali: create a new Google OAuth client (or drop client_id to use rclone's default), then run
  `rclone config reconnect gdrive:` on a browser machine. Update rclone.conf on PBS and docker-dmz,
  plus secrets/rclone.conf.sops and the survival kit. Then run L5 by hand and confirm
  `rclone check` reports 0 differences.
- The survival kit's rclone.conf probably carries the same disabled client, so off-site restore from
  the kit alone is likely broken right now.
- Why was CT 240 down from 09-16 to 09-26? Check the known boot-order issue (CT 240 starts before
  the Unraid NFS) and whether PVE vzdump jobs failed in that window.
- Nothing alerted on any of this for four weeks: the SKY-025 Phase 14 case.
