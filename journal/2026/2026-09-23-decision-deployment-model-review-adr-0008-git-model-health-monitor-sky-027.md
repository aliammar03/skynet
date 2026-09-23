---
date: 2026-09-23
time: 19:32:01            # local HH:MM:SS; orders same-day episodes in the digest
kind: decision          # session | incident | decision
title: Deployment model review: ADR 0008 git model, health monitor, SKY-027
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-025, SKY-027, ADR 0008, PR #260]  # SKY-###, PR #NNN, ADR NNNN, hosts — anything to cross-link
thread_status: open     # none | open | resolved | unknown; digest shows only explicit open
# resolves: [<episode-basename>, …]   # optional: close earlier episodes' open threads (append-only-safe)
---

# 2026-09-23 · decision · Deployment model review: ADR 0008 git model, health monitor, SKY-027

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (journal/README.md). Distillation happens at READ time, never here. -->

## What happened
Ali asked how good Skynet will be at its job and for an opinion on the deployment model, then asked to
add the recommendations, mint the NixOS idea, and propose a new git model for Docker and Tofu.

Assessment given in chat: strong at safe change (trust tiers, saved plans, fail-closed evidence);
weak at noticing outages (docs/design/observability.md: "does not provide live alerting between
nightly runs") and at fixing them (every rollback is a human-merged PR); heavy relative to ~11
compose services on 2 nodes.

Deployment facts found:
- Arcane Git Sync pulls `compose.yaml`; `scripts/gitops-deploy.sh` separately decrypts `.env.sops`
  on the ops VM and writes `.env` into Arcane's project dir via `ssh … docker run --rm -i -v <ppath>:/mnt`
  (lines ~120–160), relying on Arcane auto-sync leaving `.env` untouched.
- NixOS hosts (vm-skynet-ops, lxc-adguard-core) deploy with deploy-rs magicRollback/autoRollback and
  sops-nix; `vm-docker-dmz` (10015) is not NixOS (no `hosts/` entry).
- One tofu root, four actuators; `tofu-apply.sh` rejects mixed scope at runtime (TOFU_APPLY_SCOPE).
- `tofu/.gitignore` ignores `*.tfstate`; `runbooks/dr/DR-core-node.md` says state is only on the ops
  VM and must be re-imported if lost.

## Actions & outcomes
- ADR 0008 (proposed): PR carries the effect → merge is the approval → one executor applies the exact
  revision and refuses a different effect → running revision recorded → automatic return to last
  verified state. Docker: `skynet deploy`, Arcane Git Sync off, `skynet.revision` labels. Tofu:
  per-actuator stacks, plan + normalized-change hash in the PR, apply-on-merge with hash match,
  encrypted state on a `tofu-state` branch, nightly drift plan.
- SKY-025 now 18 phases: 13 = skynet deploy (ADR 0008), 14 = live health monitor (`skynet watch`,
  5-min timer, state-change push alerts), 15 = Tofu under ADR 0008, 16–17 backup/provision, 18 cutover.
  New Done-means boxes and F13–F15.
- SKY-027 minted (idea, long): NixOS Docker host via compose2nix + deploy-rs + sops-nix; start after
  SKY-025.

## Graveyard — tried & abandoned
- State on `main` → rejected: churns every PR and races review.
- Remote state backend → rejected: another service to run and back up.
- Keeping Arcane Git Sync alongside `skynet deploy` → rejected: two actors again.
- k3s + Flux (in SKY-027 options) → far more machinery than the lab needs.

## Follow-ups / open threads
- ADR 0008 becomes accepted only when SKY-025 Phases 13 and 15 land; AGENTS.md §4 and the
  constitution change with those phases (human-merged).
