---
summary: "The trust tiers in full — every token, ACL, principal, and the auto-expiring SSH root grant Skynet can request but never mint."
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
unprivileged `svc-ops` SSH on workload hosts, a Technitium scoped token (Zones only), a scoped
Authentik token for Applications/Providers, and the Arcane API key. Backup/snapshot of
ops-managed guests is T2 (non-destructive).

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
core-managed guest envelopes (mint a new VMID without a human minting the shell) and owns core
storage/SDN/pools day-2:

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

## Proxmox provisioning access — the operate token (SKY-008 → SKY-024)

Tofu drives Proxmox through the **`svc-ops@pve!operate`** API token — the *same* identity the
imperative ops scripts use. **SKY-008** originally split this off into a dedicated `svc-tofu` user
(privilege-separated, pool-scoped, with a config-only `/vms` role); **[SKY-024](../../planning/projects/SKY-024-tofu-declares-all-pool-guests-api-driven-ct-vm-lifecycle-no-node-ssh.md)
retired that split** — one operator token per node **declares *and* fixes**, instead of granting every
capability twice and leaving neither identity able to do the whole job. The nodes are **standalone, not
clustered**, so each has its own `pveum` DB and its own token. **API-only** — the provider's SSH
transport is unconfigured (bpg needs SSH only for snippets/idmap/local-file imports, none of which our
shape uses), no `root@pam`. Bootstrap is out-of-band — Ali runs `pveum`; tofu never manages the token
it authenticates with.

**Per-node scope** — bright lines held everywhere and machine-checked (`invariants.json`
`operate_token_scope`): **no `Permissions.Modify`** (the token rewriting its own ACLs), **no
`Sys.Modify/PowerMgmt/Console`** (node root), **no node SSH**.

- **Core** — the full VM/Datastore/Pool/SDN operator set at `/` (the SKY-021 `/vms`-root broaden), so
  the token can **mint new VMIDs** and manage core guest envelopes. Service CTs 731 (adguard), 751
  (technitium), and native-created 10030 (athena) are currently **unpooled**; their envelope
  management follows this core ACL rather than pool membership. Unraid VM 2020's envelope is
  technically reachable, but automated and OpenTofu paths must not target it: any power/config
  action is a human hard checkpoint, it stays **unpooled + guest-OS-root T3**, and it is never
  destroyed by the agent.
- **Network** — **pool-scoped, no `/vms`-root**: `OpsOperator` on `/pool/ops-managed` + `/storage/local`,
  plus (SKY-024) `Datastore.AllocateSpace`/`SDN.Use` on `/storage/local-lvm` + `/sdn/zones/localnetwork`.
  It manages *existing* pool guests but **cannot mint a new VMID or touch the T3 guests** (OPNsense 5001,
  Caddy 635, Authentik 837) at the envelope at all. Deliberate: **OPNsense enforces the agent's own
  leash**, so envelope-destroy over it is off by the "never widen your own leash" law. A new network CT
  is a rare, deliberate act (a human mints the shell, or a later PR earns the broaden).

Load-bearing rules:

- **Privsep intersection.** The operate token is privilege-separated: effective privileges are
  **user ∩ token** on each path — a grant must bind the role on **both** `svc-ops@pve` and
  `svc-ops@pve!operate`, on every path (a bare `/` read is shadowed at a path that carries a role).
- **`VM.Allocate` = create *and* destroy**, and Proxmox ACLs can't scope it to "new IDs only" — which
  is exactly why it is off the network node (above) and why the core grant is a `docs/system-design.md`
  change, machine-audited, never a silent `pveum`.
- **No URL download / snippets / SSH.** `download_file`/`query-url-metadata` needs `Sys.Modify` (T3,
  not granted); base images land in `local`'s `import` store out-of-band (rare, human/root) and tofu
  references the present volume. bpg's SSH block stays unconfigured (SKY-024).

## Pool membership and core guest envelopes

Joining a guest to an `ops-managed` pool *is* the normal act of handing the agent T2 over it. The
pool set is the Proxmox half of the write blast radius (the SSH half is `ROLE_OPS_SSH_TARGETS`, see
[network](network.md)). **Two node-local pool bindings today — a count, not a law;** new pools join
by PR to the constitution. Core's root-`/` ACL is a separate, deliberate envelope boundary for
the currently unpooled service CTs 731, 751, and 10030; do not describe those guests as pool
members. Permanently excluded from automated envelope operations: **VM 5001 (OPNsense), CT 635,
CT 837, and Unraid VM 2020.** The core token can technically reach Unraid's envelope, but any
power/config action is a human hard checkpoint and its guest OS remains T3.

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
prohibit-password`). The Ubuntu 24.04 template is only a cloud-image clone source; it does not bake
CA trust or `svc-ops`. A new VM must first receive a temporary cloud-init bootstrap key, then Ali or
the operator runs `scripts/onboard-host.sh` as root with the CA/service public keys before normal
standing or expiring access is used.

### The grant — Ali's entire job

`bin/grant-root <host|all> [duration=2h]` on the workstation fetches the agent's pubkey, signs a
cert with principal `ops-root-<host>` valid for the window, and pushes it back. Per-host certs
land in `~/.ssh/certs/<host>-cert.pub` with a matching `Host <host>` ssh_config stanza, so
**multiple host grants coexist** without offering the wrong certificates. Alias
`gr='~/bin/grant-root'` makes it `gr docker-dmz 1h`.

**How it plays out:** the agent tries T2 first; if root is genuinely needed it stops and prints
the exact `gr …` line; Ali types it in a second pane (~2s); the agent polls
`~/.ssh/certs/<host>-cert.pub`, sees it, and works silently until the cert evaporates. The KeyID
(`grant+host+timestamp+by-ali`) lands in every host's sshd log on use — the audit trail writes
itself and the nightly run greps it into `inventory/`. **The signature never happens on Skynet.**

What this enables: `provision-vm`, `update-guests` (snapshot → `apt full-upgrade` → verify →
next, rollback on failure), and real-root diagnosis — each under one grant Ali types.

## The Authentik scoped-token boundary (realized — SKY-003)

Authentik's graduation out of T3 is no longer hypothetical — directive
[SKY-003](../../planning/archive/SKY-003-apps-reverse-proxy-authentik-sso-ingress.md) implements it
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
- **Reachability:** `HOST_OMADA` (`10.10.50.25`) is in `ROLE_OPS_API_TARGETS`; its HTTPS management
  port is in `PORT_OPS_API`, so rule 360 carries the read-only collector with no dedicated rule.
  `scripts/collect-network-gear.sh` is live and renders the current estate; it still degrades to
  `exit 0` when the credential or controller is unavailable.

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
- **T2 (firewall config, approved; implementation pending):** the boundary permits non-leash aliases
  and rules through the **OPNsense tofu provider**, using human-merged source + the reviewed
  saved-plan executor. SKY-020 has not yet installed the provider/resources or
  T2 write credential, so **there is no live firewall write path today**. Non-destructive maintenance
  is also classified T2 but unavailable until that directive implements and proves it.
- **T3 (never standing):** OPNsense **node root**, **account/API-key/cert admin**, **reboot/halt** (a
  lab-wide outage — a hard checkpoint at every tier), and the **self-leash set** — the rules/aliases
  bounding the agent's own reach (`ROLE_OPS_*`, `ROLE_OPS_PRIV_TARGETS`, the block-other-DNS rules, the
  `svc-skynet-recon`/tofu accounts). The self-leash stays **human-merged forever** even as firewall
  config graduates on the ratchet, and is machine-gated on the `tofu plan` (SKY-018 P7 conftest/Rego).
- **Why not just the git mirror:** `os-git-backup` pushes to the mirror *nightly by default*, so the
  firewall map was routinely stale; the live read removes that lag. **The mirror stays** as the
  rebuild-from-git source of truth (§2a) and DR path — live API for freshness, mirror for truth.
- **How the T1 credential was born (the *safe* setup):** OPNsense's `user-config-readonly` privilege —
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
- **OpenTofu provisioning** (SKY-008 → SKY-024). Tofu runs as the **`svc-ops!operate`** token now (the
  `svc-tofu` split retired — one operator token per node). The autonomy ratchet is unchanged: `apply`
  starts human-gated; `destroy` stays a hard checkpoint permanently; create/modify graduates to
  auto-approve one action at a time, by PR.
