# DR — server-proxmox-core is dead (with PBS aboard)

Core dies carrying PBS, so the off-site copy on Google Drive (L5) is the way back in.

## Steps

1. **Pull the datastore from Google Drive** (L5): `rclone sync gdrive:skynet-backups/pbs <local>`.
2. **Stand PBS up first**, re-add the datastore, re-import the client-side encryption key
   (from the survival kit — it never transited the agent).
3. **Then** bring up Unraid, skynet-ops, and the rest, restoring guests from PBS normally.
4. skynet-ops is deliberately **stateless** — everything it knows is in git; its only unique
   material (age key, SSH keypair) is in the survival kit. Rebuild the VM, restore those two
   files to `/opt/skynet-ops/secrets/` (0600), and it is whole again.
5. Reconcile: collectors run, `inventory/` diffed against the last pre-disaster commit.
