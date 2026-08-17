> Agent-generated research feeding **SKY-008**. Sources are cited inline; recency noted where it matters. Skeptical by design — flags where the ecosystem is rough.

# OpenTofu as a provisioning layer for Skynet

*Compiled 2026-08-17. OpenTofu current stable line is 1.7+ (state encryption GA since 1.7, May 2024).*

## 1. Proxmox provider: bpg vs Telmate

**Pick `bpg/proxmox`.** It is the actively maintained, feature-complete choice; Telmate is effectively legacy for our purposes.

- **`bpg/terraform-provider-proxmox`** — ~2.2k stars, ~2,500 commits, steady PR/issue flow, works under both Terraform and OpenTofu. Declares the resources we actually need: `proxmox_virtual_environment_vm` (clone-from-template + cloud-init), `..._container` (LXC), `..._pool`, `..._user`/`_role`/`_acl`, `..._user_token`, storage/file upload, SDN, firewall, hardware mappings, HA. This is the widest surface of any current provider and maps cleanly onto our pool-as-blast-radius model. ([repo](https://github.com/bpg/terraform-provider-proxmox))
- **`Telmate/proxmox`** — older, narrower (VM/LXC only), historically buggy clone/cloud-init behavior; v3 line is still marked RC. Battle-tested but stagnant relative to bpg. ([registry](https://search.opentofu.org/provider/telmate/proxmox/v3.0.1-rc4))

**Sharp edges (bpg, all documented):**
- **Snippets/cloud-init user-data uploads need SFTP over SSH, not the API token** — a Proxmox API limitation. If we hand-author cloud-init `user_data`/`meta_data` snippets, the provider SSHes to the node (PAM account) to drop files in the snippets store. That is a standing SSH path to a node — **exactly what our trust model forbids.** Mitigation: use only the API-native cloud-init fields (`initialization` block: IP, DNS, SSH keys, user/pass) which go through the token, and avoid the snippet-upload feature entirely. ([bpg cloud-init notes](https://www.trfore.com/posts/provisioning-proxmox-8-vms-with-terraform-and-bpg/))
- **Hardware mappings / PCI passthrough require `root@pam`** — keep those out of tofu; do them manually.
- **Cloud image disk-resize kernel panic** on Debian 12 / Ubuntu unless a serial device is configured — a known one-line fix, but a footgun.
- **Concurrent create → lock errors** ("can't lock file … got timeout"). Keep `-parallelism` low (e.g. 1–2) on shared nodes.
- **HA-managed guests drift** — HA can migrate a guest between nodes without the provider knowing, producing plan noise. Don't put HA guests under tofu, or pin `node_name` and accept drift.

## 2. Declarative VM/CT provisioning + the plan/apply loop

A VM resource clones a prepared **template** (cloud-init-enabled cloud image imported once, manually or via a `..._download_file`/`_file` resource) and sets an `initialization` block for hostname, IP/CIDR, gateway, nameserver, and injected SSH keys — all API-token driven. LXC CTs clone from a CT template similarly. Pools and (optionally) ACLs/tokens are their own resources.

The loop fits Skynet's "agent proposes, human reads diff, apply" model well:
- `tofu plan -out plan.tfplan` produces a **deterministic, reviewable diff** — the artifact a human reads before merge. This is genuinely better than imperative `qm`/`pct` for reviewability.
- Merge → `tofu apply plan.tfplan` (apply the saved plan, so what was reviewed is exactly what runs).
- Rollback = `git revert` the HCL + re-apply, mirroring the Arcane GitOps pattern already in use.

**Caveat for an LLM operator:** plan output is only trustworthy if state is fresh; a stale/locked state or out-of-band change makes the diff lie. And `tofu` is a *high-branching-factor* tool (thousands of arguments, provider quirks) — the opposite of the low-tool-count discipline the design prefers. Constrain the agent to a small, templated module set rather than free-form HCL.

## 3. State file: location, secrets, encryption, token scope

- **Where:** for a single operator VM, a **local backend** (`terraform.tfstate` on `vm-skynet-ops`) is simplest and avoids standing up S3/Postgres. State must **not** be committed in plaintext.
- **State contains secrets:** cloud-init passwords, injected keys, and any provider credentials land in state. Treat the file as secret-bearing, same tier as `project.env`.
- **Encrypt it:** OpenTofu ≥1.7 has native **client-side state & plan encryption** (AES-GCM). For a local single-VM setup use the **PBKDF2 passphrase** key provider, with the passphrase sourced from our existing **sops+age** secret store (decrypt to an env var at runtime, never to disk). This keeps everything inside the encryption story we already have and adds no new online KMS dependency. ([OpenTofu state encryption docs](https://opentofu.org/docs/language/state/encryption/), [env0 1.7 writeup](https://www.env0.com/blog/opentofu-v1-7-enhanced-security-with-file-state-encryption)) — note: **lose the passphrase = unrecoverable state**, so the age-encrypted passphrase must itself be backed up.
- **Scope the API token so tofu cannot reach node-root/T3:** create a dedicated `svc-tofu@pve` user + **scoped API token with Privilege Separation ON**, granted a purpose-built role limited to the operate privileges (`VM.Allocate/Clone/Config.*/PowerMgmt/Migrate`, `Datastore.AllocateSpace/Audit`, `Pool.Allocate`, `SDN.Use`, `Sys.Audit`) and an ACL **restricted to the `ops-managed` pool path**, not `/`. No `Sys.Modify` at node scope, no `Realm`/`User.Modify`, no `root@pam`. That token can create/destroy guests in-pool but cannot touch node config, storage-wide settings, or OPNsense's VM (5001 is pool-excluded anyway). Because Skynet forbids the SSH-snippet path (§1), the token never needs a companion SSH login. ([required-privileges reference](https://www.trfore.com/posts/provisioning-proxmox-8-vms-with-terraform-and-bpg/))

## 4. Technitium DNS

Usable community providers now exist (none official). Options, best-first:
- **`kenske/technitium`** (OpenTofu Registry, published 2025-11, actively iterated) — manages zones/records/DHCP via Technitium's HTTP API with a scoped API token. Newest and most maintained. ([registry](https://search.opentofu.org/provider/kenske/technitium))
- **`kevynb/terraform-provider-technitium`** — record-focused (A/AAAA/CNAME/MX/TXT/SRV/…). ([repo](https://github.com/kevynb/terraform-provider-technitium))
- **`darkhonor/technitium`** — zones/records/TSIG/DNSSEC with STIG-compliance validation at plan time; heavier than we need.

All are small, single-maintainer, pre-1.0 — **supply-chain and abandonment risk is real.** Fits our T2 "Zones view/modify only" boundary if pointed at a **zone-scoped Technitium API token** (no Settings/DHCP/Administration). Reasonable to adopt for record management, but pin the version and vendor the provider binary; do **not** let it touch server settings (T3).

Alternative if we distrust a community provider: the generic **`Mastercard/restapi`** provider against Technitium's documented HTTP API — more boilerplate, zero third-party provider trust, fully auditable calls.

## 5. What belongs under tofu vs stays manual

**Good fit (put under tofu):** creation/lifecycle of `ops-managed`-pool VMs and LXC CTs from templates; pool membership; optionally Proxmox users/roles/ACLs/tokens (careful — self-referential); Technitium zone records. These are the repeatable, in-blast-radius operate tasks.

**Keep manual / out of tofu (hard line):**
- **OPNsense (VM 5001)** and every pool-excluded guest (CT 635, CT 837, Unraid VM 2020) — T3, never touched.
- **Node-level config** (storage definitions, cluster, networking bridges, PCI passthrough, `root@pam` operations).
- **Template creation / cloud-image import** — do once manually or via a tightly-scoped separate config; it's the most SSH/root-adjacent step.
- **The Proxmox token/role that tofu itself uses** — bootstrap it by hand so tofu can't rewrite its own leash.
- Docker services stay in **Arcane/compose** — tofu provisions the *host*, not the workloads.

## 6. Honest tradeoffs & top risks for an LLM operator

1. **Tofu is high-branching-factor** — huge argument surface, provider-specific quirks (§1). Counter to the design's low-tool-count principle. Mitigate with a small, opinionated module library the agent fills in, not free-form HCL.
2. **The SSH-snippet trap** — the most-blogged cloud-init path silently introduces a node SSH dependency that breaks our trust model. The agent must *know* to avoid it. High risk precisely because it's the "normal" tutorial path.
3. **`destroy` is irreversible and easy to over-scope** — a bad `-target` or a resource rename can delete a live guest. `tofu destroy`/replacement must be a hard checkpoint, never auto-approved.
4. **State is a secret and a single point of truth** — corruption, stale lock, or lost passphrase are all outage/data-loss modes; drift makes plans lie. Back up encrypted state; refresh before every plan.
5. **Community-provider supply chain** — Technitium providers (and to a lesser degree the ecosystem) are single-maintainer; pin + vendor.
6. **Self-referential ACL/token management** — letting tofu manage the very token it authenticates with is a footgun that can lock the agent out or (worse) let it widen its own grant. Keep that bootstrap out of band.

## Recommended shape for Skynet

Adopt **OpenTofu + `bpg/proxmox`** for lifecycle of in-pool VMs/CTs only, driven by a **scoped, privilege-separated `svc-tofu` token ACL'd to the `ops-managed` pool** (no node/root, no SSH). Use only **API-native cloud-init** (no snippet uploads). Keep **local state, encrypted with OpenTofu native PBKDF2 encryption, passphrase in sops+age**, backed up. Add **`kenske/technitium`** (or `restapi`) for DNS records under a **zone-scoped** token, version-pinned and vendored. Everything T3, node-level, template-bootstrap, and the tofu token itself stays **manual and out of git-driven apply**. The agent works through a **small module library + `tofu plan` diff → human merge → `apply` saved plan**, with `destroy`/replace as a hard checkpoint. This buys deterministic, reviewable, revertible provisioning without opening any new path to root or OPNsense.

---
### Sources
- bpg provider — https://github.com/bpg/terraform-provider-proxmox
- Telmate provider (v3 RC) — https://search.opentofu.org/provider/telmate/proxmox/v3.0.1-rc4
- bpg cloud-init / required privileges — https://www.trfore.com/posts/provisioning-proxmox-8-vms-with-terraform-and-bpg/
- OpenTofu state encryption — https://opentofu.org/docs/language/state/encryption/
- OpenTofu 1.7 state encryption writeup — https://www.env0.com/blog/opentofu-v1-7-enhanced-security-with-file-state-encryption
- kenske/technitium — https://search.opentofu.org/provider/kenske/technitium
- kevynb/technitium — https://github.com/kevynb/terraform-provider-technitium
- darkhonor/technitium — https://github.com/darkhonor/terraform-provider-technitium
- Home lab Terraform modules 2025 — https://www.virtualizationhowto.com/2025/10/best-terraform-modules-for-home-labs-in-2025/
