---
summary: "The trust tiers in full — every token, ACL, principal, and the auto-expiring SSH root grant Skynet can request but never mint."
tokens: 1776
---

# Spoke · Access & trust

> The trust tiers in full — every token, ACL, principal, and the auto-expiring root grant that is
> Ali's entire job in this system. Governed by [`../system-design.md`](../system-design.md).
> Sourced from plan §2 (tiers), §7 (Proxmox operate), §8 (SSH access model).

## The four tiers, concretely

The constitution holds the tier table; this is what implements each one.

**T1 Read — always standing.** Read-only API tokens on both Proxmox nodes, PBS, Technitium, plus
the OPNsense `config.xml` git mirror. Never writes.

**T2 Operate — standing, PR-gated changes.** Scoped write tokens on the `ops-managed` pools,
unprivileged `svc-ops` SSH on workload hosts, a Technitium scoped token (Zones only), the Arcane
API key. Backup/snapshot of ops-managed guests is T2 (non-destructive).

**T2+ Root grant — grant-only, self-expiring.** A signed SSH certificate opens a root window on
one host; when it lapses, sshd refuses it. No standing root anywhere.

**T3 Privileged — never standing.** OPNsense, Management Caddy, Authentik, Proxmox node root,
Unraid root, Technitium *server settings*. Reached only via the dormant `ROLE_OPS_PRIV_TARGETS`
alias + per-session credentials, revoked same day.

## Proxmox operate access — both nodes

Identical `pveum` setup on **both** nodes: `svc-ops@pve`, read-only at `/`, write scoped to the
`ops-managed` pool via a custom role and a privilege-separated token.

```bash
pveum user add svc-ops@pve --comment "skynet-ops agent"
pveum acl modify / --users svc-ops@pve --roles PVEAuditor
pveum user token add svc-ops@pve readonly --privsep 0
pveum pool add ops-managed
pveum role add OpsOperator -privs "VM.Audit,VM.PowerMgmt,VM.Config.Disk,VM.Config.CPU,VM.Config.Memory,VM.Config.Network,VM.Config.Options,VM.Allocate,VM.Clone,VM.Console,VM.Snapshot,VM.Snapshot.Rollback,VM.Backup,Datastore.AllocateSpace,Datastore.Audit"
pveum user token add svc-ops@pve operate --privsep 1
pveum acl modify /pool/ops-managed --tokens 'svc-ops@pve!operate' --roles OpsOperator
pveum acl modify /pool/ops-managed --users  svc-ops@pve            --roles OpsOperator
pveum acl modify /pool/ops-managed --users  svc-ops@pve            --roles PVEAuditor  # pool membership audit
pveum acl modify /storage/local    --tokens 'svc-ops@pve!operate' --roles OpsOperator
```

The operate token is privilege-separated, so its effective rights are **user ∩ token** — grant
`OpsOperator` to the **user** on the pool as well as the token, else every write is stripped.
`bootstrap-proxmox.sh` encodes both.

`VM.Snapshot` + `VM.Snapshot.Rollback` power the snapshot-before-upgrade safety net;
`VM.Backup` powers on-demand and update-run backups.

## Proxmox provisioning access — `svc-tofu` (SKY-008)

A separate user + privilege-separated token, two custom roles, **per-node** ACLs (the nodes are
**standalone, not clustered** — each has its own `pveum` DB). No `Sys.Modify`, no `root@pam`, no SSH
(the provider's SSH transport is unconfigured). Bootstrap is out-of-band — Ali runs `pveum` on the
node; tofu never manages the token it authenticates with.

```bash
# Roles: lifecycle (heavy) vs. create-time config-only
pveum role add TofuProvisioner -privs "VM.Audit,VM.Allocate,VM.Clone,VM.Config.Disk,VM.Config.CPU,VM.Config.Memory,VM.Config.Network,VM.Config.Options,VM.Config.HWType,VM.Config.Cloudinit,VM.PowerMgmt,Pool.Allocate,Pool.Audit,Datastore.AllocateSpace,Datastore.AllocateTemplate,Datastore.Audit,SDN.Use"
pveum role add TofuVmConfig    -privs "VM.Config.Options,VM.Config.Cloudinit,VM.Config.CDROM"

# User + privsep token
pveum user add svc-tofu@pve --comment "opentofu provisioning agent (SKY-008)"
pveum user token add svc-tofu@pve operate --privsep 1

# READ (T1, full node) — user + token
pveum acl modify / --users  svc-tofu@pve           --roles PVEAuditor
pveum acl modify / --tokens 'svc-tofu@pve!operate' --roles PVEAuditor

# WRITE (lifecycle) — TofuProvisioner on the pool + its storages + the SDN zone. Bind BOTH per path.
for path in /pool/ops-managed /storage/local /storage/local-lvm /sdn/zones/localnetwork; do
  pveum acl modify "$path" --tokens 'svc-tofu@pve!operate' --roles TofuProvisioner
  pveum acl modify "$path" --users  svc-tofu@pve            --roles TofuProvisioner
done

# CREATE-TIME config — config-only role at /vms (no VM.Allocate/VM.PowerMgmt)
pveum acl modify /vms --tokens 'svc-tofu@pve!operate' --roles TofuVmConfig
pveum acl modify /vms --users  svc-tofu@pve            --roles TofuVmConfig
```

Load-bearing rules:

- **Privsep intersection.** A privsep token's effective privileges are **user ∩ token** on each path
  — bind the role on **both** user and token, on every write path (and grant `Pool.Audit` in the role,
  not just at `/`: the `/`-level read doesn't survive the intersection at a path that carries a role).
- **Heavy privs are pool-scoped.** `VM.Allocate` (create/**destroy**) and `VM.PowerMgmt` (start/**stop**)
  live only in `TofuProvisioner`, bound only on `ops-managed`. The `/vms` config role exists because a
  new VMID isn't a pool member yet at `qmcreate`, so its config checks have no pool fallback; it can
  rewrite name/tags/onboot + cloud-init/CDROM drive on any core VM but **never** destroy/stop/re-disk/re-NIC.
- **Per-node, so 5001/635/837 are untouched.** These ACLs are **core-node only**. The one T3 excluded
  guest on core is Unraid VM 2020 (config-reach only, per above); OPNsense/Caddy/Authentik are on the
  network node, outside this token entirely. Extending to the network node mints its **own** `svc-tofu`;
  keep those three untouchable by **avoiding the `/vms` binding** there (per-VMID grants for new guests).
- **A separate user** (not a second `svc-ops` token): `svc-ops` must never carry `Pool.Allocate`.
- **No URL download.** `download_file`/`query-url-metadata` needs `Sys.Modify` on `/` (T3) — not
  granted. Base images land in `local`'s `import` store out-of-band (rare, human/root); tofu imports
  from the present volume (`Datastore.AllocateSpace` only, never calls `query-url-metadata`).

## Pool membership = the blast-radius dial

Joining a guest to an `ops-managed` pool *is* the act of handing the agent T2 over it. The pool
set is the Proxmox half of the write blast radius (the SSH half is `ROLE_OPS_SSH_TARGETS`, see
[network](network.md)). **Two pools today — a count, not a law;** new pools join by PR to the
constitution. Permanently excluded: **VM 5001 (OPNsense)** — never any pool — plus CT 635, CT 837,
Unraid VM 2020 (seen at T1, T3 otherwise).

## SSH access model — standing user + auto-expiring root

Two layers on every workload host:

- **Standing:** unprivileged `svc-ops` (docker group) via ordinary `authorized_keys` — inventory,
  docker contexts, log reading.
- **Elevation:** **OpenSSH user certificates** signed by a CA that lives on *Ali's workstation*,
  never on Skynet.

### Why certificates beat every alternative

A signed cert carries its own expiry (`-V +2h`); when it lapses, sshd simply refuses it. No
sudoers to install and remove, no cron cleanup, no revocation infra. The approval act is Ali
running one command; the de-provisioning act is physics. **Because the CA private key sits on the
workstation, the agent cannot mint its own access — temporary is guaranteed by construction.**

### One-time setup

```bash
# workstation — create the CA (passphrase-protect it; copy to the password manager)
mkdir -p ~/.skynet-ca && ssh-keygen -t ed25519 -f ~/.skynet-ca/ops_ca -C "skynet-ops-ca"
```

`scripts/onboard-host.sh` runs once per managed host — installs CA trust, the principal mapping,
and an sshd snippet (`TrustedUserCAKeys`, `AuthorizedPrincipalsFile`, `PermitRootLogin
prohibit-password`). The `ubuntu-2404-skynet` golden template bakes this in, so new guests are
born onboarded.

### The grant — Ali's entire job

`bin/grant-root <host|all> [duration=2h]` on the workstation fetches the agent's pubkey, signs a
cert with principal `ops-root-<host>` valid for the window, and pushes it back. Per-host certs
land in `~/.ssh/certs/<host>-cert.pub` with a `Match user root` ssh_config block, so
**multiple host grants coexist**. Alias `gr='~/skynet/bin/grant-root'` makes it `gr docker-dmz 1h`.

**How it plays out:** the agent tries T2 first; if root is genuinely needed it stops and prints
the exact `gr …` line; Ali types it in a second pane (~2s); the agent polls
`~/.ssh/certs/<host>-cert.pub`, sees it, and works silently until the cert evaporates. The KeyID
(`grant+host+timestamp+by-ali`) lands in every host's sshd log on use — the audit trail writes
itself and the nightly run greps it into `inventory/`. **The signature never happens on Skynet.**

What this enables: `provision-vm`, `update-guests` (snapshot → `apt full-upgrade` → verify →
next, rollback on failure), and real-root diagnosis — each under one grant Ali types.

## The Authentik scoped-token boundary (realized — SKY-003)

Authentik's graduation out of T3 is no longer hypothetical — directive
[SKY-003](../../planning/projects/SKY-003-apps-reverse-proxy-authentik-sso-ingress.md) implements it
on exactly the Technitium pattern (view/modify a slice, never settings):

- **T2 (scoped `svc-skynet` token):** CRUD **Applications** + **Providers**, and **bind an existing
  outpost**. That is the whole surface — enough to publish a forward-auth app routinely, nothing more.
- **T3 (never in scope):** **Flows** and **Policies** (the authentication spine), **Users** and
  **Groups**, **System settings**, outpost tokens, and **signing keys**.
- **How the token is born:** a one-time T3 ceremony Ali performs in the Authentik UI — Skynet cannot
  mint it. Stored `0600` at `/opt/skynet-ops/secrets/authentik.env` (or sops), and its scope is
  *verified real* (it must demonstrably fail to touch Flows/Users/settings/keys).

The full two-door + forward-auth model, and the honest docker-group≈root caveat that the merge gate
guards, live in the [identity-and-proxy](identity-and-proxy.md) spoke.

## Planned expansion

- **More hosts / more pools under T2.** The operate model generalizes without redesign: onboard to
  the CA, decide pool membership, add to `ROLE_OPS_SSH_TARGETS`, land in inventory. A *new pool* is
  the only move that touches the constitution (it widens the dial).
- **OpenTofu provisioning** (SKY-008). `svc-tofu` token carries `TofuProvisioner` — same pool-scoped
  shape as `svc-ops`/`OpsOperator` but trades backup/snapshot privs for `Pool.Allocate`. The
  autonomy ratchet: `apply` starts human-gated; `destroy` stays a hard checkpoint permanently;
  create/modify graduates to auto-approve one action at a time, by PR.
