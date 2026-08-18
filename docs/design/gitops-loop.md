---
summary: "How a service change becomes a running container via Arcane, with git-revert rollback and image pinning + Renovate."
tokens: 900
---

# Spoke · The GitOps loop

> How a change to a service becomes a running container, and how versions stay pinned and current.
> Governed by [`../system-design.md`](../system-design.md). Sourced from plan §4 (truth model +
> loop) and §12 (pinning). Naming/compose rules live in [conventions](../conventions.md).

## The truth model

Two private GitHub repos:

- **`skynet`** — operational truth: `AGENTS.md`, `.sops.yaml`, `docs/`, `inventory/` (auto-generated
  JSON, never hand-edited), `compose/<svc>/`, `scripts/`, `runbooks/`, `bin/ops`.
- **`skynet-opnsense`** — automatic pushes from the OPNsense **os-git-backup** plugin: every
  firewall change auto-commits `config.xml`. Complete firewall/DHCP/alias truth with zero standing
  management-plane access — and, critically for DR, **the router config survives the router**.

## The loop

```
edit compose/<svc>/ → branch → PR → Ali merges
   → Arcane Git Sync polls, pulls, reconciles (project read-only in the UI)
   → agent verifies health via Arcane API / docker context, commits refreshed inventory
```

- **One Arcane Git Sync per project dir**, auto-sync on; Arcane's own auto-update polling **off**
  for git-synced projects (one reconciler, one truth).
- **Rollback = `git revert`** — Arcane converges back. SSH + `docker context` is the break-glass
  path when Arcane itself is the patient.
- **Env layering** is Arcane-native (`.env.git` + `project.env` → effective `.env`); the
  secret-bearing `project.env` is what [secrets](secrets.md) encrypts. Every service needs
  `env_file: .env`.
- Auto-sync **only redeploys projects already running** — a stopped project updates on its next
  manual start (matters during maintenance windows).

Restore is conversational and made deterministic by `runbooks/restore-service.md` — pause sync →
stop stack → `restic restore` the dated snapshot → `sops -d` the matching `.env.sops` from that
commit → resume sync → health check → report. (See [backup-strategy](../backup-strategy.md).)

## Image pinning & updates

Every `compose.yaml` pins an **exact version tag**. **Renovate** (Mend's free GitHub App, private
repos, first-class docker-compose manager) watches the repo and opens one PR per bump with release
notes embedded. Arcane's auto-update stays off for git-synced projects.

*"Update everything"* → the agent triages open Renovate PRs, reads the embedded notes, researches
the consequential ones, and reports (routine vs. needs-a-migration vs. propose-deferring) →
Ali says apply → Arcane converges each project → health watch → inventory commit → summary.
Anything unhealthy: `git revert`, Arcane rolls it back.

## Planned expansion

- **Docs-only auto-merge** (the merge-gate dial's first foreseeable loosening) would let the agent
  close the loop on documentation PRs without a human merge — a change to the constitution's merge
  dial and the `AGENTS.md` auto-approve list, not to this mechanism.
- **A managed reverse proxy** gives services a consistent front door and hooks into this loop — the
  apps Caddy publishes routes as a Caddyfile in git, deployed by the same PR → Arcane-reconcile path
  (SKY-003). Its design lives in the [identity-and-proxy](identity-and-proxy.md) spoke; a future step
  is generating that Caddyfile from `inventory/` the way `docs/generated/` already is.
- **Service intake** — `planning/services/` maturing into a steady pipeline feeding this loop.
