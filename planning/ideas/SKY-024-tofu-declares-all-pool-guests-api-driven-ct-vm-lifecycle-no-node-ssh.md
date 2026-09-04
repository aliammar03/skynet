---
id: SKY-024
title: tofu declares all pool guests — API-driven CT/VM lifecycle, no node SSH
status: draft
horizon: short
created: 2026-09-04
updated: 2026-09-04
phases: 3
current_phase: 0
tier_touched: [T2, T3]   # T3: a pveum grant widening svc-tofu on core → the plan MUST PR
                         # docs/system-design.md (the constitution).
related:
  - docs/system-design.md
  - planning/projects/SKY-008-opentofu-provisioning-layer-vm-and-ct-lifecycle-plus-dns.md
  - planning/archive/SKY-021-nixos-in-lxc-prove-the-container-path-and-set-the-new-ct-default.md
  - "[[SKY-008-progress]]"
  - "[[SKY-021-progress]]"
  - "[[SKY-024-progress]]"
---

# SKY-024 · tofu declares all pool guests — API-driven CT/VM lifecycle, no node SSH

> One-line pitch: make "deploy a new LXC" a **`tofu apply` + `deploy`**, not a hand-rolled Proxmox
> API curl — by letting OpenTofu declare the guest *envelope* (create-from-template, network, MAC)
> via the **API alone**, keeping the no-standing-node-SSH invariant intact.

## 1. Problem / motivation
SKY-021 proved the NixOS-LXC path, but the **create** step is still manual: this session I hand-rolled
a `POST /nodes/<node>/lxc` curl (create + MAC pin), repeated it through a stale-ARP incident, and only
*then* injected the Option C key and ran deploy-rs. The CT envelope is declared nowhere — no reviewable
`plan` diff, no drift detection, and the MAC isn't pinned in code (which is exactly what let the ARP
gremlin bite). SKY-008 stood up the tofu layer but has only ever **imported** one CT (240, zero-drift);
it has never **created** a guest. So provisioning is the one part of the loop that isn't declarative.

Goal: tofu owns the guest envelope for pool guests, so a new one = **a resource block + a flake host +
a PR**, with `tofu plan` as the reviewable diff and the MAC pinned declaratively.

## 2. Brainstorm — decisions

- **Transport — API-only, NO node SSH (CHOSEN).** bpg needs its `ssh{}` block *only* for snippet /
  cloud-init uploads, **local-file** disk imports (`source_file.path`), and container `idmap` — the bpg
  docs state SSH is **not** required for "creating, modifying, or deleting VMs and Containers" or
  "managing storage, networks, pools." Our NixOS pool guests use **none** of the SSH-only features:
  they boot from an already-uploaded vztmpl, get their network via the API, and nix owns the inside —
  the exact path SKY-021 proved works with the token alone. Enabling bpg SSH would hand tofu a
  **standing node-root** channel — a Judgement-Day invariant violation (§6) and the very thing the
  SKY-008 provider comment deliberately refuses — for **zero** functional gain on our shape. So: no SSH.
- **Grant — `svc-tofu` gains API-level *create* on core (CHOSEN).** Today `svc-tofu` is pool-scoped and
  can't mint a new VMID (the P1b wall). Grant it the same **API** create set SKY-021 gave the operate
  token on core — `VM.Allocate` (new id), `Datastore.AllocateSpace` (rootfs), `SDN.Use` (NIC),
  `Datastore.AllocateTemplate` (if tofu ever uploads templates) — with the **bright lines held**: NO
  `Permissions.Modify`, NO `Sys.Console/Modify/PowerMgmt` (node root), NO SSH. A T3 `pveum` (⚠ Ali) +
  a constitution PR (it widens `svc-tofu` on core; the ACL-audit gate from SKY-021 extends to cover it).
- **Ownership split — tofu the envelope, nix the inside (CHOSEN).** `tofu apply` makes the CT exist
  (API) → `ct-age-identity.sh inject` the Option C key → `deploy .#lxc-<name>` activates the config.
  tofu has no SSH and does not touch the guest OS — the SKY-007/008 "tofu makes the box, nix defines
  it" pairing, kept exactly.
- **Template handling (CHOSEN).** The NixOS base vztmpl stays **built by nix + uploaded via the API**
  upload endpoint (as SKY-021 does), referenced by tofu as `template_file_id`. bpg's `download_file`
  (URL-based, API) is the alternative but we host no URL — deferred.
- **Fleet scope (CHOSEN).** Pool guests only. The T3-excluded set (PBS 240, Caddy 635, technitium-
  network 837, OPNsense 5001, Unraid 2020) is **never fresh-created** by tofu — 240 stays import-only,
  the rest stay hand-managed. Start with pool CTs (adguard-core the reference), then generalize to VMs.

## 3. The plan
- **Scope / non-goals.** In: API-only tofu *create* of pool CTs (then VMs), MAC pinned in code, the
  `svc-tofu` create grant + its constitution note, and a `new pool guest = block + flake host + PR`
  runbook. Out: node SSH for tofu (explicitly rejected above); migrating the T3-excluded guests;
  the nix/deploy-rs half (unchanged — SKY-007/021 own it).
- **Hosts & tiers touched.** T3: the `svc-tofu` `pveum` grant on core (⚠ Ali) → **PR
  `docs/system-design.md`**. T2: tofu-create/destroy pool guests via API; deploy-rs over SSH (existing).
- **Rollback posture.** Each phase proves on a **throwaway** CT (tofu `destroy` = rollback). The
  adguard-core migration is an **import** (read-only, zero live mutation — the SKY-008 240 recipe), so
  it can't disrupt the running guest. `git revert` backs out any resource block.
- **Grants / human actions.** ⚠ Ali runs the `svc-tofu` `pveum` grant (T3, his hands) once, in Phase 1.

### Phase 1 — grant + prove one fresh tofu-created CT  (~1–2h)   `[ ]` not started
Steps:
1. **⚠ Ali** grants `svc-tofu` the API create set on core (VM.Allocate + Datastore.AllocateSpace +
   SDN.Use, bright lines held, no SSH). Verify via the token's own `/access/permissions`.
2. Author a `proxmox_virtual_environment_container` for a **throwaway** CT from the nixos vztmpl
   (`template_file_id` real; `network_interface.mac_address` pinned; `initialization` ip/hostname;
   unpriv + nesting). `tofu plan` → apply → CT boots.
3. `ct-age-identity.sh inject` + `deploy .#<throwaway>` → verify it activates. Nail down the
   `ignore_changes` set bpg needs for a live NixOS CT (reuse/trim the 240 recipe).
4. `tofu destroy` the throwaway. **PR `docs/system-design.md`** recording the `svc-tofu` core-create
   grant + extend the ACL-audit gate (invariants.json) to assert svc-tofu's scope.

Exit criteria: a CT created **entirely by `tofu apply`** (API-only, no SSH), specialized by deploy-rs,
with a clean re-`plan`; the grant is in the constitution and machine-audited.
Grants / human actions: ⚠ Ali's `pveum` (T3).

### Phase 2 — migrate adguard-core into tofu as the reference  (~1–2h)   `[ ]` not started
Steps:
1. Author `tofu/lxc-adguard-core.tf` and **import** the live CT 731 (zero-drift, the 240 recipe) —
   MAC pinned in code, so a future reprovision can't churn ARP.
2. Prove `tofu plan` is clean against the running guest (no diff, no replacement).
3. Write the runbook: **new pool CT = a container block + a `hosts/lxc-<name>/` flake host + PR →
   `tofu apply` + `deploy`** (fold into `runbooks/` + the SKY-021 close-out).

Exit criteria: adguard-core's envelope is tofu-declared with a clean plan; the end-to-end runbook is
documented and reproducible.

### Phase 3 — generalize (module + VMs)  (~1–2h)   `[ ]` not started
Steps:
1. Extract a small `for_each` module so a new pool guest is a **data entry** (name/vlan/octet/resources)
   — VMID derived by the naming law, MAC pinned, wired to its flake host.
2. Bring the existing pool VM(s) (docker-dmz) under the same declaration where it adds value.
3. Note the remaining migration candidates (technitium-core, omada, authentik) as one-block adds.

Exit criteria: a new pool guest is a single data entry + flake host + PR; the pattern covers CTs and VMs.

## 4. ▶ Execute prompt
> Paste into a fresh Skynet session to run this directive. Swap `<N>` for the phase to run.
```
Read planning/projects/SKY-024-tofu-declares-all-pool-guests-api-driven-ct-vm-lifecycle-no-node-ssh.md and execute Phase <N>.
Follow AGENTS.md: plan loudly then run quietly, never merge your own PRs, request the
narrowest host / shortest grant the phase needs, and checkpoint at the listed human/grant
steps. When the phase's exit criteria are met, do the "Phase close-out" at the bottom.
```

## 5. Phase close-out (resume material)
Run this every time a phase finishes successfully — it's what makes the next session cold-startable:
- [ ] Land the work via **PR** (agent never merges its own).
- [ ] Write/refresh a memory `SKY-024-progress` (what shipped, what's next, gotchas) + a MEMORY.md pointer.
- [ ] Bump this file's frontmatter (`current_phase`, `status`, `updated`) and flip the phase box to `[x]`.
- [ ] `bin/plan list` to refresh the roadmap index.
- [ ] Paste the **Continue prompt** below to resume in a fresh session:
```
Continue planning/projects/SKY-024-tofu-declares-all-pool-guests-api-driven-ct-vm-lifecycle-no-node-ssh.md at Phase <N+1>.
Prereqs carried from the last phase: <…>. Resume context from memory [[SKY-024-progress]].
Follow AGENTS.md as above.
```

## 6. Status log
*(One dated line per milestone — cite PR numbers; convert relative dates to absolute. Newest last.)*
- 2026-09-04 — created (draft) out of the SKY-021 close-out. Web research (bpg/proxmox docs) settled the
  key question: **the API token alone creates/modifies/deletes CTs & VMs and manages storage/network/
  pools; SSH is required only for snippet uploads, local-file disk imports, and container idmap** — none
  of which our NixOS pool guests use. So "tofu declares all" needs an API create grant for `svc-tofu`,
  **not** node SSH. Sources: bpg docs (docs/index.md — SSH requirements), corroborated by the
  community LXC modules.
