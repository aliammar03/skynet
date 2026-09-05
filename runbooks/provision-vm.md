---
summary: "Provision a VM from merged source and an explicitly approved saved plan; creates are supervised T2 without automatic rollback."
trigger: "Set up a VM for X, hardened, with restic"
tier: "Supervised T2 saved-plan create + T2+ root grant"
executor: "OpenTofu saved-plan wrapper, onboard-host.sh, and provision-restic.sh"
rollback: "No automatic rollback for a new VM; operator recovery on partial create"
---

# Runbook — provision a hardened guest (declarative, via OpenTofu)

**Tier:** T2 saved-plan clone/apply + T2+ root grant for hardening. **Trigger:** *"Set up a VM for X, hardened, with restic."*

> **Tofu makes the box exist; cloud-init defines its first boot.** A guest is a `proxmox_virtual_environment_*` resource
> with a real `plan`-before-apply diff, not a hand-run clone. The imperative path is retired.

> [!warning] **Create is supervised, not automatically reversible.** A new VMID has no pre-change
> snapshot. `scripts/tofu-apply.sh` applies the exact approved plan but never auto-destroys a partial
> create. Inspect failures and request separate approval before any cleanup; this path stays below A4.

## Preconditions

- Agree name, VMID/IP, resources, purpose, hardening scope, backups, and partial-create recovery. The merged source and exact saved plan need explicit approval.

## Steps

1. **Plan first** (system-design §9): name, VLAN/IP per convention (VMID = VLAN + last octet),
   resources, purpose, rollback. Get one-word approval.
2. **Declare the guest in `tofu/`.** Add a `proxmox_virtual_environment_vm` resource that **clones the
   base template** `ubuntu-2404-base` (VMID 9000, `tofu/template-ubuntu-2404.tf`) into the
   `ops-managed` pool, and set VLAN/IP/hostname plus a temporary bootstrap SSH key through the
   **API-native `initialization` (cloud-init) block** — **never** the SSH-snippet/`proxmox_virtual_environment_file`
   path (that is a standing node-SSH dependency, forbidden). The base template contains only the
   Ubuntu cloud image; it does **not** bake CA trust or `svc-ops`. Use the bootstrap key for the first
   login, run `scripts/onboard-host.sh` as root with the CA/service public keys, then use the
   auto-expiring root grant for hardening. **Never** add an excluded guest (OPNsense 5001, CT 635/837,
   VM 2020) to any pool. An LXC uses `proxmox_virtual_environment_container`; to bring
   an *existing* container under management, use the zero-drift import recipe in `tofu/lxc-pbs.tf`.
3. **Propose the source.** Open a PR containing the tofu declaration and a speculative plan output;
   Ali reviews and merges the authored change. Do not apply from the unmerged branch.
4. **Save, review, and apply the merged revision.**
   ```
   eval "$(scripts/tofu-env.sh)"
   tofu -chdir=tofu plan -out=/tmp/provision-<newhost>.tfplan
   tofu -chdir=tofu show -no-color /tmp/provision-<newhost>.tfplan
   # STOP: Ali explicitly approves this exact create plan.
   TOFU_APPLY_SCOPE=proxmox-core scripts/tofu-apply.sh /tmp/provision-<newhost>.tfplan
   ```
   Verify running-state via the read API (`/cluster/resources`). If apply or verification fails,
   stop: the wrapper does not auto-destroy a partial create. Do **not** use the guest agent for
   verification because the token omits `VM.GuestAgent.Audit`; keep `agent { enabled = false }`.
5. **Request the grant:** print `bin/grant-root <newhost> 2h` (narrowest host, shortest duration).
   Wait for the cert to land (poll `~/.ssh/certs/<newhost>-cert.pub`, validate with `ssh-keygen -L`).
6. **Harden as root** (inside the window):
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
7. Land refreshed inventory/docs and any hardening definitions in a follow-up PR.
   **Internal DNS:** an apps-Caddy service's
   record derives from the Caddyfile automatically (see [`publish-service.md`](publish-service.md)); a
   standalone host record is its own tofu-managed `technitium_record`. The cert expires on its own —
   no de-provisioning step.

## Verify

- Confirm the VM is running through the read API, onboarding/hardening completed inside the grant window, backups are configured, and the intended service/DNS path works.

## Rollback

- A new VM has no pre-change snapshot. On a partial-create or verification failure, stop for operator recovery; do not auto-destroy. Later definition changes roll back by human-merged `git revert`.

## Evidence

- Preserve the saved plan and approval record; land the provisioning/hardening definitions plus refreshed inventory/docs in the follow-up PR.
