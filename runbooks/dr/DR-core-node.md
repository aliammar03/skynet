---
summary: "Recover when server-proxmox-core (with PBS aboard) is dead."
trigger: "Core node is dead"
tier: "T2+"
executor: "supervised Proxmox, PBS, and recovery-host procedure"
rollback: "preserve surviving state; stop before destructive recovery changes"
---

# DR — server-proxmox-core is dead (with PBS aboard)

**Tier:** **T2+** (supervised recovery using PBS, Proxmox, and the survival-kit materials).
**Trigger:** `server-proxmox-core` is unavailable and PBS cannot serve restores.

Targeted L5 archive recovery is verified. Rebuilding PBS, attaching the recovered datastore, and
booting a guest after core loss remain unverified and require supervised recovery.

## Preconditions

- The core node is confirmed unavailable; do not overwrite any surviving PBS datastore.
- Have the survival kit's PBS encryption key and the Google Drive `rclone` configuration. These remain
  human-held and never transit the agent.
- Have a recovery host/datastore with enough capacity for the selected restore.

## Steps

1. **Pull the datastore from Google Drive** (L5): `rclone sync gdrive:Skynet/Backups/pbs <local>`.
2. **Stand PBS up first**, re-add the datastore, re-import the client-side encryption key
   (from the survival kit — it never transited the agent).
3. **Then** bring up Unraid, skynet-ops, and the rest, restoring guests from PBS normally.
4. **skynet-ops is a NixOS flake — near-stateless.** Everything it knows is in git,
   with all secrets **sops-encrypted** (`secrets/*.sops`): the tofu tokens (core **and** network),
   the agent SSH key, the login/password hashes. The **only** out-of-band material is the master
   **age private key** (survival kit) — it decrypts all the rest. To restore: reprovision the VM
   from the flake, drop the age key at `/nix/persist/opt/skynet-ops/secrets/age.key` (root `0600`),
   and `nixos-rebuild switch` — sops-nix decrypts every secret to `/run/secrets` (symlinked into
   `/opt/skynet-ops/secrets/`; the agent SSH key lands at `~/.ssh/id_ed25519` the same way). No
   manual per-file secret copy — the age key is the one seed.
   - **Tofu state is in git:** each stack's encrypted state is on the `tofu-state` branch. The
     first `skynet tofu plan <stack>` or apply rebuilds `/opt/skynet-ops/state/tofu/<stack>.tfstate`
     from it; the passphrase comes back with the age key (`tofu-passphrase.sops`). Then
     `skynet tofu drift` should report no changes for every stack.
5. Reconcile: collectors run, `inventory/` diffed against the last pre-disaster commit.

## Verify

- Confirm the recovered datastore is readable and PBS can enumerate the expected archives before any
  guest restore.
- Restore one selected guest, boot it, and verify network, storage, and service health.
- Run collectors and confirm the generated inventory matches the recovered systems.

## Rollback

Stop a failed restore before booting or replacing a guest, preserve the recovered datastore, and retry
into a fresh target. Do not destroy the source copy or overwrite surviving guest disks during recovery.

## Evidence

Record the recovered datastore path, PBS archive/guest restored, verification results, and inventory
diff in a raw journal incident. Include any failed target and the replacement target used.
