---
summary: "Recover when server-proxmox-core (with PBS aboard) is dead."
trigger: "Core node is dead"
---

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
4. **skynet-ops is a NixOS flake (SKY-007) — near-stateless.** Everything it knows is in git,
   with all secrets **sops-encrypted** (`secrets/*.sops`): the tofu tokens (core **and** network),
   the agent SSH key, the login/password hashes. The **only** out-of-band material is the master
   **age private key** (survival kit) — it decrypts all the rest. To restore: reprovision the VM
   from the flake, drop the age key at `/nix/persist/opt/skynet-ops/secrets/age.key` (root `0600`),
   and `nixos-rebuild switch` — sops-nix decrypts every secret to `/run/secrets` (symlinked into
   `/opt/skynet-ops/secrets/`; the agent SSH key lands at `~/.ssh/id_ed25519` the same way). No
   manual per-file secret copy — the age key is the one seed.
   - **Tofu state caveat:** the local PBKDF2-encrypted `tofu/terraform.tfstate` is on the ops VM and
     **not in git**. If lost, `tofu import` the managed guests again (they still exist on Proxmox);
     the state passphrase itself is recoverable (`tofu-passphrase.sops`, via the age key).
5. Reconcile: collectors run, `inventory/` diffed against the last pre-disaster commit.
