# Survival kit

What has to exist outside the lab so that, with both nodes, Unraid and every VM gone, the repo and
Drive bring it all back (`restore.md`, case 6). Ali keeps it: in the password manager, and the
three keys (1–3) on paper too, stored away from the house. A fire takes the lab and anything kept
beside it.

Every other secret is in git, encrypted to key 1. Items 4–7 are in git as well; the kit holds them
anyway, so losing key 1 doesn't also lose the backups.

**Never fill it in here, in an issue or in a chat: this repo is public.**

## The kit

Commands run on the workstation, in the repo, unless the row says otherwise. `sops` there is
`nix shell nixpkgs#sops -c sops`.

| # | Item | Opens | Copy it with | Check value |
|---|---|---|---|---|
| 1 | age master key | every sops file in git | `cat ~/.config/sops/age/keys.txt` | public key `age1wl4e…q8savt2` |
| 2 | PVE's PBS encryption key, server-proxmox-core | core's guest backups, on PBS and on Drive | as root on the node: `cat /etc/pve/priv/storage/pbs.enc` | fingerprint `f9:8f:…:af:36` |
| 3 | PVE's PBS encryption key, server-proxmox-network | the network node's guest backups | the same, on that node | fingerprint `d1:68:…:08:e0` |
| 4 | restic password, docker-dmz | its app data on Drive (`gdrive:skynet/restic/docker-dmz`) | `sops -d --extract '["RESTIC_PASSWORD"]' stacks/dmz/backup/secret.sops.env` | it lists the snapshots |
| 5 | restic password, docker-admin | its app data on Drive (`gdrive:skynet/restic/docker-admin`) | `sops -d --extract '["RESTIC_PASSWORD"]' stacks/admin/backup/secret.sops.env` | it lists the snapshots |
| 6 | Google OAuth client: ID and secret | Drive, through rclone (scope `drive.file`: what rclone made) | `sops -d --input-type ini --output-type ini stacks/admin/backup/rclone.sops.conf`: `client_id`, `client_secret` (not the token) | `rclone lsd gdrive:skynet` lists `pbs` and `restic` |
| 7 | PBS root password | PBS's UI (realm Linux PAM) and console | `sops -d --extract '["root_password"]' pbs/secret.sops.yaml` | it logs in at https://10.10.20.40:8007 |

- **Key 1** is the file's three lines: the date, the public key, and `AGE-SECRET-KEY-1…`.
- **Keys 2 and 3** are JSON files, kept whole. PVE generated them with no passphrase, so the file
  alone opens the backups. For paper, as root on the node:
  `proxmox-backup-client key paperkey /etc/pve/priv/storage/pbs.enc --output-format text`.
- **The OAuth client** belongs to Google Cloud project `skynet-backup` (`skynetv2.md` → P4 → Drive
  access). With it, a new login gives a new token.

## Accounts the lab hangs on

Each one's login, its second factor, and its recovery codes: without them, losing a phone locks a
door the restore needs.

| Account | Holds |
|---|---|
| GitHub `aliammar03` | this repo, `skynet-opnsense` (OPNsense's config), the Renovate app, the agent's access |
| Google | Drive (every backup offsite), Cloud project `skynet-backup` |
| Cloudflare | `aliammar.net`'s public DNS, the tunnel |
| Discord | the server, `#alerts` and its webhook, the bot |
| Tailscale | remote access (signs in through another account: note which) |
| healthchecks.io | the heartbeat checks |

## Logins git doesn't hold

The appliances keep their own. A restore needs each one's console.

| Login | Where |
|---|---|
| `root@pam`, server-proxmox-core | https://10.10.50.11:8006, and its console |
| `root@pam`, server-proxmox-network | https://10.10.50.10:8006, and its console |
| OPNsense `root` | https://10.10.50.1 |
| Unraid `root` | http://10.10.20.20; also its flash backup (Main → Flash → Flash Backup) |
| Omada controller admin | https://10.10.50.25:8043 |
| Home Assistant | http://10.10.30.50 |

## The template

Paste it into one secure note in the password manager, and fill it in there. The check values are
filled in already: they aren't secret, and they prove the right key went in.

```text
SKYNET SURVIVAL KIT                                       last checked: ____-__-__
Restore with: github.com/aliammar03/skynet → runbooks/restore.md, case 6

1. age master key (opens every secret in the repo)
   check: age-keygen -y prints age1wl4edsa2pvac5nt0vvyagnmk3q756ee7lcy4gs6eenasjsl8eeaq8savt2
   # created: ____________________
   # public key: age1wl4edsa2pvac5nt0vvyagnmk3q756ee7lcy4gs6eenasjsl8eeaq8savt2
   AGE-SECRET-KEY-1______________________________________________________________
   on paper at: ______________________________         [ ] checked

2. PVE backup key, server-proxmox-core (/etc/pve/priv/storage/pbs.enc)
   check: fingerprint f9:8f:19:c9:62:dd:79:f7:ef:bb:1c:96:2b:7b:7d:9a:c3:18:65:46:fd:2e:9a:dd:1f:c6:76:c6:80:99:af:36
   the whole file: _______________________________________________________________
   on paper (paperkey) at: ______________________         [ ] checked

3. PVE backup key, server-proxmox-network (/etc/pve/priv/storage/pbs.enc)
   check: fingerprint d1:68:65:94:7e:30:7c:90:5a:cf:af:cd:c0:15:26:4a:03:40:97:b5:76:be:c2:60:17:5b:fb:bd:b8:c7:08:e0
   the whole file: _______________________________________________________________
   on paper (paperkey) at: ______________________         [ ] checked

4. restic password, docker-dmz      repo rclone:gdrive:skynet/restic/docker-dmz
   ______________________________________________          [ ] checked

5. restic password, docker-admin    repo rclone:gdrive:skynet/restic/docker-admin
   ______________________________________________          [ ] checked

6. Google OAuth client (Cloud project skynet-backup, Desktop app, scope drive.file)
   client ID:     _______________________________________________
   client secret: _______________________________________________ [ ] checked

7. PBS root password (https://10.10.20.40:8007, realm Linux PAM)
   ______________________________________________          [ ] checked

Accounts: login, second factor, recovery codes stored
   [ ] GitHub aliammar03        [ ] Google        [ ] Cloudflare
   [ ] Discord                  [ ] Tailscale (signs in with: __________)
   [ ] healthchecks.io

Appliance logins stored
   [ ] Proxmox root@pam, core   [ ] Proxmox root@pam, network   [ ] OPNsense root
   [ ] Unraid root (+ flash backup, dated ____-__-__)   [ ] Omada admin   [ ] Home Assistant
```

## Check it

Once now, then yearly, and after anything under Keep it current. Each check reads only.

1. **Key 1:** save the kit's three lines to a file, then
   `nix shell nixpkgs#age -c age-keygen -y <file>`: it prints the public key above. Delete the file.
2. **Keys 2 and 3:** save each to a file, then
   `nix shell nixpkgs#proxmox-backup-client -c proxmox-backup-client key show <file>`: its
   fingerprint matches the row's. Delete the files.
3. **restic (4, 5) and the OAuth client (6):** a scratch rclone config with the kit's client:
   ```sh
   nix shell nixpkgs#rclone nixpkgs#restic
   rclone config --config /tmp/kit.conf      # remote gdrive, type drive, the kit's client, scope drive.file
   rclone --config /tmp/kit.conf lsd gdrive:skynet
   RCLONE_CONFIG=/tmp/kit.conf restic -r rclone:gdrive:skynet/restic/docker-dmz snapshots
   RCLONE_CONFIG=/tmp/kit.conf restic -r rclone:gdrive:skynet/restic/docker-admin snapshots
   rm /tmp/kit.conf
   ```
   restic asks for each password: the kit's opens it.
4. **PBS's password (7):** log in to its UI.

Then the note's date.

## Keep it current

Update the kit, and the check values here (a PR), when:
- a Docker host joins or is rebuilt with a new backup repository (another restic password);
- a node's storage `pbs` gets a new encryption key, or a node is reinstalled;
- PBS's root password changes;
- the OAuth client is replaced;
- the age master key is replaced (every sops file is then re-encrypted to the new one).
