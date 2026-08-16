# DR — server-proxmox-core is dead (with PBS aboard)

Core dies carrying PBS, so the off-site copy on Google Drive (L5) is the way back in.

> ⚠️ **A6 drill (2026-08-16) found the off-site copy INCOMPLETE — do not rely on this path
> until a full re-seed verifies.** The restore drill (pull CT 101's 184 chunks from Drive →
> restore) failed: only 93 were present; entire chunk shards past ~`855f` were absent. Root
> cause: the nightly `skynet-pbs-gdrive.service` was TERM-killed at `TimeoutStartSec=6h` every
> night before finishing, so ~46% of the ~39k-chunk store (39,063 local vs ~20,986 on Drive)
> never uploaded — and nothing verified completion, so it looked healthy for weeks. The A4
> "upload proven" claim was a dry-run *scope* estimate, not a completion check.
> Fixed by raising the unit timeout, unthrottling the seed, and adding an `rclone check`
> completion guard (script fails loudly if the copy is incomplete). **Re-seed, confirm the
> guard passes green, then re-run this restore drill to actually prove the round-trip.**

## Steps

1. **Pull the datastore from Google Drive** (L5): `rclone sync gdrive:Skynet/Backups/pbs <local>`.
2. **Stand PBS up first**, re-add the datastore, re-import the client-side encryption key
   (from the survival kit — it never transited the agent).
3. **Then** bring up Unraid, skynet-ops, and the rest, restoring guests from PBS normally.
4. skynet-ops is deliberately **stateless** — everything it knows is in git; its only unique
   material (age key, SSH keypair) is in the survival kit. Rebuild the VM, restore those two
   files to `/opt/skynet-ops/secrets/` (0600), and it is whole again.
5. Reconcile: collectors run, `inventory/` diffed against the last pre-disaster commit.
