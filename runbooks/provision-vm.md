---
summary: "Declare a guest as an OpenTofu resource (clone the base template), plan/apply, then harden under a scoped auto-expiring root grant with restic."
trigger: "Set up a VM for X, hardened, with restic"
---

# Runbook — provision a hardened guest (declarative, via OpenTofu)

**Tier:** T2 tofu clone/apply + T2+ root grant for hardening. **Trigger:** *"Set up a VM for X, hardened, with restic."*

> **Tofu makes the box exist; [SKY-007](../planning/archive/) Nix/cloud-init defines what's on it.**
> Provisioning is declarative now (SKY-008) — a guest is a `proxmox_virtual_environment_*` resource
> with a real `plan`-before-apply diff, not a hand-run clone. The imperative path is retired.

## Steps

1. **Plan first** (system-design §9): name, VLAN/IP per convention (VMID = VLAN + last octet),
   resources, purpose, rollback. Get one-word approval.
2. **Declare the guest in `tofu/`.** Add a `proxmox_virtual_environment_vm` resource that **clones the
   base template** `ubuntu-2404-base` (VMID 9000, `tofu/template-ubuntu-2404.tf` — CA trust + `svc-ops`
   baked in → born onboarded) into the `ops-managed` pool, and set VLAN/IP/hostname/SSH-key through the
   **API-native `initialization` (cloud-init) block** — **never** the SSH-snippet/`proxmox_virtual_environment_file`
   path (that is a standing node-SSH dependency, forbidden). **Never** add an excluded guest (OPNsense
   5001, CT 635/837, VM 2020) to any pool. An LXC uses `proxmox_virtual_environment_container`; to bring
   an *existing* container under management, use the zero-drift import recipe in `tofu/lxc-pbs.tf`.
3. **Plan, then apply (⚠ create checkpoint).**
   ```
   eval "$(scripts/tofu-env.sh)"
   cd tofu && tofu plan            # read the EXACT diff — hosts touched, IP, pool
   tofu apply                      # ⚠ creating a guest is a hard checkpoint — Ali approves, never auto
   ```
   The box now exists (clone → boot). Verify running-state via the read API (`/cluster/resources`),
   **not** the guest agent (the token omits `VM.GuestAgent.Audit` by design; keep `agent { enabled = false }`).
4. **Request the grant:** print `bin/grant-root <newhost> 2h` (narrowest host, shortest duration).
   Wait for the cert to land (poll `~/.ssh/id_ed25519-cert.pub`, validate with `ssh-keygen -L`).
5. **Harden as root** (inside the window):
   - SSH lockdown (`PermitRootLogin prohibit-password`, no password auth);
   - `unattended-upgrades`; `fail2ban` where sensible;
   - **restic backups** — one command from skynet-ops (installs restic+rclone, stages secrets 0600,
     generates the repo password on-host, deploys `backup-restic.sh` + the nightly timer, inits the
     repo). Pick what to back up: `--docker` (appdata + `skynet.backup=protect` volumes) and/or
     `--path DIR`, repeatable:
     ```
     scripts/provision-restic.sh <newhost> root@<ip> --docker            # docker host
     scripts/provision-restic.sh <newhost> root@<ip> --path /srv/data    # plain host
     ```
     Idempotent (never regenerates the password / re-inits an existing repo). Afterwards save the repo
     password to the survival kit: `ssh root@<ip> cat /opt/skynet-ops/secrets/restic-<newhost>.pass`.
   - guest-firewall notes.
6. **PR** the tofu config + refreshed `inventory/` + `docs/`. **Internal DNS:** an apps-Caddy service's
   record derives from the Caddyfile automatically (see [`publish-service.md`](publish-service.md)); a
   standalone host record is its own tofu-managed `technitium_record`. Ali merges. The cert expires on
   its own — no de-provisioning step.
