# pbs

Proxmox Backup Server: both nodes' nightly guest backups. VMID 2040 · 10.10.20.40 · VLAN 20 ·
server-proxmox-core · 2 vCPU / 4 GB (2 GB guaranteed) / 32 GB. Proxmox's appliance (Debian), not
NixOS: it installs from Proxmox's ISO with `answer.toml`, then `setup.sh` gives it `etc/`, the
part of its `/etc` that git holds. ops compares that with the host every day.

- **Datastore `skynet`:** Unraid's share `pbs` (`10.10.20.20:/mnt/user/pbs`), mounted over NFS at
  `/mnt/datastore/skynet` on first use. Namespaces `core` and `network`, one per node. PVE encrypts
  every chunk before it leaves the node: without PVE's keys (survival kit) the datastore, and its
  copy on Drive, can't be read.
- **Jobs** (`etc/proxmox-backup/`): prune per namespace (core 05:00, network 05:15; 14 daily,
  8 weekly, 12 monthly); verify daily at 00:00, skipping verified snapshots until they're 30 days
  old; GC Sundays 12:00, after the offsite copy. The backups themselves are PVE's jobs (network node
  02:00, core 03:30); core's leaves out 2040, since PBS rebuilds from git.
- **Users:** `root@pam` (Ali in the UI; the agent over SSH) and `pve@pbs`. Its tokens `core` and
  `network` each hold `DatastoreBackup` on their own namespace, and `pve@pbs` holds it on both,
  because a token never gets more than its user. The tokens' secrets exist only in PVE's storage
  config.
- **Secrets:** `secret.sops.yaml` (Ali only): `root_password`, for the UI and the console.
- **Agent:** root over SSH from ops only (`from=` in `answer.toml`, D11). ops pins the host key
  (`ssh_host.pub`, `modules/agent.nix`).
- **`etc/`:** `proxmox-backup/`'s config files that hold no secret, the datastore's mount units,
  the apt sources (no subscription) and `resolv.conf`. `modules/pbs-drift.nix` on ops compares them
  with PBS at 07:00, and every allowlisted name too, so a file that appears on PBS (a sync job added
  in the UI) counts. A difference, or a failed check, goes to `#alerts`.
- **Updates:** `apt full-upgrade` (setup runs one). Proxmox's no-subscription repository.

## Install (a rebuild too)

1. **Agent:** `nix build .#installer-pbs --print-out-paths` on ops: Proxmox's PBS 4.2-1 ISO with
   `answer.toml` built in (`installer.nix`).
2. **Ali, Unraid** (first install only): a share `pbs` with NFS export Yes, security Private, rule
   `10.10.20.40(sec=sys,rw,no_root_squash)`. PBS creates the datastore as root, then hands it to
   user `backup`; with root squashed that fails (`setup.sh` checks before it tries).
3. **Ali:** the ISO from ops to the core node, from the workstation:
   `scp -3 aliammar@10.10.90.91:<store path> root@10.10.50.11:/var/lib/vz/template/iso/pbs-installer.iso`.
   Then on the node: fetch `proxmox.sh` from the branch, read it, run it, and (first install only)
   leave 2040 out of the core node's backup job:
   ```sh
   curl -fsSL https://raw.githubusercontent.com/aliammar03/skynet/refs/heads/<branch>/pbs/proxmox.sh -o /root/proxmox-pbs.sh
   sh /root/proxmox-pbs.sh
   pvesh set /cluster/backup/backup-c59694d0-3593 --exclude 2020,240,731,751,9000,9090,10015,2040
   ```
   The VM installs itself in a few minutes and reboots into PBS.
4. **Agent:** scan the host key, run `setup.sh`, reboot, check. The scanned key is new, so ssh
   can't ask about it:
   ```sh
   kh=$(mktemp); ssh-keyscan -t ed25519 10.10.20.40 2>/dev/null > "$kh"; cut -d' ' -f2- "$kh" > pbs/ssh_host.pub
   tar -C pbs -c setup.sh etc | ssh -o UserKnownHostsFile="$kh" -o GlobalKnownHostsFile=/dev/null root@10.10.20.40 \
     'rm -rf /root/pbs && mkdir /root/pbs && tar -C /root/pbs -x && sh /root/pbs/setup.sh; s=$?; rm -r /root/pbs; exit $s'
   ```
   `setup.sh` prints each file's diff as it installs it. A difference worth keeping (something the
   installer wrote) goes into `etc/`.
5. **Ali:**
   - on the core node, `qm guest exec 2040 -- ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub`
     shows the fingerprint the PR names;
   - PBS's UI at https://10.10.20.40:8007, as root (`nix shell nixpkgs#sops -c sops -d --extract '["root_password"]' pbs/secret.sops.yaml`):
     Configuration → Access Control → API Token → `pve@pbs!core` → **Regenerate**, and copy the
     secret. The ACLs stay. (In its Shell instead:
     `proxmox-backup-debug api set /access/users/pve@pbs/token/core --regenerate true`.)
   - the core node's UI: Datacenter → Storage → Add → Proxmox Backup Server: ID `pbs`, server
     10.10.20.40, username `pve@pbs!core`, password the secret, datastore `skynet`, namespace
     `core`, fingerprint from the PR, Backup Retention "Keep all backups" (PBS prunes), Encryption
     "Auto-generate a client encryption key". Store the key it offers in the password manager
     (survival kit). Then Datacenter → Backup → the job → storage `pbs`;
   - the same on the network node with token `network` and namespace `network`.
6. **Agent:** the PR's last commit: `ssh_host.pub` and its pin in `modules/agent.nix`, caddy-admin's
   pinned cert (`stacks/admin/caddy-admin/certs/pbs.pem`) and `tls_server_name`, and `etc/` equal
   to the host.

The first night writes full backups into `skynet`.

## Change

Edit `etc/` in a PR. Once it's merged, the agent runs `setup.sh` again (step 4's line, with the
pinned key), which shows and applies the difference. A change made on PBS first (in its UI, or by
the agent as root) gets its PR the same day; the drift check reports it every morning until `main`
matches.

## Rebuild

Steps 1 and 3–6: a fresh VM from `answer.toml`, then `setup.sh`, which reuses the datastore on
Unraid as it is. The ISO boot makes a new host key and a new self-signed cert, so the PR updates
`ssh_host.pub`, the agent's pin and caddy-admin's cert. Ali regenerates both tokens' secrets and
gives each node's `pbs` storage the new fingerprint and its token. The encryption keys don't change:
they're PVE's.

## Gotchas

- The disk boots first (`proxmox.sh`), so a reboot never reinstalls, even with the ISO attached.
- The NFS mount is hard: while Unraid is down, jobs wait for it. PBS never writes the datastore to
  the local disk, which has no `.chunks`.
- caddy-admin pins PBS's self-signed cert. A new one (a rebuild, or `proxmox-backup-manager cert
  update`) needs `certs/pbs.pem` replaced in the same PR.
- `root@pam`'s mail stays on the box (no relay), so a failed job emails no one.
- `user.cfg` brings the tokens without their secrets (those are in `token.shadow`, never in git).
  **Regenerate** gives each one a secret and keeps its ACLs.
