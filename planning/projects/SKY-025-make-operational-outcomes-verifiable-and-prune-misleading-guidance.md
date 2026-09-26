---
id: SKY-025
title: Rebuild the Skynet engine in Python
status: in-progress
horizon: long
created: 2026-09-06
updated: 2026-09-26
phases: 18
current_phase: 11
tier_touched: [T1, T2, T2+, T3]
related:
  - docs/system-design.md
  - AGENTS.md
  - docs/conventions/construction.md
  - planning/README.md
  - docs/decisions/0008-git-model-for-docker-and-opentofu.md
---

# SKY-025 · Rebuild the Skynet engine in Python

> One small, tested Python operations application. Simple, reviewable, rebuildable, easy to automate.

## Status

**Current:** phases 1–11 done. Every read-only path is Python (collection, entities, cache,
rendering, recall, deployment verification) behind one `skynet` command on PATH (ops VM system
package + devshell); the shell forwarders, `bin/skynet`, `bin/plan`, `bin/new`, and `bin/recall` are
gone. Collectors share one module (`common.py`: literal credentials, HTTPS, atomic writes, results)
and `collect all` loops over one collector list. The process overhaul is in: local pytest suite,
`bin/check`, Light/Full review tiers, agent-agnostic construction, this block as the only tracker,
a two-active-directive limit (SKY-023 archived; SKY-005/006/018/020/024 parked in the backlog),
a docs-only context budget, and weekly batched Renovate image updates. The deploy and Tofu phases
follow the git model proposed in [ADR 0008](../../docs/decisions/0008-git-model-for-docker-and-opentofu.md);
a live health monitor is Phase 14.

**Next:** Phase 12 — census and gates. Review: Full.

This block, the phase boxes, and the frontmatter are the **only** progress record. Each phase PR
updates them itself; merge is completion ([construction](../../docs/conventions/construction.md)).

## Done means

SKY-025 is finished when every box holds:

- [ ] One `skynet` command on PATH. No forwarding scripts, no `bin/skynet`, no `bin/ops`.
- [ ] Shell only on the allowlist below; everything else with branching logic is Python.
- [ ] Nightly, deploy, publish, Tofu apply, backup, and restore run through Python on the ops VM.
- [ ] Docker and OpenTofu follow ADR 0008: effect in the PR, merge is the approval, one executor,
      Tofu state in the `tofu-state` branch; ADR 0008 is accepted.
- [ ] A failed deploy rolls back to the last verified revision without waiting for a human.
- [ ] A service outage reaches Ali's phone within 10 minutes.
- [ ] The nightly is deterministic (no AI engine), runs `bin/check` on `main`, and opens a PR only
      when inventory changed beyond timestamps.
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
| `bin/ops` engine layer (`OPS_ENGINE*`, Codex/Claude fallback) | the nightly is deterministic; agent runs are started on purpose, not by the timer |

Everything else in `scripts/` and `bin/` is ported by the phase that owns it below.

## Roadmap

| # | Phase | Review | Outcome | Exit evidence |
|---|---|---|---|---|
| 1–10 | Python CLI, collectors, entities, cache, rendering, recall, deploy verification | — | done | merged through PR #257 |
| 11 | Purge and consolidate | Light | forwarders gone; shared collector core; `skynet plan`/`skynet new` | nothing calls a deleted path; `skynet collect all` works live |
| 12 | Census and gates | Full | live facts recorded; gates in Python | blocker table filled; `skynet check` replaces the shell gates, same failures caught |
| 13 | Write-path skeleton + `skynet deploy` + publish | Full | ADR 0008 Docker model: one executor, dry-run effect in PR, auto-rollback to last verified; Caddy/Auth/DNS publish | real deploy; forced failure rolls back automatically; Arcane Git Sync off |
| 14 | Live health monitor | Full | `skynet watch` timer every 5 min, push alert on state change | stopped test container alerts within 10 min; recovery alert follows; no alert storm |
| 15 | OpenTofu under ADR 0008 | Full | per-actuator stacks, plan+hash in PR, apply-on-merge with hash match, state on `tofu-state` branch, nightly drift plan | mismatched hash refused; delete/protected-guest refused; injected apply failure restores the snapshot; state rebuilt from git |
| 16 | Backup, restore, PBS off-site | Full | restic selection/consistency, PBS transfer guards, service/guest restore | empty-source transfer refused; isolated restore of one service |
| 17 | Provision, onboard, OS updates | Full | provision/onboard, pins, age identity, OS-aware updates | one guest provisioned and updated; failed update stops with rollback |
| 18 | Cutover | Full | deterministic Python nightly, install on ops VM, final prune, cold start | every "Done means" box ticked; ADR 0008 accepted; directive archived |

### Phase 11 — Purge and consolidate   `[x]` · review: Light

1. Delete the forwarders and stubs in the delete list. Rewrite every caller (runbooks, `nightly.sh`,
   systemd units, `nix/packages/skynet.nix` fileset, docs) to call `skynet …` directly.
2. Put `skynet` on PATH through the Nix package for the ops VM and the devshell.
3. One shared module for literal credential files, HTTPS/TLS, atomic writes, and status markers.
   One credential-value rule for every collector.
4. Collectors return result objects; `collect_all` loops over one collector list instead of
   re-parsing each collector's stdout JSON.
5. Port `bin/plan` and `bin/new` to `skynet plan …` / `skynet new …` (roadmap regeneration,
   stage moves, template stamping) with tests; delete the shell versions.
6. Rename the proof-era `lxc-proof` identity on the production NixOS LXC bootstrap artifact
   (carried from SKY-023 P10). Already done by PR #205 (`lxc-base`); verified, no change.
7. Triage `planning/scratchpad/`: each note becomes an idea directive, moves to `journal/`, or is
   deleted. Ali's personal notes stay unless Ali says otherwise.
8. Existing tests stay green; add tests for the shared module.

### Phase 12 — Census and gates   `[ ]` · review: Full

1. Read-only census of live facts the later phases need (table below); record them in
   `docs/design/` or the owning runbook, not here.
2. Port `check-invariants.sh` and `secret-scan.sh` to `skynet check`; the pre-commit hook and
   `bin/check` call it. Carry every current check and its tests over.

| Needed before | Fact to record |
|---|---|
| 13 | actual Arcane Git Sync command, revision source, materialized env path, mounts, project ownership |
| 14 | a push channel Ali will actually see (ntfy topic or Pushover), and where its credential lives |
| 15 | current Tofu state addresses per actuator, for the per-stack `tofu state mv` split |
| 16, 17 | installed restic/PBS scripts, units, enabled instances, paths, packages on each host |
| 18 | active ops VM checkout, package, services, and timers |
| 16, 18 | `/opt/skynet-ops` persistent cert/mirror/state paths that must survive |
| 18 | ignored local state (`.cache`, provider cache) classed as recovery-critical or rebuildable |
| 16 | one independent rebuild/access path proven from the survival kit |

### Phase 13 — Write-path skeleton, `skynet deploy`, publish   `[ ]` · review: Full

1. Build the write-path shape once (plan → preflight → snapshot → execute → verify → rollback or
   stop → record) as plain functions every later write path reuses.
2. `skynet deploy <svc> [--dry-run]` per ADR 0008: exact merged revision, env decrypted in memory,
   compose and env applied together over the Docker context, `skynet.revision` label, Phase 10
   verifier, automatic redeploy of the last verified revision on failure, then a revert PR.
3. Turn Arcane Git Sync off for every project (Arcane stays a read-only dashboard).
4. Port publishing (`cf-dns-route.sh`, `dns-revert.sh`, Caddy/Auth coordination) onto the same shape.
5. Delete `gitops-deploy.sh`, `gitops-rollback.sh`, `deploy-gate.sh`, and the publishing scripts.
   Update AGENTS.md §4, the gitops-loop spoke, and the deploy/publish runbooks (human-merged).

### Phase 14 — Live health monitor   `[ ]` · review: Full

1. `skynet watch`: a systemd timer on the ops VM runs the Phase 10 verifier for every deployed
   service every 5 minutes (T1 read only).
2. Alert on **state change** only: healthy → unhealthy after two consecutive failures, and back.
   One message per change, no storms, a daily "still down" reminder at most.
3. Push through the channel recorded in Phase 12; its credential is a sops-materialized file like
   every other.
4. Tests: a flapping probe does not alert; a sustained failure alerts once; recovery alerts once;
   a monitor that cannot run reports itself as unavailable rather than silent.

### Phase 15 — OpenTofu under ADR 0008   `[ ]` · review: Full

1. Split `tofu/` into `proxmox-core`, `proxmox-network`, `technitium-dns`, `cloudflare-dns` stacks;
   migrate state with `tofu state mv` as a supervised saved-plan step (zero-change plans after).
2. `skynet tofu plan <stack>` prints the plan and a normalized-change hash for the PR.
3. `skynet tofu apply <stack>` after merge: re-plan, require the PR's hash, keep every current
   refusal (delete/replace, protected guests), snapshot existing guests, apply, verify, restore on
   failure.
4. Commit encrypted state to the `tofu-state` branch after each apply, under a local lock; update
   the DR runbooks so rebuilding reads state from git.
5. Nightly read-only drift plan per stack.
6. Delete `tofu-env.sh`, `tofu-apply.sh`, `pve-snapshot.sh`. Update AGENTS.md §4 and the constitution
   (approval moves into the PR — human-merged).

### Phases 16–17

Each follows the write-path shape and the Full tier. Port the owning shell scripts
(`provision-restic.sh`, `ct-age-identity.sh`, `onboard-host.sh`, `pin-cert.sh`,
`skynet-ops-ssh-certs.sh`) and delete them in the same PR.

### Phase 18 — Cutover   `[ ]` · review: Full

1. **Deterministic nightly.** `skynet nightly` replaces `nightly.sh` and `bin/ops`: collect, render,
   report, PR. No AI engine is invoked by the timer; delete the `OPS_ENGINE*` layer and its env docs.
2. **PR only on real change.** Compare inventory ignoring `collected`/`attempted` timestamps and
   hashes of unchanged snapshots; open a PR only when observed state changed. Freshness receipts
   are still written locally so `collect-status` keeps proving recency. The nightly writes a
   journal episode only on failure or real drift.
3. **Nightly `bin/check` on `main`.** A red result leads the nightly report and opens nothing else.
4. Port `hygiene.sh` and `repo-surface.sh` into `skynet check`; delete them.
5. Install on the ops VM (package, services, timers), run the staged acceptance, and rehearse one
   cold-start rebuild from git alone.
6. Tick every "Done means" box and archive this directive.

## Carry-forward correctness cases

Each needs a test in `tests/` by the phase that owns it.

| Case | Required property | Phase |
|---|---|---|
| F1 | SSH/container failure or empty required set cannot look healthy | 10 ✓, 13 |
| F2 | deploy/API/revision errors cannot be ignored | 13 |
| F3 | unsafe infrastructure actions are refused; partial state stays recoverable | 15 |
| F4 | backup init/timer/target failure cannot report success | 16 |
| F5 | backup/restore consistency is explicit and tested | 16 |
| F6 | fleet operations are OS-aware and stop on failed rollback | 17 |
| F7 | empty/wrong PBS source cannot drive destructive mirror behavior | 16 |
| F8 | stale/missing collectors cannot look current | 3–9 ✓ (tested) |
| F9 | package/config ownership stays singular | 11, 18 |
| F12 | an unchanged lab produces no nightly PR; a red `bin/check` on `main` is reported, never hidden | 18 |
| F13 | env and compose go live together at one revision; a failed deploy returns to the last verified revision | 13 |
| F14 | an outage alerts once within 10 minutes; flapping does not alert; a dead monitor is visible | 14 |
| F15 | a Tofu apply whose plan differs from the PR's is refused; state survives losing the ops VM | 15 |
| F10–F11 | one authority per rule; docs, help, runbooks stay truthful | every phase |

## Live and recovery boundaries

Services may go down; the only recovery path may not. Before live installation or destructive work,
keep the survival kit, workstation access, protected payload/state, credential custody, and scoped
grant rules intact. Git/Nix rollback fits source/config changes; interrupted infrastructure or data
writes need operation-specific recovery evidence, not a blind `git revert`.

## Adjacent directives

SKY-025 replaces existing substrate only. SKY-005, SKY-006, SKY-018, SKY-020, and SKY-024 are
parked in `backlog/` under the two-active-directive limit; one may be started alongside SKY-025.
New features stay with their directives: diagnosis
practice (SKY-005), semantic retrieval (SKY-006), runbook capabilities (SKY-012), renderer features
(SKY-015), extra deployment features (SKY-016), autonomy promotions (SKY-017), eight-layer semantics
(SKY-018), OPNsense write path (SKY-020), documentation hygiene (SKY-023), guest declarations
(SKY-024), one deployment model on NixOS (SKY-027, after SKY-025).

## Prompts

```text
Read planning/prompts/execute.md and execute the next phase of SKY-025.
Read planning/prompts/review.md and review PR #<number>.
```
