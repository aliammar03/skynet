# Drive access: Ali's OAuth client, and a token for rclone

Every copy on Google Drive goes through rclone with Ali's own OAuth client, scope `drive.file`
(ADR-0009): a token sees only the files rclone created. Three stacks hold the token, each in its own
`rclone.sops.conf`: `stacks/dmz/backup`, `stacks/admin/backup` and `stacks/admin/pbs-offsite`.
**All of this is Ali's**: the client and its token are credentials.

## The client (once)

From rclone's [Making your own client_id](https://rclone.org/drive/#making-your-own-client-id):
1. Google Cloud console: create the project `skynet-backup` and enable the Google Drive API.
2. Google Auth Platform:
   - audience External, with an app name and your email;
   - data access: only `https://www.googleapis.com/auth/drive.file`, a non-sensitive scope, so
     Google needs no verification;
   - add yourself as a test user.
3. Clients → Create → Desktop app. Its ID and secret go in the survival kit (item 6).
4. Audience → **Publish app**. While in Testing, Google expires the refresh token after 7 days. If
   Publish is greyed out, Branding first wants a home page, a privacy-policy URL (two pages on
   `aliammar.net` will do) and `aliammar.net` as an authorized domain.

## A token (the first time, or after one is revoked)

1. On the workstation, `nix shell nixpkgs#rclone -c rclone config`: a new remote `gdrive`, type
   `drive`, the client's ID and secret, scope `drive.file`, then log in in the browser. It writes
   `~/.config/rclone/rclone.conf`. Check: `nix shell nixpkgs#rclone -c rclone lsd gdrive:skynet`
   lists `pbs` and `restic` (nothing, for a first token).
2. Into each stack's sops file, on the PR's branch, from the repo's checkout; then the plaintext
   goes. sops doesn't know `.conf`, so the format is given:
   ```sh
   git fetch origin
   git switch <branch>
   nix shell nixpkgs#sops -c sh -c 'set -e; for d in stacks/dmz/backup stacks/admin/backup stacks/admin/pbs-offsite; do sops encrypt --filename-override "$d/rclone.sops.conf" --input-type ini --output-type ini ~/.config/rclone/rclone.conf > "$d/rclone.sops.conf"; done'
   rm ~/.config/rclone/rclone.conf
   git add stacks/dmz/backup/rclone.sops.conf stacks/admin/backup/rclone.sops.conf stacks/admin/pbs-offsite/rclone.sops.conf
   git commit -m "backup: a new Drive token"
   git push origin <branch>
   git switch main
   ```
3. After the merge, the night's three jobs succeed: the two backups at 04:30, the datastore's copy
   at 06:00.

A new token from the same client sees everything the client created, so the restic repositories and
the datastore's copy stay readable. A restore on a bare machine makes its own token the same way, in
its own `rclone config` (`runbooks/restore.md`, case 6).
