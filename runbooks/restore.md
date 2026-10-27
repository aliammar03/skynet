# Restores

Git rebuilds the system (`skynetv2.md` → Rules, 2). Backups bring back what git doesn't hold: the
apps' data, and the guests git doesn't describe (OPNsense, HAOS, Omada, athena). A NixOS guest
restored whole is a shortcut: comin then brings it to `main`. Six cases, smallest first. **Agent** steps run on ops as
`skynet`; **Ali** steps are his.

## The copies

| Copy | Of | Taken | Kept | Readable with |
|---|---|---|---|---|
| btrbk snapshots, docker-dmz `/mnt/appdata-pool/@snapshots/` | its `/opt/appdata` | 04:20 | each 2 days, then one a day for 7 | — |
| restic, `gdrive:skynet/restic/<host>` | each Docker host's `/opt/appdata`, caches left out (`excludes.txt`) | 04:30 | 7 daily, 4 weekly, 12 monthly | its restic password |
| PBS, datastore `skynet` on Unraid's share `pbs` | every guest but Unraid (2020) and PBS (2040) | network node 02:00, core 03:30 | 14 daily, 8 weekly, 12 monthly | the node's PVE encryption key |
| `gdrive:skynet/pbs` | that datastore, mirrored | 06:00 | as the datastore; what it drops stays 30 days in Drive's trash | the same keys |

The passwords and keys are in the survival kit (`skynetv2.md` → P4 → Survival kit).

## Before any restore

- **Smallest first:** one app's folder before a whole host, a local snapshot before Drive.
- **Alerts:** the agent silences what its own planned restore will trip (a host or target down), for
  at most 4 hours, the comment naming the restore.
- **Cap a guest restore:** `--bwlimit 51200` (KiB/s: 50 MiB/s). Uncapped, it takes the node's disk,
  and every guest on that node slows, OPNsense too on the network node.
- **Over the original, or beside it:** a restore over an existing guest replaces its disks. That
  destroys it: Ali's call. Beside it means a free VMID.

## 1. An app, from a local snapshot (docker-dmz)

**Agent** (root there, D11):
```sh
ssh skynet@10.10.100.10 sudo skynet-restore list <stack>
ssh skynet@10.10.100.10 sudo skynet-restore local <stack> <snapshot>
```
- `list` shows the local snapshots (`@appdata.<YYYYMMDDThhmm>`; `latest` is the newest) and Drive's.
- Name the snapshot, with or without `@appdata.`. Never "the newest": after a restore, that's the undo
  snapshot taken just before it.
- In seconds, it:
  1. takes the undo snapshot;
  2. holds doco-cd: it takes `/opt/appdata/.data-ready` away, so nothing starts doco-cd again, then
     stops it;
  3. stops the stack's containers;
  4. makes `/opt/appdata/<stack>` equal to the snapshot (`rsync --delete --checksum`), leaving the
     stack's cache folders (`excludes.txt`) as they are;
  5. puts the marker back, starts the containers, then doco-cd.

  It ends by printing the undo: `skynet-restore local <stack> <undo snapshot>`.
- One file: `--to <dir>` copies the stack's folder there, with nothing stopped; take the file from it.
- Check: the app's Gatus row, and `journalctl CONTAINER_NAME=<container> -n 50 -o cat`.
- A stack whose search index is a cache (karakeep's meilisearch) may need a reindex in the app.

## 2. An app, from Drive

`skynet-restore drive <stack> [<snapshot>]`: case 1's steps, from restic (`latest` by default).
- **Who:** on docker-dmz the agent; on docker-admin **Ali**
  (`ssh -t aliammar@10.10.50.40 sudo skynet-restore …`), where the agent has no sudo. docker-admin
  has no snapshots, so no undo.
- `list <stack>` shows Drive's snapshots, and how many entries each one changed in the stack. Pick
  the one before the change.
- Minutes: librespeed took 26 s in place; karakeep's 1.79 GiB took 75 s into a folder.
- Sundays at 10:00 the `check` job prunes, and restic's lock refuses a restore meanwhile. Run it
  again after.
- docker-admin's metrics, logs, and Grafana's and Gatus's data are caches, not in the backup.

**A failed restore holds the host** (cases 1 and 2):
- One that fails before any file changed puts everything back.
- One that fails later leaves the stack stopped and doco-cd held: the folder is part one snapshot,
  part the other. `skynet-restore list` says so.
- The first of these to succeed ends the hold: the same restore again (any snapshot), its undo, or
  `--all`. A restore of another stack is refused meanwhile.
- To accept the data as it is, as root:
  `rm /var/lib/skynet/restore-held && touch /opt/appdata/.data-ready && systemctl start docker-doco-cd`.
- While doco-cd is held its jobs wait too, so healthchecks.io pages the host's heartbeat.

## 3. A host, rebuilt from git

`runbooks/new-vm.md` → Rebuild. The rest comes back from:

| Host | Not in git | From |
|---|---|---|
| docker-dmz, docker-admin | `/opt/appdata` | `skynet-restore drive --all [<snapshot>]` while doco-cd is held (Rebuild, step 4), or the copy on ops if the old host still ran. Ali runs it on docker-admin |
| ops | `~skynet/.claude` (logins, the Discord plugin, memory) and the agent's SSH key | only its guest backup: restore the guest (case 4). Rebuilt, it logs in again and has new keys: `hosts/ops/agent.pub` and `cache.pub` change in the PR (`hosts/ops/README.md`), and Ali puts the new agent key on PBS (`answer.toml` and root's `authorized_keys`) |
| technitium-network, technitium-core | nothing | — |
| PBS | nothing on its disk | case 5 |

- `--all` restores every stack from one snapshot, takes the first local snapshot (docker-dmz), then
  writes the marker and starts doco-cd, which deploys the stacks onto their data. A failed `--all`
  writes no marker, so nothing starts on half the data.
- docker-admin's metrics and logs start empty.
- **Rebuild, or restore the guest?** Rebuild when the VM itself changes (its disk layout, its NICs) or
  can't be trusted. Restoring the guest (case 4) brings it back faster, as it was the night before.

## 4. A guest, from PBS

**Ali**, on the guest's node. Each node's storage `pbs` sees only its own namespace:
```sh
pvesm list pbs --vmid <vmid>     # its backups: pbs:backup/vm/<vmid>/<time>
qm stop <vmid> && qmrestore pbs:backup/vm/<vmid>/<time> <vmid> --force 1 --bwlimit 51200
pct stop <vmid> && pct restore <vmid> pbs:backup/ct/<vmid>/<time> --force 1 --bwlimit 51200   # a container
```
Beside the original (a drill, or files out of it): a free VMID and `--unique 1` (new MACs), then
`qm set <new vmid> --delete net0 --onboot 0` before it starts, so it can't take the original's
address.

After a VM comes back from an older backup:
- **Its PVE config is the backup's.** Re-apply what `hosts/<h>/proxmox.sh` (or `pbs/proxmox.sh`)
  sets differently now, e.g. docker-admin's `qm set 5040 --balloon 3072`.
- **A NixOS guest boots the backup's generation.** comin then builds `main` and switches to it
  (docker-admin: 7 minutes at a load of 10 on its 2 vCPUs). Judge the host after the switch.
- **A Docker host whose backup predates the marker** (before 2026-10-27) waits with doco-cd held. As
  root: `touch /opt/appdata/.data-ready && systemctl start docker-doco-cd`.
- **Job metrics** (`/var/lib/node-exporter/*.prom`) stay the backup's until each job runs again.
  docker-admin's metrics and logs lose everything after the backup.

## 5. PBS, rebuilt from `pbs/etc/`

`pbs/README.md` → Rebuild. A fresh VM 2040 from `answer.toml`, then `setup.sh` (agent) brings back
`etc/` and mounts the datastore on Unraid as it is, so every backup is still there. Then:
- **Ali** regenerates the three tokens' secrets: `pve@pbs!core` and `pve@pbs!network` into each node's
  storage `pbs`, with the new fingerprint, and `metrics@pbs!exporter` into
  `stacks/admin/metrics/secret.sops.env`;
- **Agent**, in the same PR: `ssh_host.pub` and its pin, caddy-admin's `certs/pbs.pem`, pbs-exporter's
  `skynet.pinned-cert` label.
- **Check:** each node's `pvesm list pbs` lists its guests' backups; the next 07:00 drift check is
  quiet; that night's backups, verify and offsite copy succeed.
- Only PBS's task history is lost. The encryption keys are PVE's, so nothing else changes.

## 6. From Drive, with nothing else left

**Needs:**
- the repo (public, `github.com/aliammar03/skynet`);
- the survival kit: the age master key, each node's PVE encryption key, the restic passwords, the
  OAuth client's ID and secret, PBS's root password;
- a workstation with Nix.

**Order.** NixOS installers take only the agent's key, which lives on ops, so ops comes back from its
guest backup before any host is rebuilt.
1. **Ali:** a Proxmox node and a network. Neither is in this repo: a node is installed by hand, and
   OPNsense's config is in `skynet-opnsense`.
2. **Ali:** rclone. The repo's `rclone.sops.conf` files hold a working token unless it was revoked;
   otherwise make a new one from the kit's client (`skynetv2.md` → P4 → Drive access, steps 5–6).
   Any token of that client sees what the client created (`drive.file`).
3. **Ali:** PBS (case 5), its ISO built on the workstation
   (`nix build github:aliammar03/skynet#installer-pbs`). It accepts his key as well as the agent's.
   Its datastore needs a new, empty Unraid share `pbs` with room for `rclone size gdrive:skynet/pbs`
   (`pbs/README.md` → Install, step 2): `setup.sh` makes a new datastore there. Anything else
   needs `etc/`'s mount units changed first (a PR).
4. **The datastore back,** as root on PBS, into the new one: `apt-get install -y rclone`, `rclone
   config` (remote `gdrive`), then
   `rclone copy gdrive:skynet/pbs /mnt/datastore/skynet --transfers 8 && chown -R backup:backup /mnt/datastore/skynet`,
   then `proxmox-backup-manager verify skynet`. Hours: Drive serves about 10 requests a second, one
   per file. Copying into a datastore PBS made matters: Drive's copy lacks the empty chunk folders
   (rclone skips them), which PBS's own has.
5. **Ali**, on each node: storage `pbs` with its token and the kit's key (a file; it asks for the
   token's secret):
   `pvesm add pbs pbs --server <PBS> --datastore skynet --namespace <core|network> --username 'pve@pbs!<node>' --fingerprint <PBS's> --encryption-key <key file>`.
6. **Guests:** ops first (case 4, Ali), which brings the agent back. Then the rest, restored (case
   4) or rebuilt (case 3), the DNS VMs before the Docker hosts. A rebuilt Docker host's data comes
   from restic (`skynet-restore drive --all`).

**One guest, without copying it all** (a drill, or the first guest): mount Drive's copy read-only and
give a scratch datastore its chunks, so only the chunks the restore reads are fetched.
- **Agent**, as root on PBS:
  1. `apt-get install -y rclone fuse3`; Ali's `rclone config` (remote `gdrive`);
  2. mount `gdrive:skynet/pbs` read-only where `backup` can read it
     (`rclone mount --read-only --allow-other --vfs-cache-mode full`);
  3. `proxmox-backup-manager datastore create <scratch> /mnt/datastore/<scratch>`, then bind the
     mount's `.chunks` over its own;
  4. copy the guest's `owner` file and the snapshot's folder (in `ns/<node>/vm/<vmid>/`) into the
     same paths there, owned by `backup`;
  5. `DatastoreReader` on `/datastore/<scratch>` for `pve@pbs` and the node's token, then
     `proxmox-backup-manager verify <scratch>`.
- **Ali**, on the node:
  1. storage `<scratch>` with the node's own token and key, and the fingerprint from storage `pbs`
     (`/etc/pve/storage.cfg`):
     `pvesm add pbs <scratch> --server 10.10.50.24 --datastore <scratch> --namespace <node> --username 'pve@pbs!<node>' --password "$(cat /etc/pve/priv/storage/pbs.pw)" --fingerprint <fingerprint> --encryption-key /etc/pve/priv/storage/pbs.enc`;
  2. restore beside the original (case 4), and check it boots: `qm guest cmd <new vmid> get-host-name`;
  3. destroy it and `pvesm remove <scratch>`.
- **Agent** removes the scratch datastore and the mount. The datastore is removed on Ali's go
  (D11), which the drill's go covers.

## Last done

| Case | When, what | Result |
|---|---|---|
| 1 | 2026-10-25, librespeed in place | 8 s; the folder equal to the snapshot |
| 2 | 2026-10-25, librespeed in place; karakeep into a folder | 26 s and 75 s; each equal to its snapshot |
| 3 | 2026-10-25, docker-dmz rebuilt, its data from ops; `--all` from Drive not yet | under 3 minutes each way, no difference |
| 4 | 2026-10-27, docker-admin over itself, from its 10-25 backup | back; case 4's after-steps come from it |
| 5 | not yet; PBS's first install (2026-10-25) took the same steps | — |
| 6 | not yet: one guest, technitium-core, is P4's next drill | — |
