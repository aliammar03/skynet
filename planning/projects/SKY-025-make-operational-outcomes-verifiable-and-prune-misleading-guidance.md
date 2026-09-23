---
id: SKY-025
title: Rebuild the Skynet engine in Python
status: in-progress
horizon: long
created: 2026-09-06
updated: 2026-09-23
phases: 17
current_phase: 10
tier_touched: [T1, T2, T2+, T3]
related:
  - docs/system-design.md
  - AGENTS.md
  - docs/conventions/construction.md
  - planning/README.md
---

# SKY-025 · Rebuild the Skynet engine in Python

> One small, tested Python operations application. Simple, reviewable, rebuildable, easy to automate.

## Status

**Current:** phases 1–10 done (every read-only path is Python: collection, entities, cache,
rendering, recall, deployment verification). The process overhaul is in: local pytest suite,
`bin/check`, Light/Full review tiers, agent-agnostic construction, this block as the only tracker.

**Next:** Phase 11 — purge and consolidate. Review: Light.

This block, the phase boxes, and the frontmatter are the **only** progress record. Each phase PR
updates them itself; merge is completion ([construction](../../docs/conventions/construction.md)).

## Done means

SKY-025 is finished when every box holds:

- [ ] One `skynet` command on PATH. No forwarding scripts, no `bin/skynet`, no `bin/ops`.
- [ ] Shell only on the allowlist below; everything else with branching logic is Python.
- [ ] Nightly, deploy, publish, Tofu apply, backup, and restore run through Python on the ops VM.
- [ ] `bin/check` passes, with a failure-case test for every write path.
- [ ] One cold-start rebuild from git alone has been rehearsed and recorded.
- [ ] Docs and runbooks reference only commands that exist.

## Mandate and boundaries

Python for procedural logic, validation, orchestration, collectors, checks, and bounded workflows.
Nix for hosts, packages, services, and timers. OpenTofu for resource declarations. Compose/Caddy for
services and routes. SQL where a query is clearer as SQL. Git, SSH, sops, restic, rclone, PBS, and
deploy-rs stay external tools.

Downtime is accepted; dual engines are not a goal. **Downtime never expands authority:** saved-plan
rules, the self-leash, protected guests (5001, 635, 837, 2020), secret custody, grant boundaries,
and human merge all hold throughout.

### Engineering rules

- Plain functions and synchronous execution. Shared code only for real repeated callers.
- No app server, daemon, queue, workflow database, plugin system, or second scheduler.
- Missing, partial, stale, malformed, timed-out, or indeterminate evidence never reads as healthy.
- Every write path runs one shape: plan → preflight → snapshot/backup → execute → verify →
  rollback or stop → record (target, source/plan identity, steps, verification, recovery state).
  A timed-out write is reconciled before any retry.
- Delete the shell implementation in the same PR that ports it. No compatibility shims.
- Nix owns packaging. No production pip/npm.

### What stays out of Python

| Keep as shell or Nix | Why |
|---|---|
| `bootstrap-workstation.sh`, `bootstrap-proxmox.sh` | run before Python exists; rescue path |
| `backup-restic.sh`, `backup-pbs-gdrive.sh` (or plain Nix units) | thin wrappers over restic/rclone; host-local |
| `bin/grant-root` | workstation-only; the CA never touches the engine |
| `.githooks/pre-commit` | glue that calls the gates |

| Delete, no replacement | Why |
|---|---|
| all `scripts/collect-*.sh`, `render-*.sh`, `entity.sh`, `build-db.sh`, `audit-entities.sh`, `recon.sh`, `bin/recall` | forwarders to finished Python |
| `bin/skynet` | the Nix package puts `skynet` on PATH |
| `scripts/nightly-automerge.sh` | suspended capability stub |
| `scripts/update-clis.sh` | Nix owns CLI packages |

Everything else in `scripts/` and `bin/` is ported by the phase that owns it below.

## Roadmap

| # | Phase | Review | Outcome | Exit evidence |
|---|---|---|---|---|
| 1–10 | Python CLI, collectors, entities, cache, rendering, recall, deploy verification | — | done | merged through PR #257 |
| 11 | Purge and consolidate | Light | forwarders gone; shared collector core | nothing calls a deleted path; `skynet collect all` works live |
| 12 | Census and gates | Full | live facts recorded; gates in Python | blocker table filled; `skynet check` replaces the shell gates, same failures caught |
| 13 | Write-path skeleton + deploy/publish | Full | Arcane deploy, env materialization, Caddy/Auth/DNS publish | real deploy; forced failure rolls back |
| 14 | OpenTofu saved-plan execution | Full | plan policy, snapshot, apply, verify, restore | delete/protected-guest/mixed-scope plans refused; injected apply failure restores the snapshot |
| 15 | Backup, restore, PBS off-site | Full | restic selection/consistency, PBS transfer guards, service/guest restore | empty-source transfer refused; isolated restore of one service |
| 16 | Provision, onboard, OS updates | Full | provision/onboard, pins, age identity, OS-aware updates | one guest provisioned and updated; failed update stops with rollback |
| 17 | Cutover | Full | Python nightly, install on ops VM, final prune, cold start | every "Done means" box ticked; directive archived |

### Phase 11 — Purge and consolidate   `[ ]` · review: Light

1. Delete the forwarders and stubs in the delete list. Rewrite every caller (runbooks, `nightly.sh`,
   systemd units, `nix/packages/skynet.nix` fileset, docs) to call `skynet …` directly.
2. Put `skynet` on PATH through the Nix package for the ops VM and the devshell.
3. One shared module for literal credential files, HTTPS/TLS, atomic writes, and status markers.
   One credential-value rule for every collector.
4. Collectors return result objects; `collect_all` loops over one collector list instead of
   re-parsing each collector's stdout JSON.
5. Existing tests stay green; add tests for the shared module.

### Phase 12 — Census and gates   `[ ]` · review: Full

1. Read-only census of live facts the later phases need (table below); record them in
   `docs/design/` or the owning runbook, not here.
2. Port `check-invariants.sh` and `secret-scan.sh` to `skynet check`; the pre-commit hook and
   `bin/check` call it. Carry every current check and its tests over.

| Needed before | Fact to record |
|---|---|
| 13 | actual Arcane Git Sync command, revision source, materialized env path, mounts |
| 15, 16 | installed restic/PBS scripts, units, enabled instances, paths, packages on each host |
| 17 | active ops VM checkout, package, services, and timers |
| 15, 17 | `/opt/skynet-ops` persistent cert/mirror/state paths that must survive |
| 17 | ignored local state (`.cache`, Tofu state/provider cache) classed as recovery-critical or rebuildable |
| 15 | one independent rebuild/access path proven from the survival kit |

### Phases 13–17

Each follows the write-path shape above and the Full tier. Port the owning shell scripts
(`gitops-deploy.sh`, `gitops-rollback.sh`, `deploy-gate.sh`, `cf-dns-route.sh`, `dns-revert.sh`,
`tofu-env.sh`, `tofu-apply.sh`, `pve-snapshot.sh`, `provision-restic.sh`, `ct-age-identity.sh`,
`onboard-host.sh`, `pin-cert.sh`, `skynet-ops-ssh-certs.sh`, `nightly.sh`, `hygiene.sh`,
`repo-surface.sh`, `bin/ops`, `bin/plan`, `bin/new`) and delete them in the same PR.

## Carry-forward correctness cases

Each needs a test in `tests/` by the phase that owns it.

| Case | Required property | Phase |
|---|---|---|
| F1 | SSH/container failure or empty required set cannot look healthy | 10 ✓, 13 |
| F2 | deploy/API/revision errors cannot be ignored | 13 |
| F3 | unsafe mixed infrastructure actions are refused; partial state stays recoverable | 14 |
| F4 | backup init/timer/target failure cannot report success | 15 |
| F5 | backup/restore consistency is explicit and tested | 15 |
| F6 | fleet operations are OS-aware and stop on failed rollback | 16 |
| F7 | empty/wrong PBS source cannot drive destructive mirror behavior | 15 |
| F8 | stale/missing collectors cannot look current | 3–9 ✓ (tested) |
| F9 | package/config ownership stays singular | 11, 17 |
| F10–F11 | one authority per rule; docs, help, runbooks stay truthful | every phase |

## Live and recovery boundaries

Services may go down; the only recovery path may not. Before live installation or destructive work,
keep the survival kit, workstation access, protected payload/state, credential custody, and scoped
grant rules intact. Git/Nix rollback fits source/config changes; interrupted infrastructure or data
writes need operation-specific recovery evidence, not a blind `git revert`.

## Adjacent directives

SKY-025 replaces existing substrate only. New features stay with their directives: diagnosis
practice (SKY-005), semantic retrieval (SKY-006), runbook capabilities (SKY-012), renderer features
(SKY-015), extra deployment features (SKY-016), autonomy promotions (SKY-017), eight-layer semantics
(SKY-018), OPNsense write path (SKY-020), documentation hygiene (SKY-023), guest declarations
(SKY-024).

## Prompts

```text
Read planning/prompts/execute.md and execute the next phase of SKY-025.
Read planning/prompts/review.md and review PR #<number>.
```
