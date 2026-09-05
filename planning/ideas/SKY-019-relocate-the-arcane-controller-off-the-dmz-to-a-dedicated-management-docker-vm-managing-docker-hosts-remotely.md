---
id: SKY-019
title: Relocate the Arcane controller off the DMZ to a dedicated Management docker VM, managing docker hosts remotely
status: draft
horizon: long
created: 2026-09-01
updated: 2026-09-01
phases: 4
current_phase: 0
tier_touched: [T1, T2]   # Provisioning is T2 (svc-tofu, existing). P3 gives the controller a REMOTE
                         # credential to docker hosts + moves where the management plane lives ⇒ a
                         # docs/system-design.md PR (blast-radius/topology change), even though the
                         # unprivileged-SSH mechanism itself is already T2.
related:
  - docs/system-design.md
  - docs/design/gitops-loop.md
  - docs/design/access-and-trust.md
  - compose/arcane-manager/            # the interim in-DMZ capture this directive relocates
  - planning/projects/SKY-018-eight-layer-reconciliation-entity-spine-the-analyze-phase-and-the-verification-toolchain.md
  - planning/archive/SKY-008-opentofu-provisioning-layer-vm-and-ct-lifecycle-plus-dns.md
  - "[[SKY-019-progress]]"
  - "[[arcane-api-reference]]"
---

# SKY-019 · Relocate the Arcane controller off the DMZ to a dedicated Management docker VM

> The GitOps controller currently runs *inside* the least-trusted host it manages. Move it to a
> dedicated Management-VLAN docker VM and have it manage `docker-dmz` (and future hosts) **remotely**,
> so the management brain sits above its blast radius, not inside it.

> **Status: idea.** Promote with `bin/plan start SKY-019`.

## 1. Problem / motivation

`arcane-manager` — Arcane itself, the tool that reconciles every other `compose/` project — runs as a
container **on `guest/docker-dmz-10015`** (VLAN 100, the DMZ), managing that host through a local
`/var/run/docker.sock` mount. That is root-equivalent on the DMZ host, held by the DMZ host. The
management plane is inside the most-exposed VLAN, and a single host both runs the public app
workloads and controls its own deployment. SKY-018 P1 surfaced it as the one running service with no
git home; it now has an interim capture (`compose/arcane-manager/`, bootstrap component) — this
directive delivers the real fix.

## 2. Decisions (settled — recorded so they stay settled)

- **Placement: a dedicated docker VM in Management (VLAN 50), cloned from the `9000` template.**
  Peer to the Management Caddy; management plane out of the DMZ, and **not** co-located on the NixOS
  ops VM (keep the agent brain and the deploy controller as separate blast radii; don't grow a docker
  daemon onto the ops VM). In the `ops-managed` pool so `svc-tofu` can provision it.
- **Remote management over unprivileged SSH**, the mechanism the tier table already names ("Docker
  hosts via Arcane + unprivileged SSH"). Arcane adds `docker-dmz` as a **remote environment** via an
  `svc-ops` docker context / agent; the controller holds a **scoped remote credential**, never a
  local root socket in the DMZ.
- **Secrets:** regenerate `JWT_SECRET`/`ENCRYPTION_KEY` fresh on the new host (clean install) rather
  than migrate the DMZ instance's `/app/data`. Simpler, and the only state worth carrying (which repo,
  which environments) is re-declared, not restored. (If Arcane holds credentials worth keeping by
  cutover, revisit in P2.)

## 3. The plan

- **Scope:** provision the Management docker VM; stand up Arcane on it; wire remote management of
  `docker-dmz`; cut over and decommission the in-DMZ controller.
- **Non-goals:** changing the deployment loop's contract (still `compose/` → PR → sync); onboarding a
  second docker host (the remote model just makes it cheap later); any T3 path.
- **Hosts & tiers touched:** new VLAN-50 guest via `svc-tofu` (T2). **P3 is a `docs/system-design.md`
  PR** — the management plane moves and the controller gains a remote docker credential.
- **Rollback posture:** every phase additive until P4's cutover. The in-DMZ `arcane-manager` keeps
  running until P3 proves the remote controller reconciles correctly; P4 only then stops it. `git
  revert` + re-enable the DMZ container is the back-out.

### Phase 1 — provision the Management docker VM  (~1–2h)   `[ ]` not started
Steps:
1. `tofu/` resource: clone VMID `9000` → a new VLAN-50 guest (canonical VMID, e.g. `50xx`), static IP
   per ADR 0001, `ops-managed` pool, cloud-init installs docker + the `svc-ops` user (docker group).
2. Register a `docker context` / SSH reachability from the ops VM to the new host (mirror `docker-dmz`).
3. Refresh inventory; `bin/ops entities` sees the new guest as **matched** (add its firewall host fact).

Exit criteria: the new guest is up, in-pool, docker runs, `svc-ops` reaches it read-only, and it is
not a running-unmapped hole. Grants: normal PR merge.

### Phase 2 — stand up Arcane on the new host  (~1–2h)   `[ ]` not started
Steps:
1. Deploy `compose/arcane-manager/` on the new host (fresh `JWT_SECRET`/`ENCRYPTION_KEY` → `.env.sops`),
   binding to the Management host IP; front it at `arcane.aliammar.net` via the Management Caddy.
2. Point its Git Sync at this repo; confirm it can read `compose/` (still human-merge gated).
3. Update `compose/arcane-manager/` to the new host's reality (ports, no local `docker.sock` — see P3).

Exit criteria: Arcane is reachable at `arcane.aliammar.net`, healthy, watching the repo, running on the
Management host — with **no `docker.sock` mount** (remote-only, wired in P3). Grants: normal PR merge.

### Phase 3 — wire remote management of docker-dmz  (~1–2h)   `[ ]` not started
**⚠ `docs/system-design.md` PR** — the management plane's location and the controller's remote
credential change the blast-radius description.
Steps:
1. Add `docker-dmz` to Arcane as a **remote environment** over `svc-ops` (context/agent), least-priv.
2. Verify Arcane reconciles the existing DMZ projects **remotely**, read-back health, no local socket.
3. PR `docs/system-design.md` + `docs/design/gitops-loop.md`/`access-and-trust.md`: controller on the
   Management host, docker hosts managed remotely, credential scope + storage.

Exit criteria: a `compose/` change to a DMZ project deploys via the **remote** controller; the design
docs describe the new topology; the credential is `0600` and scoped. Grants: normal PR merge (⚠ the
constitution PR is the checkpoint).

### Phase 4 — cut over and decommission the in-DMZ controller  (~1–2h)   `[ ]` not started
Steps:
1. Stop the in-DMZ `arcane` container; remove its `docker.sock` exposure and `/opt/docker/arcane-manager`
   from the DMZ host (payload only — the definition is in git).
2. The DMZ host no longer runs a controller; confirm `bin/ops entities` + inventory reflect it.
3. Update the entity map / renderer; refresh `SKY-018` cross-refs; close the "relocation pending" notes
   in `compose/arcane-manager/`.

Exit criteria: no controller runs in the DMZ; the DMZ host has no `docker.sock`-mounting container; the
deployment loop runs end-to-end from the Management host. Grants: normal PR merge.

## 4. ▶ Execute prompt
```
Read planning/projects/SKY-019-relocate-the-arcane-controller-off-the-dmz-to-a-dedicated-management-docker-vm-managing-docker-hosts-remotely.md and execute Phase <N>.
Follow AGENTS.md: plan loudly then run quietly, never merge your own PRs, request the
narrowest host / shortest grant the phase needs, and checkpoint at the listed human/grant
steps. Phase 3 needs a docs/system-design.md PR (topology + remote credential) — treat the
constitution PR as the checkpoint. When the phase's exit criteria are met, do the close-out.
```

## 5. Phase close-out (resume material)
- [ ] Land the work via **PR** (agent never merges its own).
- [ ] Write/refresh a memory `SKY-019-progress` (what shipped, what's next, gotchas) + a MEMORY.md pointer.
- [ ] Bump this file's frontmatter (`current_phase`, `status`, `updated`) and flip the phase box to `[x]`.
- [ ] `bin/plan list` to refresh the roadmap index.
- [ ] Paste the **Continue prompt** below to resume in a fresh session:
```
Continue planning/projects/SKY-019-relocate-the-arcane-controller-off-the-dmz-to-a-dedicated-management-docker-vm-managing-docker-hosts-remotely.md at Phase <N+1>.
Prereqs carried from the last phase: <…>. Resume context from memory [[SKY-019-progress]].
Follow AGENTS.md as above.
```

## 6. Status log
- 2026-09-01 — created (draft). Split out of SKY-018 P1's arcane-manager triage: the fix is a
  relocation, not a compose tidy-up. Placement (dedicated Management VLAN-50 docker VM, cloned from
  the 9000 template), remote-over-unprivileged-SSH management, and fresh secrets all settled with Ali.
  Interim in-DMZ capture landed under `compose/arcane-manager/` (bootstrap component, not self-synced).
