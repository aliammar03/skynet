# Runbook — provision a hardened VM

**Tier:** T2 clone + T2+ root grant for hardening. **Trigger:** *"Set up a VM for X, hardened, with restic."*

## Steps

1. **Plan first** (§9): name, VLAN/IP per convention (VMID = VLAN + last octet), resources,
   purpose, rollback. Get one-word approval.
2. **Clone the golden template** `ubuntu-2404-skynet` (CA trust + `svc-ops` baked in → born
   onboarded) into the `ops-managed` pool (T2). Assign VLAN/IP, boot. **Never** add to a pool
   any excluded guest (OPNsense 5001, CT 635/837, VM 2020).
3. **Request the grant:** print `grant-root <newhost> 2h` (narrowest host, shortest duration).
   Wait for the cert to land (poll `~/.ssh/id_ed25519-cert.pub`, validate with `ssh-keygen -L`).
4. **Harden as root** (inside the window):
   - SSH lockdown (`PermitRootLogin prohibit-password`, no password auth);
   - `unattended-upgrades`;
   - `fail2ban` where sensible;
   - **restic backups** — one command from skynet-ops (installs restic+rclone, stages secrets
     0600, generates the repo password on-host, deploys `backup-restic.sh` + the nightly timer,
     inits the repo). Pick what to back up: `--docker` (appdata + `skynet.backup=protect`
     volumes) and/or `--path DIR` (any folder), repeatable:
     ```
     scripts/provision-restic.sh <newhost> root@<ip> --docker            # docker host
     scripts/provision-restic.sh <newhost> root@<ip> --path /srv/data    # plain host
     scripts/provision-restic.sh <newhost> root@<ip> --docker --path /srv/extra --time 03:15
     ```
     Idempotent (never regenerates the password / re-inits an existing repo). Afterwards save
     the repo password to the survival kit: `ssh root@<ip> cat /opt/skynet-ops/secrets/restic-<newhost>.pass`.
   - guest-firewall notes.
5. **PR** recording the new host in `inventory/`, DNS (Technitium T2), and `docs/`. Ali merges.
   The cert expires on its own — no de-provisioning step.
