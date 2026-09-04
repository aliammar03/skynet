---
id: SKY-021
title: NixOS-in-LXC: prove the container path and set the new-CT default
status: in-progress
horizon: short
created: 2026-09-03
updated: 2026-09-04
phases: 3
current_phase: 0
tier_touched: [T2]     # reprovisions a pool CT (T2 destroy/recreate) + sets a new-CT default
                       # policy → the plan MUST PR docs/system-design.md (the constitution).
related:
  - docs/system-design.md
  - planning/projects/SKY-008-opentofu-provisioning-layer-vm-and-ct-lifecycle-plus-dns.md
  - planning/scratchpad/research/2026-08-17-nixos-fleet.md
  - "[[SKY-007-progress]]"
  - "[[SKY-008-progress]]"
  - "[[SKY-021-progress]]"
---

# SKY-021 · NixOS-in-LXC: prove the container path and set the new-CT default

> One-line pitch: SKY-007 made the ops **VM** a git-reconstructable NixOS flake; this proves the
> **LXC** equivalent on one throwaway then one low-stakes pool CT, and — only on that evidence —
> flips the default for *new* pool-able containers from Debian to NixOS.

## 1. Problem / motivation

The lab's service hosts are hand-built, drift-prone LXCs (`adguard-core` 731, `technitium-core`
751, `adguard-network`, `omada`, `authentik`, plus the T3-excluded `pbs` 240 / `caddy-management`
635 / `technitium-network` 837). Every one violates the Judgement-Day invariant "**the system
rebuilds from git alone**" (§6) — a lost CT is rebuilt by hand, not by a `nixos-rebuild`.

SKY-007 solved this for the ops box, but proved it on a **VM** via `nixos-anywhere` + disko +
systemd-boot + deploy-rs magic-rollback. **None of that provisioning path survives the jump to an
LXC**: a container has no kernel, no bootloader, and no disk to partition (`boot.isContainer =
true`). The LXC path — build a `proxmox-lxc` template → `pct create` → manage day-2 — is entirely
**unexercised in this lab**, so we can't yet make NixOS the default for a new CT without gambling
on an unproven method. Meanwhile every new Debian CT we spin up is fresh migration debt.

**The decisive unknown** (from research below): the community consensus is that in-place
`nixos-rebuild switch` in a Proxmox LXC has been historically flaky (systemd/`busctl` + `nscd`
failures), with the reliable pattern being **rebuild-the-template + recreate the CT** (immutable),
*not* in-place activation. If that still holds on our stack, then **deploy-rs magic-rollback — the
"decisive LLM-safety feature" from the SKY-007 research — may not work in a container**, which
changes the whole operating model. This directive exists to answer that with evidence before
committing the fleet.

## 2. Brainstorm — decisions

- **Pilot target — `adguard-network` (CHOSEN).** A DNS *filter*, not an authoritative resolver;
  losing it briefly is survivable, and it's pool-able (agent can reprovision it). The authoritative
  DNS (`technitium-core`), `omada`, and `authentik` wait for the pilot's evidence. The T3-excluded
  three (240/635/837) are **never in scope** — the agent can't reprovision them, so they stay
  hand-managed Debian regardless.
- **Provisioning — Tofu builds the CT from a NixOS template, deploy-rs (or template-recreate) owns
  day-2 (CHOSEN).** "Tofu makes the box, Nix defines it" — the SKY-007 pairing, extended to CTs.
  SKY-008 already does CT lifecycle + the CT 240 zero-drift import recipe (reused here).
- **Day-2 model — in-place rebuild, mutable (CHOSEN).** Long-lived CT managed by in-place
  `nixos-rebuild switch` / deploy-rs, keeping deploy-rs **magic-rollback** (the SKY-007 LLM-safety
  win). The pilot's job is therefore to **prove in-place rebuild works reliably** on our PVE 9.1 /
  NixOS 26.05 (historically the broken step — see research), *not* to choose a model. The immutable
  template-recreate pattern is the **fallback only if** the pilot can't make in-place reliable; if
  it comes to that, it's a checkpoint back to Ali, not a silent switch.
- **Container mode — unprivileged (CHOSEN).** Unprivileged CT with `nesting=1`; `proxmoxLXC.privileged`
  stays off. (Consequence: no Docker-in-CT — fine, the DMZ Docker host is a VM and stays one.)
- **Distro default for NON-migratable / appliance CTs — Debian (CHOSEN).** Not Alpine: musl +
  busybox + non-Debian appliance scripts add branching factor exactly where an LLM stalls, for a
  size win that's irrelevant in this lab.

## 3. The plan

- **Scope / non-goals.** In: prove the LXC NixOS path end-to-end; convert one low-stakes pool CT;
  set the new-CT default via a `docs/system-design.md` PR. Out: migrating `technitium-core` /
  `omada` / `authentik` (each its own follow-up, gated on this pilot); anything touching the
  T3-excluded CTs; impermanence/tmpfs-root in a container (defer, as SKY-007 deferred it).
- **Hosts & tiers touched.** T2: build/upload a CT template, `pct create`/destroy a **pool** CT,
  deploy-rs over SSH. The **new-CT default is a constitution change → PR `docs/system-design.md`.**
- **Rollback posture.** P1/P2 run on a **throwaway** CT (destroy = rollback). P3 converts
  `adguard-network`: snapshot/PBS-back the old CT and keep it **stopped** as instant rollback
  (the SKY-007 cutover pattern); DNS filtering has a second AdGuard so a brief gap is survivable.
- **Grants / human actions.** Operate token's `VM.Allocate` is pool-scoped and historically
  couldn't mint a *new* VMID (SKY-007 P1b) — if the same bites, **⚠ Ali creates the empty CT shell**;
  the agent does everything else.

### Phase 1 — path proof on a throwaway CT  (~1–2h)   `[ ]` not started
Prove the LXC build+boot+rebuild path once, on a CT we destroy at the end.
Steps:
1. Author a minimal in-repo flake output for a `proxmox-lxc` template — import
   `(modulesPath + "/virtualisation/proxmox-lxc.nix")`, `boot.isContainer = true`, sshd + a login
   key, `proxmoxLXC.manageNetwork`/`privileged` as needed. Build via nixos-generators
   (`--format proxmox-lxc`) or the nixpkgs `proxmoxLXC` attribute — pick whichever the flake wires
   cleanly. Pin **NixOS 26.05** to match the ops box (SKY-007 1b bumped it 25.05→26.05).
2. Upload the `.tar.xz` as a CT template; `pct create` an **unprivileged** CT with **nesting=1**
   and **Console Mode `/dev/console`** (verified-required options). Boot it.
3. **The decisive test:** change the config (add a package), run in-place `nixos-rebuild switch`,
   confirm it *actually applies* — this is the historically-broken step (fpletz's
   `nixos/proxmox-lxc: fix getty start and nixos-rebuild` fix; workaround `boot.isContainer = true`
   + `environment.variables.NIX_REMOTE = lib.mkForce ""`). Record pass/fail verbatim.
4. Destroy the throwaway CT.

Exit criteria: a CT boots NixOS from a flake-built template **and** we have a recorded verdict on
whether in-place `nixos-rebuild switch` reliably applies changes on our stack — the make-or-break
for the chosen in-place model, which Phase 2 then hardens with deploy-rs rollback.
Grants / human actions: ⚠ possibly Ali mints the empty CT shell (pool-scoped `VM.Allocate` limit).

### Phase 2 — deploy-rs round-trip + pick the day-2 model  (~1–2h)   `[ ]` not started
Steps:
1. On a fresh throwaway CT from the P1 template, wire **deploy-rs** and attempt the magic-rollback
   round-trip proven on the VM in SKY-007 1c (trivial deploy confirmed → an SSH-breaking change
   auto-reverts). Confirm whether profile-switch activation + canary rollback work **in a container**
   (no bootloader involved — the open question is whether container systemd cooperates).
2. Wire **sops-nix** decrypt-to-tmpfs against the lab age key (expected to transfer unchanged).
3. **Confirm the chosen model holds:** in-place `nixos-rebuild switch` + deploy-rs magic-rollback
   work reliably in the unprivileged CT. Record the evidence in `[[SKY-021-progress]]`. **Only if**
   in-place proves unreliable after a genuine attempt → **⚠ checkpoint to Ali** with the failure
   evidence and the immutable-fallback tradeoff (Tofu `pct` recreate from a rebuilt template; every
   change is a reprovision, rollback becomes the stopped-CT not deploy-rs) — don't switch silently.
4. Destroy the throwaway CT.

Exit criteria: recorded verdict that in-place rebuild + deploy-rs rollback work in an unprivileged
LXC on 26.05 — or, if not, a logged checkpoint to Ali on the fallback (not an autonomous switch).
Grants / human actions: same possible CT-shell checkpoint as P1.

### Phase 3 — convert `adguard-network` + set the new-CT default  (~1–2h)   `[ ]` not started
Steps:
1. Author the real `hosts/lxc-adguard-network/` flake host: base module + `services.adguardhome`
   (service config now lives in Nix — the new surface vs the ops box where Arcane owned services),
   sops-nix, the chosen day-2 model from P2.
2. Snapshot/PBS-back the existing CT; provision the NixOS replacement via the P2 model; cut DNS
   filtering over; keep the old CT **stopped** as rollback.
3. **PR `docs/system-design.md`**: record the new-CT default = **NixOS for pool-able LXCs**, Debian
   only for T3-excluded/appliance CTs where the agent can't own the lifecycle. Note the remaining
   migration candidates (technitium-core, omada, authentik) as evidence-gated follow-ups.

Exit criteria: `adguard-network` runs NixOS, filtering verified from a client; the new-CT default is
in the constitution; old CT retained stopped for one cycle then reclaimed.
Grants / human actions: ⚠ destructive cutover of a real (pool) CT — hard checkpoint; ⚠ possible
CT-shell mint.

## 4. ▶ Execute prompt
> Paste into a fresh Skynet session to run this directive. Swap `<N>` for the phase to run.
```
Read planning/projects/SKY-021-nixos-in-lxc-prove-the-container-path-and-set-the-new-ct-default.md and execute Phase <N>.
Follow AGENTS.md: plan loudly then run quietly, never merge your own PRs, request the
narrowest host / shortest grant the phase needs, and checkpoint at the listed human/grant
steps. When the phase's exit criteria are met, do the "Phase close-out" at the bottom.
```

## 5. Phase close-out (resume material)
Run this every time a phase finishes successfully — it's what makes the next session cold-startable:
- [ ] Land the work via **PR** (agent never merges its own).
- [ ] Write/refresh a memory `SKY-021-progress` (what shipped, what's next, gotchas) + a MEMORY.md pointer.
- [ ] Bump this file's frontmatter (`current_phase`, `status`, `updated`) and flip the phase box to `[x]`.
- [ ] `bin/plan list` to refresh the roadmap index.
- [ ] Paste the **Continue prompt** below to resume in a fresh session:
```
Continue planning/projects/SKY-021-nixos-in-lxc-prove-the-container-path-and-set-the-new-ct-default.md at Phase <N+1>.
Prereqs carried from the last phase: <…>. Resume context from memory [[SKY-021-progress]].
Follow AGENTS.md as above.
```

## 6. Status log
*(One dated line per milestone — cite PR numbers; convert relative dates to absolute. Newest last.)*
- 2026-09-03 — created (draft) from an "evaluate NixOS-LXC" session. Research (verified against
  the official NixOS wiki + Discourse, 2026): LXC template built via
  `nix run github:nix-community/nixos-generators -- --format proxmox-lxc`; import
  `(modulesPath + "/virtualisation/proxmox-lxc.nix")` with `boot.isContainer = true`; CT needs
  **unprivileged + nesting=1 + Console Mode `/dev/console`**. **Key finding:** in-place
  `nixos-rebuild switch` in a Proxmox LXC has been historically broken (systemd/`busctl` + `nscd`);
  fixed upstream by fpletz's `nixos/proxmox-lxc: fix getty start and nixos-rebuild` + the
  `boot.isContainer`/`NIX_REMOTE=""` workaround, but community consensus still leans **immutable
  template-recreate** over in-place rebuild — which puts deploy-rs magic-rollback (the SKY-007
  LLM-safety win) in question for containers. Upstream's tested baseline is NixOS 25.11 / PVE 9.1;
  **our pilot pins NixOS 26.05** to match the ops box, so the pilot also proves the path on 26.05
  before flipping the fleet. Pairs with SKY-008 ("Tofu makes the box, Nix defines it").
