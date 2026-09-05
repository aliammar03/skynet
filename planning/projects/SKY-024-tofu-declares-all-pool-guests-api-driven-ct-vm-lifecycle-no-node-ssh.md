---
id: SKY-024
title: tofu declares managed core guests — API-driven CT/VM lifecycle, no node SSH
status: in-progress
horizon: short
created: 2026-09-04
updated: 2026-09-05
phases: 6
current_phase: 4
tier_touched: [T2, T3]   # T3: consolidating the agent's Proxmox identity (tofu → operate token) +
                         # a network-node pveum → the plan MUST PR docs/system-design.md.
related:
  - docs/system-design.md
  - planning/projects/SKY-008-opentofu-provisioning-layer-vm-and-ct-lifecycle-plus-dns.md
  - planning/archive/SKY-021-nixos-in-lxc-prove-the-container-path-and-set-the-new-ct-default.md
  - "[[SKY-008-progress]]"
  - "[[SKY-021-progress]]"
  - "[[SKY-024-progress]]"
---

# SKY-024 · tofu declares managed core guests — API-driven CT/VM lifecycle, no node SSH

> One-line pitch: make "deploy a new LXC" a **reviewed saved-plan wrapper + `deploy`**, not a hand-rolled Proxmox
> API curl — by letting OpenTofu declare the guest *envelope* (create-from-template, network, MAC)
> via the **API alone**, keeping the no-standing-node-SSH invariant intact.

## 1. Problem / motivation
SKY-021 proved the NixOS-LXC path, but the **create** step is still manual: this session I hand-rolled
a `POST /nodes/<node>/lxc` curl (create + MAC pin), repeated it through a stale-ARP incident, and only
*then* injected the Option C key and ran deploy-rs. The CT envelope is declared nowhere — no reviewable
`plan` diff, no drift detection, and the MAC isn't pinned in code (which is exactly what let the ARP
gremlin bite). SKY-008 stood up the tofu layer but has only ever **imported** one CT (240, zero-drift);
it has never **created** a guest. So provisioning is the one part of the loop that isn't declarative.

Goal: tofu owns the guest envelope for managed core guests, so a new one = **a resource block + a
flake host + a PR**, with `tofu plan` as the reviewable diff and the MAC pinned declaratively.

## 2. Brainstorm — decisions

- **Transport — API-only, NO node SSH (CHOSEN).** bpg needs its `ssh{}` block *only* for snippet /
  cloud-init uploads, **local-file** disk imports (`source_file.path`), and container `idmap` — the bpg
  docs state SSH is **not** required for "creating, modifying, or deleting VMs and Containers" or
  "managing storage, networks, pools." Our NixOS managed guests use **none** of the SSH-only features:
  they boot from an already-uploaded vztmpl, get their network via the API, and nix owns the inside —
  the exact path SKY-021 proved works with the token alone. Enabling bpg SSH would hand tofu a
  **standing node-root** channel — a Judgement-Day invariant violation (§6) and the very thing the
  SKY-008 provider comment deliberately refuses — for **zero** functional gain on our shape. So: no SSH.
- **One operator token — retire the `svc-tofu` split (CHOSEN).** The SKY-008 split (`svc-tofu`
  declarative / `svc-ops!operate` imperative, plus a config-only `/vms` role) is the real friction:
  every capability is granted twice, and neither identity can do the whole job (svc-tofu can't mint a
  VMID; operate isn't what tofu points at). Collapse it: **tofu points at the `svc-ops@pve!operate`
  token**, which already holds the full VM/Datastore/Pool/SDN set at `/` on core (SKY-021 broaden). So
  ops does imperative *and* declarative work with one token — create/destroy/reconfigure/power/migrate/
  snapshot/clone any guest, manage storage/networks/pools — **no new `pveum` on core**. `svc-tofu`
  retires. Rejected: minting `svc-tofu` a parallel create grant (keeps two tokens, the thing we're
  killing). The split was the mistake, not the perms.
- **The three bright lines stay off — even the big token (LOCKED).** Not scoping-for-scoping; these are
  the §6 Judgement-Day laws that make every *other* capability safe to keep widening: **NO
  `Permissions.Modify`** (the token rewriting its own ACLs → all gates become theater), **NO
  `Sys.Modify/PowerMgmt/Console`** (Proxmox *node* root — operating guests ≠ rooting the host), **NO
  node SSH** (node root by another name; the API does everything our shape needs — see transport
  decision). These are human-merged-forever; the agent never proposes granting them. The operate token
  already holds this posture (bright lines absent), so consolidation adds nothing here.
- **Ownership split — tofu the envelope, nix the inside (CHOSEN).** The explicitly approved
  saved-plan wrapper makes the CT exist (API) → `ct-age-identity.sh inject` the Option C key →
  `deploy .#lxc-<name>` activates the config.
  tofu has no SSH and does not touch the guest OS — the SKY-007/008 "tofu makes the box, nix defines
  it" pairing, kept exactly.
- **Template handling (CHOSEN).** The NixOS base vztmpl stays **built by nix + uploaded via the API**
  upload endpoint (as SKY-021 does), referenced by tofu as `template_file_id`. bpg's `download_file`
  (URL-based, API) is the alternative but we host no URL — deferred.
- **Fleet scope (CHOSEN).** Core-managed guests only. Service CTs 731 (adguard), 751 (technitium),
  and 10030 (athena) are currently unpooled but their envelopes are managed by the core-node ACL.
  PBS 240 is an existing `ops-managed` import, not an excluded guest. The permanently excluded set
  (CT 635, CT 837, OPNsense VM 5001, and Unraid VM 2020) is not fresh-created by tofu and remains
  outside automated envelope paths.

## 3. The plan
- **Scope / non-goals.** In: API-only tofu *create* of core-managed guests, MAC pinned in code, the
  `svc-tofu` create grant + its constitution note, and a `new managed guest = block + flake host + PR`
  runbook. Out: node SSH for tofu (explicitly rejected above); migrating the T3-excluded guests;
  the nix/deploy-rs half (unchanged — SKY-007/021 own it).
- **Hosts & tiers touched.** T2/T3: consolidating the agent's Proxmox identity (tofu → operate token,
  retire svc-tofu) is a trust-model change → **PR `docs/system-design.md`**. No new `pveum` on core
  (operate already holds the create set). T2: saved-plan wrapper creates/updates managed guests;
  the wrapper refuses destroy/replace plans.
- **Rollback posture.** A new create has no automatic rollback and a partial failure needs operator
  recovery. Existing-guest update snapshots are retained for recovery, but post-apply verification
  failures do not trigger an automatic destructive rollback. The adguard-core migration is an
  **import** (read-only, zero live mutation — the SKY-008 240 recipe), so it can't disrupt the running
  guest. `git revert` backs out any resource block or the token repoint; cleanup remains a separate
  human hard checkpoint.
- **Grants / human actions.** No `pveum` needed on core. ⚠ Ali confirms the identity consolidation
  (which token tofu runs as) via the constitution PR; optionally deactivates the retired svc-tofu token.

### Phase 1 — consolidate the token + prove one fresh tofu-created CT  (~1–2h)   `[x]` DONE (2026-09-04)
Steps:
1. **Repoint tofu at the operate token** on core (`tofu-env.sh` / the provider var sources
   `PVE_TOKEN_OPERATE` from `secrets/proxmox-core.env` instead of the svc-tofu secret). `tofu plan`
   against the existing state must be clean (same effective perms or broader → no auth regressions).
2. Author a `proxmox_virtual_environment_container` for a **throwaway** CT from the nixos vztmpl
   (`template_file_id` real; `network_interface.mac_address` pinned; `initialization` ip/hostname;
   unpriv + nesting). `tofu plan` → apply → CT boots. Resolve live whether bpg drives the NixOS
   network via `initialization.ip_config` or still needs `ostype`.
3. `ct-age-identity.sh inject` + `deploy .#<throwaway>` → verify it activates. Nail down the
   `ignore_changes` set bpg needs for a live NixOS CT (reuse/trim the 240 recipe).
4. Remove the throwaway only through a separately approved human hard checkpoint; the current
   saved-plan wrapper refuses destroy/replace. **PR `docs/system-design.md`**: record the **one-operator-token**
   consolidation (tofu = operate; svc-tofu retired; the three bright lines stay off, human-merged-
   forever) + extend the ACL-audit gate to assert the operate token's tofu use holds the bright lines.

Exit criteria: tofu runs as the one operator token; a CT created entirely by the reviewed
**saved-plan wrapper** (API-only, no SSH), specialized by deploy-rs, with a clean re-`plan`; the
consolidation is in the constitution and
machine-audited.
Grants / human actions: ⚠ Ali confirms the consolidation via the constitution PR (no pveum).

### Phase 2 — migrate adguard-core into tofu as the reference  (~1–2h)   `[x]` DONE (2026-09-04)
Steps:
1. Author `tofu/lxc-adguard-core.tf` and **import** the live CT 731 (zero-drift, the 240 recipe) —
   MAC pinned in code, so a future reprovision can't churn ARP.
2. Prove `tofu plan` is clean against the running guest (no diff, no replacement).
3. Write the runbook: **new core-managed CT = a container block + a `hosts/lxc-<name>/` flake host
   + PR → reviewed saved plan + `TOFU_APPLY_SCOPE=proxmox-core scripts/tofu-apply.sh` + `deploy`**
   (fold into `runbooks/` + the SKY-021 close-out). The wrapper refuses destroy/replace plans.

Exit criteria: adguard-core's envelope is tofu-declared with a clean plan; the end-to-end runbook is
documented and reproducible.

### Phase 3 — generalize (module + VMs)  (~1–2h)   `[x]` DONE (2026-09-04)
Steps:
1. Extract a small `for_each` module so a new managed guest is a **data entry** (name/vlan/octet/resources)
   — VMID derived by the naming law, MAC pinned, wired to its flake host.
2. Bring the existing pool VM(s) (docker-dmz) under the same declaration where it adds value.
3. Note the remaining migration candidates (technitium-core, omada, authentik) as one-block adds.

Exit criteria: a new managed guest is a single data entry + flake host + PR; the pattern covers CTs and VMs.

---
*Phases 4–6 migrate the remaining pool services onto the P1–P3 machinery — each the SKY-021
adguard-core pattern: author `hosts/lxc-<name>/` (service config in Nix + sops-nix Option C), add a
`pool_cts` entry (MAC pinned), snapshot the old CT, provision the NixOS replacement, `deploy`, verify,
keep the old CT **stopped** as rollback, PR + close-out. They flip the new-CT default from theory to
fleet. Ordered by fit-certainty and stakes.*

### Phase 4 — technitium-core (751) → NixOS core-managed CT  (~1–2h)   `[ ]` not started
The DNS clients actually use (unlike the adguard leftover) — so a **real** cutover. Core node, VLAN 70
`.51`, VMID 751. Steps:
1. **First:** confirm the resolver redundancy — sequence the cutover so clients keep DNS through the
   gap (technitium-network `.50` as fallback, or a short low-traffic window). Snapshot old 751.
2. Author `hosts/lxc-technitium-core/`. **Open Q — the config surface:** Technitium keeps state in a
   DB/config dir, not a single declarative file like AdGuard's YAML. Check nixpkgs for a
   `technitium-dns-server` package/module; if config isn't cleanly declarative, decide the model
   (persist the config dir + seed zones via the Technitium API/tofu, vs. a full declarative port).
   Zones stay T2 (the Technitium zones token); *server settings* are T3.
3. Option C secret (admin), `native_core_cts` entry (pinned MAC = its existing MAC). Author and
   merge the source, save/show the plan, then run `TOFU_APPLY_SCOPE=proxmox-core
   scripts/tofu-apply.sh <saved-plan>` after explicit approval. Provision → inject → deploy →
   verify resolution + zones from a client. The wrapper refuses destroy/replace plans.
4. Cut over; keep old 751 **stopped** as rollback. ⚠ real DNS — hard checkpoint. PR + close-out.

Exit criteria: technitium-core runs NixOS, clients resolve through it, zones intact; old CT stopped.

### Phase 5 — omada (525) → evaluate fit, then migrate  (~1–2h)   `[ ]` not started
The Omada controller (VLAN 50 `.25`, VMID 525) manages the switch/AP estate (losing it drops
*management*, not the network). Steps:
1. **Fit check first (⚠ decision):** Omada is a Java app often shipped as Docker — and managed CTs are
   **unprivileged, no Docker-in-CT**. Check nixpkgs for a native `tplink-omada-controller` service. If
   it only runs under Docker → checkpoint to Ali: keep it Debian, run it on the DMZ Docker host, or a
   privileged-CT exception. Don't force it into the NixOS-LXC pattern.
2. If a native service fits: author the host + Option C + `native_core_cts` entry; use the merged,
   explicitly approved saved-plan wrapper for provisioning (never a bare apply or destroy); deploy;
   re-adopt/verify the estate; keep old stopped. PR + close-out.

Exit criteria: a recorded verdict — omada on NixOS (if it fits) or a logged decision on its alternative.

### Phase 6 — authentik (837) → gated on leaving T3 + a fit check  (~1–2h)   `[ ]` not started
**Two gates before any work.** authentik (network node, VMID 837) is currently a **T3-excluded** guest
(server admin is T3; on the pool-scoped network node). Steps:
1. **⚠ Constitution decision:** does authentik's *envelope* graduate out of `excluded_guests` so the
   agent may own its lifecycle? (App-admin — flows/policies/keys — can stay T3 even if the box is a
   NixOS CT.) A `docs/system-design.md` PR; if **no**, the phase closes as won't-do and authentik stays
   hand-managed.
2. **⚠ Fit check:** authentik is a **multi-service** app (server + worker + postgres + redis), normally
   Docker-compose — which does **not** fit an unprivileged single-CT NixOS host. If it doesn't fit,
   record that it stays on the Docker host / Debian, not a managed CT.
3. Only if both gates pass: author the host + secrets + `native_core_cts` entry (⚠ network-node new
   VMID needs a human) + cutover through the explicitly approved saved-plan wrapper. The wrapper
   refuses destroy/replace plans.

Exit criteria: a recorded decision — authentik migrated, or a logged won't-do with the reason (T3 or fit).

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
- 2026-09-04 — **Phase 1 DONE** (PR pending, branch `feat/sky-024-p1`). Ali's call: "fuck splits, one
  big boy token." **Consolidated to one operator token per node** — tofu-env.sh now sources
  `svc-ops!operate` for BOTH nodes (svc-tofu retired). Core needed no grant (already `/`-broadened);
  **network** needed a pveum (⚠ Ali ran it) giving operate-network `Datastore.AllocateSpace` + `SDN.Use`
  at `/storage/local-lvm` + `/sdn/zones/localnetwork` — but deliberately **not** `/vms`-root (OPNsense,
  the leash-enforcing firewall, lives on network → envelope-destroy over it stays off, machine-checked
  by `vms_root_nodes=[core]`). `tofu plan` clean on both after repoint (no auth regression). **Proved the
  full loop:** authored a throwaway `proxmox_virtual_environment_container` (CT 9042 @ 10.10.90.42,
  VLAN 90, MAC pinned) → `tofu apply` created it **API-only** (bpg accepts `operating_system.type =
  "nixos"`; `initialization.ip_config` set the NixOS network — no manual step) → booted + SSH-reachable
  → `deploy .#lxc-proof --hostname` specialized it (gen 1→2) → `tofu destroy` removed it. So tofu owns
  the envelope, deploy-rs owns the inside, one token, no node SSH. Constitution + invariants.json updated;
  check-invariants green. Throwaway .tf removed (adguard-core is the Phase-2 committed reference).
  Follow-up: Ali can deactivate the now-unused svc-tofu tokens + we can drop the tofu-proxmox*.sops secrets.
- 2026-09-04 — **Phase 3 DONE** (branch `feat/sky-024-p3`, PR #171). The core objective is met; the
  fleet migrations that ride this machinery are now added as **Phases 4–6** (technitium-core, omada,
  authentik) — SKY-024 stays open as their umbrella rather than archiving. Built the `for_each`
  module `tofu/pool-cts.tf`: a `local.pool_cts` map (`{vmid,node,vlan,octet,mac,cores,memory,swap,disk,
  tags}` per guest) → one `proxmox_virtual_environment_container "pool_ct"` for_each. **A new pool CT is
  now one data entry** (+ a flake host + a PR). `mac` is a required field → pinning is structural, the
  ARP footgun can't recur. Migrated adguard-core into it via a `moved {}` block (state rename, **0 infra
  change** — verified live: DNS rewrite + ad-block still answer). Removed the standalone
  `lxc-adguard-core.tf`. Migration candidates (technitium-core/omada/authentik) are commented one-block
  adds in the map. **VMs deferred:** a for_each VM module for the single pool VM (docker-dmz) adds no
  value — VMs stay per-file until there are several (the directive's "where it adds value"). Runbook
  `provision-lxc.md` updated to the data-entry flow.
- 2026-09-04 — added **Phases 4–6** (Ali): the pool-service migrations onto the P1–P3 machinery —
  technitium-core (751), omada (525), authentik (837). Each is now a `pool_cts` entry + a flake host +
  a cutover, following the SKY-021 adguard-core pattern. Not started; SKY-024 stays open.
- 2026-09-04 — **Phase 2 DONE** (same branch/PR #168, Ali's "go ahead in the same pr"). adguard-core
  (CT 731) is now the tofu reference: `tofu/lxc-adguard-core.tf` **zero-drift imported** (MAC pinned in
  code — `network_interface.mac_address` round-trips, so it's declarative now). Import needed the console
  block declared to read-back (`type="console"`) and **`cpu` added to `ignore_changes`** (bpg's import
  didn't populate cpu for this raw-API-created CT → would drift forever). `tofu plan` = No changes.
  Wrote `runbooks/provision-lxc.md` (new LXC = container block + flake host + PR → apply → inject →
  deploy) + catalogued it. **Next — P3:** a `for_each` module (new guest = one data entry) + pool VMs.
- 2026-09-04 — created (draft) out of the SKY-021 close-out. Web research (bpg/proxmox docs) settled the
  key question: **the API token alone creates/modifies/deletes CTs & VMs and manages storage/network/
  pools; SSH is required only for snippet uploads, local-file disk imports, and container idmap** — none
  of which our NixOS pool guests use. So "tofu declares all" needs an API create grant for `svc-tofu`,
  **not** node SSH. Sources: bpg docs (docs/index.md — SSH requirements), corroborated by the
  community LXC modules.
- 2026-09-05 — truth correction: live inventory shows CT 731, CT 751, and CT 10030 are unpooled
  core guests; PBS CT 240 is the existing `ops-managed` import. Current provisioning text now
  uses the core envelope boundary, separates imported-adguard compatibility ignores from native
  guest declarations, requires `TOFU_APPLY_SCOPE=proxmox-core` with the saved-plan wrapper, and
  forbids automated/OpenTofu targeting of Unraid VM 2020 despite technical envelope reachability.
