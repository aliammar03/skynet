# runbooks — procedures any agent can execute

A **runbook** is a plain-markdown procedure. Nothing auto-loads them; an agent reads one
when a task (or a `SKY-###` directive's ▶ Execute prompt) calls for it. That keeps them free
at startup and — because they're just markdown + bash — readable by **every** engine
(Codex CLI, Claude Code, Goose, Amp…). This is deliberate: Skynet is agent-agnostic by
contract (see [`../AGENTS.md`](../AGENTS.md)), so procedures live here as prose, **not** as any
one vendor's skill/command format.

**This file is that catalog** — the menu so a runbook is never invisible. Each runbook opens
with its own **Tier** and (where relevant) **Trigger** line; the summaries below mirror them.

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
| [`provision-vm.md`](provision-vm.md) | T2 clone + T2+ root grant | Clone the golden template into a hardened VM with restic. Trigger: *"Set up a VM for X, hardened, with restic."* |

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
- Anything touching **T2+/T3** or a blast-radius boundary must also PR `docs/system-design.md`.
