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
   - restic timer (`backup-restic.sh <newhost>`), guest-firewall notes.
5. **PR** recording the new host in `inventory/`, DNS (Technitium T2), and `docs/`. Ali merges.
   The cert expires on its own — no de-provisioning step.
