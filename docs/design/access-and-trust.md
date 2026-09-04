---
summary: "The trust tiers in full — every token, ACL, principal, and the auto-expiring SSH root grant Skynet can request but never mint."
tokens: 4828
---

# Spoke · Access & trust

> The trust tiers in full — every token, ACL, principal, and the auto-expiring root grant that is
> Ali's entire job in this system. Governed by [`../system-design.md`](../system-design.md).
> Sourced from plan §2 (tiers), §7 (Proxmox operate), §8 (SSH access model).

## The four tiers, concretely

The constitution holds the tier table; this is what implements each one.

**T1 Read — always standing.** Read-only API tokens on both Proxmox nodes, PBS, Technitium, the
**Omada network controller**, and **OPNsense (a scoped read-only API credential)** — plus the
OPNsense `config.xml` git mirror as the rebuild-from-git backstop. Never writes.

**T2 Operate — standing, PR-gated changes.** Scoped write tokens on the `ops-managed` pools,
unprivileged `svc-ops` SSH on workload hosts, a Technitium scoped token (Zones only), the Arcane
API key. Backup/snapshot of ops-managed guests is T2 (non-destructive).

**T2+ Root grant — grant-only, self-expiring.** A signed SSH certificate opens a root window on
one host; when it lapses, sshd refuses it. No standing root anywhere.

**T3 Privileged — never standing.** OPNsense *node root / account / reboot / self-leash rules*,
Management Caddy, Authentik, Proxmox node root, Unraid root, Technitium *server settings*. Reached
only via the dormant `ROLE_OPS_PRIV_TARGETS` alias + per-session credentials, revoked same day.
(OPNsense read+diagnostics is T1, firewall config is T2 via OpenTofu — see below.)

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

### Core-node broaden — full guests/storage/network/pools (SKY-021)

The block above is the **network-node** shape (pool-scoped). On the **core node only**, `OpsOperator`
is broadened to the full provisioning set and bound at the ACL root `/`, so the agent self-provisions
pool CTs (mint a new VMID without a human minting the shell) and owns core storage/SDN/pools day-2:

```bash
# core only — full VM.* / Datastore.* / SDN.* / Pool.* + Sys.Audit; bright lines held out.
pveum role modify OpsOperator -privs "VM.Allocate,VM.Audit,VM.Backup,VM.Clone,VM.Config.CDROM,VM.Config.CPU,VM.Config.Cloudinit,VM.Config.Disk,VM.Config.HWType,VM.Config.Memory,VM.Config.Network,VM.Config.Options,VM.Console,VM.GuestAgent.Audit,VM.GuestAgent.FileRead,VM.GuestAgent.FileSystemMgmt,VM.GuestAgent.FileWrite,VM.GuestAgent.Unrestricted,VM.Migrate,VM.PowerMgmt,VM.Replicate,VM.Snapshot,VM.Snapshot.Rollback,Datastore.Allocate,Datastore.AllocateSpace,Datastore.AllocateTemplate,Datastore.Audit,Pool.Allocate,Pool.Audit,SDN.Allocate,SDN.Audit,SDN.Use,Sys.Audit,Mapping.Audit,Mapping.Use"
pveum acl modify / --users  'svc-ops@pve'         --roles OpsOperator   # privsep: bind BOTH sides
pveum acl modify / --tokens 'svc-ops@pve!operate' --roles OpsOperator
```

**Two bright lines are held out and machine-enforced** — the token carries **no `Permissions.Modify`**
(it can never rewrite its own leash) and **no `Sys.Modify` / `Sys.PowerMgmt` / `Sys.Console`** (no
standing Proxmox node root). The ACL-audit gate (`scripts/collect-proxmox-acl.sh` snapshots the token's
own effective perms → `inventory/proxmox-<node>-acl.json`; `invariants.json` `operate_token_scope` +
`check-invariants.sh` assert it) **fails** if any bright-line priv ever appears, or if node-root
`VM.Allocate` (`/` or `/vms`) shows up on any node other than the declared core. Widening either — the
network node, or a bright line — is a `docs/system-design.md` PR (§2), never a silent `pveum`. Details:
[system-design §2](../system-design.md) core-node exception.

## Proxmox provisioning access — `svc-tofu` (SKY-008)

A separate user + privilege-separated token, two custom roles, **per-node** ACLs (the nodes are
**standalone, not clustered** — each has its own `pveum` DB). No `Sys.Modify`, no `root@pam`, no SSH
(the provider's SSH transport is unconfigured). Bootstrap is out-of-band — Ali runs `pveum` on the
node; tofu never manages the token it authenticates with.

```bash
# Roles: lifecycle (heavy) vs. create-time config + read. TofuVmConfig carries VM.Audit too: the /vms
# binding shadows the propagated `/` PVEAuditor at /vms/<id>, so without it the token would list only
# *pooled* guests. VM.Audit is read-only (T1) — it does not widen write.
pveum role add TofuProvisioner -privs "VM.Audit,VM.Allocate,VM.Clone,VM.Config.Disk,VM.Config.CPU,VM.Config.Memory,VM.Config.Network,VM.Config.Options,VM.Config.HWType,VM.Config.Cloudinit,VM.PowerMgmt,Pool.Allocate,Pool.Audit,Datastore.AllocateSpace,Datastore.AllocateTemplate,Datastore.Audit,SDN.Use"
pveum role add TofuVmConfig    -privs "VM.Config.Options,VM.Config.Cloudinit,VM.Config.CDROM,VM.Audit"

# User + privsep token
pveum user add svc-tofu@pve --comment "opentofu provisioning agent (SKY-008)"
pveum user token add svc-tofu@pve operate --privsep 1

# READ (T1) — user + token, full cluster read. (Node-wide GUEST listing also needs VM.Audit reachable
# at /vms/<id>, which TofuVmConfig above provides; `/` PVEAuditor alone is shadowed by the /vms role.)
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
- **Per-node — one `svc-tofu` per standalone node.** Both nodes run the same setup (core `.11`,
  network `.10`), each with its own user/token/roles and a separate provider (`proxmox.network`). Both
  bind the config-only `/vms` role, so tofu has config-reach — name/tags/onboot + cloud-init/CDROM
  drive — over **every** guest, the T3 excluded ones included (Unraid 2020 on core; OPNsense 5001,
  Caddy 635, Authentik 837 on the network node). Held safe by the same split: **no `VM.Allocate`,
  no `VM.PowerMgmt`** over them, so tofu can **never destroy, stop, re-disk, or re-NIC** an excluded
  guest — those privs stay pool-scoped, per node, and the excluded guests are never pooled.
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

## The Omada controller read boundary (realized — SKY-018 P4)

The Omada software controller (`10.10.50.25`, VLAN 50 Management) owns the switch/AP estate. Skynet
reads it and never touches it — the same view/modify-a-slice split as Technitium and Authentik:

- **T1 (read-only account):** device inventory, ports, PoE state, VLAN/profile assignment, firmware,
  adoption status — everything a collector needs to make the estate visible. That is the whole
  surface.
- **T3 (never in scope):** adopting/forgetting devices, pushing port profiles or WLAN config, and all
  controller/site **server settings**. The agent reads and argues; a human acts.
- **How the credential is born:** Ali creates a **read-only** local account (Omada role *Viewer*) — or
  a read-scoped API key — in the controller UI; Skynet cannot mint it. Stored `0600` at
  `/opt/skynet-ops/secrets/omada.env` (`OMADA_HOST`, `OMADA_USER`, `OMADA_PASS`, and `OMADA_CACERT`
  pointing at a pinned cert), same shape as `cloudflare-dns.env` and the Proxmox collector secrets.
  The account holds no admin rights, so a leak reads the estate and nothing more.
- **Reachability:** the controller is not in the agent's API-target alias by default. Add
  `HOST_OMADA` (`10.10.50.25`) to `ROLE_OPS_API_TARGETS` and the controller's HTTPS management port
  (Omada software-controller default **8043** — confirm on the box) to `PORT_OPS_API`; rule 360 then
  carries it with no new rule. This is a **T3 OPNsense change** — Ali makes it. The collector
  (`scripts/collect-network-gear.sh`) degrades to `exit 0` until both the credential and reachability
  exist, like every other collector.

## The OPNsense tiers (ADR 0006)

OPNsense is the firewall — the enforcement boundary for the whole lab — so it is tiered across three
planes: **read+diagnostics T1, firewall config T2 (PR-gated via OpenTofu), and node-root / reboot /
the agent's own leash T3, never-standing.**

- **T1 (the `svc-skynet-recon` credential, group `skynet-recon`):** the agent reads firewall aliases,
  rules, interfaces, DHCP leases, and neighbour state **live**, and runs **non-mutating diagnostics**
  (ping, traceroute, DNS lookup, ARP/NDP + route + state tables, logs). All observe-or-probe, nothing
  changes state. Stored `0600` sops-nix at `/opt/skynet-ops/secrets/opnsense.env` (`OPN_HOST`,
  `OPN_USER=svc-skynet-recon`, `OPN_KEY`, `OPN_SECRET`, `OPN_CACERT`), same shape as the Proxmox/Omada
  creds. The collector reads scoped endpoints and **strips secrets** out of `inventory/` — hygiene, not
  a boundary (the box already holds the raw `config.xml` via the mirror).
- **T2 (firewall config, PR-gated via OpenTofu):** aliases and rules become `tofu/` resources managed
  through the **OPNsense tofu provider**. A change is a `tofu plan` diff **in a PR** → human-merged →
  `apply` via the API — the exact `svc-tofu`-for-guests model (SKY-008). A separate T2 **write** API
  key (Ali-minted, sops-nix) is used **only** by `apply` on a merged plan; non-destructive maintenance
  (service restart, apply-config, flush) is T2 too. **This is a directive-sized build (firewall-as-code)
  — the T1 read slice ships first.**
- **T3 (never standing):** OPNsense **node root**, **account/API-key/cert admin**, **reboot/halt** (a
  lab-wide outage — a hard checkpoint at every tier), and the **self-leash set** — the rules/aliases
  bounding the agent's own reach (`ROLE_OPS_*`, `ROLE_OPS_PRIV_TARGETS`, the block-other-DNS rules, the
  `svc-skynet-recon`/tofu accounts). The self-leash stays **human-merged forever** even as firewall
  config graduates on the ratchet, and is machine-gated on the `tofu plan` (SKY-018 P7 conftest/Rego).
- **Why not just the git mirror:** `os-git-backup` pushes to the mirror *nightly by default*, so the
  firewall map was routinely stale; the live read removes that lag. **The mirror stays** as the
  rebuild-from-git source of truth (§2a) and DR path — live API for freshness, mirror for truth.
- **How the credential is born (the *safe* setup):** OPNsense's `user-config-readonly` privilege —
  shown in the group's Assigned Privileges list as **"System: Deny config write"** (not "read only",
  which finds nothing) — makes `ApiControllerBase::throwReadOnly()` block **every** MVC/API *config
  write* regardless of page privileges. It does **not** block non-config *actions* (reboot, restart),
  so those pages are simply never granted. Per advisory
  [GHSA-p9pr-782r-w2xw](https://github.com/opnsense/core/security/advisories/GHSA-p9pr-782r-w2xw) the
  guard is **bypassable if assigned directly on the user**, so it **must** go on a group. The recipe
  (a T3 act — the agent cannot mint firewall access):
  1. OPNsense **≥ 26.1.11 / 26.4.1p1** (the advisory fix). 26.7+ is safe.
  2. Group **`skynet-recon`** = **`System: Deny config write`** + the read/diagnostic pages: Firewall
     Aliases/Rules, Interfaces, Services DHCPv4/Kea, and Diagnostics **Ping / Traceroute / DNS Lookup
     / ARP-NDP / Routes / States (view) / Logs**. **Do not** grant Reboot/Halt, service control,
     Firmware, config Apply, or Backups: restore — those are the T3 actions.
  3. User **`svc-skynet-recon`**, member of that group. **Assign every privilege through the group,
     never directly on the user.**
  4. Generate an **API key** for the user → `OPN_KEY` / `OPN_SECRET`.

  The collector degrades to the mirror parse, and to `exit 0` with no credential, so nothing
  hard-depends on it.

## Planned expansion

- **More hosts / more pools under T2.** The operate model generalizes without redesign: onboard to
  the CA, decide pool membership, add to `ROLE_OPS_SSH_TARGETS`, land in inventory. A *new pool* is
  the only move that touches the constitution (it widens the dial).
- **OpenTofu provisioning** (SKY-008). `svc-tofu` token carries `TofuProvisioner` — same pool-scoped
  shape as `svc-ops`/`OpsOperator` but trades backup/snapshot privs for `Pool.Allocate`. The
  autonomy ratchet: `apply` starts human-gated; `destroy` stays a hard checkpoint permanently;
  create/modify graduates to auto-approve one action at a time, by PR.
