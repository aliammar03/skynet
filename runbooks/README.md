---
summary: "Catalog of engine-neutral procedures any agent can execute, each tagged by tier and trigger — the routing menu."
tokens: 1601
---

# runbooks — procedures any agent can execute

A **runbook** is a plain-markdown procedure. Nothing auto-loads them; an agent reads one
when a task (or a `SKY-###` directive's ▶ Execute prompt) calls for it. That keeps them free
at startup and — because they're just markdown + bash — readable by **every** engine
(Codex CLI, Claude Code, Goose, Amp…). This is deliberate: Skynet is agent-agnostic by
contract (see [`../AGENTS.md`](../AGENTS.md)), so procedures live here as prose, **not** as any
one vendor's skill/command format.

**This file is that catalog** — the menu so a runbook is never invisible. Each runbook opens
with its own **Tier** and (where relevant) **Trigger** line; the summaries below mirror them.

## Diagnosis (imperative — "diagnose imperatively, fix declaratively")

| Runbook | Tier | What it does |
|---|---|---|
| [`recon.md`](recon.md) | T1 read-only | **Start here.** One `scripts/recon.sh <host>` snapshot — units, disk/inodes, ports, containers, recent warnings + changes — with **no grant to observe**, then branch to a diagnosis runbook. Trigger: *"figure out why X is broken."* |
| [`diagnose/container-crashloop.md`](diagnose/container-crashloop.md) | T1 diagnose · fix = compose PR | A container `Restarting`/`unhealthy`/exiting — exit code + logs + healthcheck + env layering → the cause → a `compose/` fix. |
| [`diagnose/disk-full.md`](diagnose/disk-full.md) | T1 diagnose · fix = config/grant | Full FS **or** exhausted inodes — find what ate it (data vs logs vs docker cruft) → rotation/log-limit/resize, declaratively. |
| [`diagnose/dns-failure.md`](diagnose/dns-failure.md) | T1 read · fix = T2 record | A name won't resolve — split internal (Technitium) vs public (Cloudflare), read NXDOMAIN/SERVFAIL → fix declaratively (tofu for internal `aliammar.net`; Cloudflare token for public). |
| [`diagnose/cert-expired.md`](diagnose/cert-expired.md) | T1 inspect · fix = Caddy PR | Expired/failing TLS — read the served cert, find why ACME isn't renewing (HTTP-01/DNS-01/rate-limit/clock) → Caddy-config fix. |
| [`diagnose/backup-missed.md`](diagnose/backup-missed.md) | T1 read (grant for repo) | A missing snapshot / failed timer — timer + last-snapshot age + repo reachability (restic→gdrive, PBS) → timer/creds fix. |
| [`diagnose/arcane-stuck.md`](diagnose/arcane-stuck.md) | T1/T2 · fix = compose PR | A merged compose PR that didn't deploy — Git Sync status + git-vs-running → sync-fail / apply-fail / drift → reconcile in git. |

## Routine operations

| Runbook | Tier | What it does |
|---|---|---|
| [`deploy-service.md`](deploy-service.md) | T2 (PR-gated) | Add or update a service the skynet way — Arcane GitOps, pinned digests, `.env.sops` secrets, healthcheck + role tag. Includes the one-time legacy→GitOps cutover. |
| [`publish-service.md`](publish-service.md) | T2 (PR-gated) | Give a service a real URL (`https://<svc>.aliammar.net`) through the apps Caddy — edit one Caddyfile → PR → deploy. Own-auth reverse-proxy path (P3 adds the Authentik forward-auth path). |
| [`nightly.md`](nightly.md) | T1 read + PR | The `skynet-nightly.timer` maintenance pass: refresh inventory → envsync → render docs → (agent) narrative + grant audit → open a PR. Report-only until actions are promoted. Documents the engine order + deterministic fallback. |
| [`update-guests.md`](update-guests.md) | T2 snapshot + T2+ fleet root grant | Update all guests. Trigger: *"Update all guests."* |

## Provisioning

| Runbook | Tier | What it does |
|---|---|---|
| [`provision-vm.md`](provision-vm.md) | T2 tofu apply + T2+ root grant | **Declarative (SKY-008)** — declare the guest as an OpenTofu resource cloning the base template, `plan`/apply, then harden with restic under a scoped root grant. Trigger: *"Set up a VM for X, hardened, with restic."* |
| [`provision-lxc.md`](provision-lxc.md) | T2 tofu apply (API-only) + deploy-rs | **NixOS pool LXC (SKY-021/024)** — a new CT = a `proxmox_virtual_environment_container` block (from the NixOS vztmpl, MAC pinned) + a `hosts/lxc-<name>/` flake host + PR → `tofu apply` (tofu owns the envelope) → Option C key inject → `deploy` (nix owns the inside). Trigger: *"Set up / deploy a new LXC for X."* |

## Backup & restore

| Runbook | Tier | What it does |
|---|---|---|
| [`backup.md`](backup.md) | T2+ (root grant) | How restic/PBS backups run, and how to trigger one on demand. See [`../docs/backup-strategy.md`](../docs/backup-strategy.md) for the *why*. |
| [`restore-service.md`](restore-service.md) | T2 (+ PBS token for a VM restore) | Conversational, deterministic recovery of a service's data — or a whole guest. Written so any agent runs it verbatim. |

## Disaster recovery (`dr/`)

These assume the lab is gone and the DR agent starts from a laptop + phone hotspot and this repo.

| Runbook | Tier | What it does |
|---|---|---|
| [`dr/DR-network-node.md`](dr/DR-network-node.md) | DR | Rebuild `server-proxmox-network` — OPNsense + routing — needing nothing from the dead lab. |
| [`dr/DR-core-node.md`](dr/DR-core-node.md) | DR | Rebuild `server-proxmox-core` when it dies carrying PBS; recover via the L5 off-site copy on Google Drive. |
| [`dr/survival-kit.md`](dr/survival-kit.md) | reference | The paper + password-manager kit stored **outside** Skynet (keys, IDs, one printed page). Without it, encrypted history is confetti. Verified quarterly. |

## Adding or changing a runbook

- Keep it **engine-neutral**: markdown prose + plain bash, no vendor-specific invocation.
- Open with a **Tier** line (and **Trigger** where there's a natural phrase), matching §1 of `AGENTS.md`.
- Add a row here in the same PR — an uncatalogued runbook is an invisible one.
- **Don't hardcode unverified specifics.** A host IP, hostname, or container name goes in as a clear
  `<placeholder>`, or cites the generated host map (`docs/generated/`) — never a value typed from
  memory.
- **Before committing, run `scripts/budget-frontmatter.sh`** to stamp the generated `tokens:` line
  (never hand-set it — the pre-commit hook rejects a stale/missing value). Author `summary:`/`trigger:`.
- Anything touching **T2+/T3** or a blast-radius boundary must also PR `docs/system-design.md`.
