# DR — server-proxmox-core is dead (with PBS aboard)

Core dies carrying PBS, so the off-site copy on Google Drive (L5) is the way back in.

> ✅ **This path is PROVEN as of 2026-08-16 (A5.5).** An earlier A6 drill caught the off-site
> copy ~46% incomplete — the nightly `skynet-pbs-gdrive.service` was TERM-killed at
> `TimeoutStartSec=6h` every night before finishing, and nothing verified completion, so it
> looked healthy for weeks (the A4 "upload proven" claim was a dry-run *scope* estimate, not a
> completion check). Fixed in **PR #24**: unit timeout 6h→20h, seed unthrottled, and an
> `rclone check --one-way` completion guard that fails the job loudly if the copy is incomplete.
> After a full re-seed the guard passed clean (**0 differences, 39,513 files**) and the CT 101
> restore drill went green — **184/184** chunks pulled from Drive, `root.pxar` rebuilt
> byte-identical to the live datastore. The nightly guard now keeps this honest going forward.

## Steps

1. **Pull the datastore from Google Drive** (L5): `rclone sync gdrive:Skynet/Backups/pbs <local>`.
2. **Stand PBS up first**, re-add the datastore, re-import the client-side encryption key
   (from the survival kit — it never transited the agent).
3. **Then** bring up Unraid, skynet-ops, and the rest, restoring guests from PBS normally.
4. skynet-ops is deliberately **stateless** — everything it knows is in git; its only unique
   material (age key, SSH keypair) is in the survival kit. Rebuild the VM, restore those two
   files to `/opt/skynet-ops/secrets/` (0600), and it is whole again.
5. Reconcile: collectors run, `inventory/` diffed against the last pre-disaster commit.
