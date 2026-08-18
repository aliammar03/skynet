---
id: SKY-007
title: NixOS host definition, piloted on the ops VM
status: draft
horizon: long
created: 2026-08-17
updated: 2026-08-17
phases: 2
current_phase: 0
tier_touched: [T2+, T3]   # rebuilding a host = root (T2+); the host is the agent's own box and this
                          # changes the host-management model ⇒ MUST PR docs/system-design.md.
related:
  - docs/system-design.md
  - docs/decisions/0003-ambiguity-layering-and-format-follows-enforcement.md  # what to schematize vs. keep prose
  - docs/design/access-and-trust.md
  - docs/design/disaster-recovery.md
  - docs/design/secrets.md
  - planning/scratchpad/2026-08-17-declarative-future-and-agent-cognition.md
  - planning/scratchpad/research/2026-08-17-nixos-fleet.md
  - "[[SKY-008-progress]]"
  - "[[SKY-007-progress]]"
---

# SKY-007 · NixOS host definition, piloted on the ops VM

> Push the declarative boundary *below* Docker: define a whole host as a reproducible Nix flake.
> Piloted on the ops VM only — lowest blast radius, highest payoff — to prove the agent can actually
> operate Nix before betting any workload host on it.

## 1. Problem / motivation
The declarative boundary stops at the Docker layer. Host config is imperative and snowflaky; the
T2+ **root grant used to harden a host leaves mutable state nothing reconciles**; and DR of a host
means rebuilding by hand. NixOS would make a host a **git diff** — reproducible, atomic-rollback,
drift-impossible inside the declared surface — and collapse root-hardening into a *reviewed nix
module* instead of an imperative escape hatch. The catch: **Nix is hard, and the real risk is the
LLM operator, not NixOS.** So we de-risk on the one host we can afford to rebuild. (Thesis §5;
research brief `research/2026-08-17-nixos-fleet.md`.)

## 2. Brainstorm — options considered

**Where to pilot**
- **Option A — a workload host.** Real payoff, but real tenant-service blast radius while we're still
  learning the toolchain.
- **Option B — the ops VM itself** (`vm-skynet-ops`). The agent's own box, no tenant services; a
  botched rebuild hurts only the agent, on a host we can afford to rebuild. Also directly upgrades
  DR *of the agent*.
- **Decision:** **Option B (CHOSEN).** Any workload-host migration is gated on evidence from this pilot.

**How to convert** *(research-informed)*
- **`nixos-anywhere` (CHOSEN)** — kexecs into a RAM-only installer, disko-reprovisions over SSH; the
  original OS isn't running when it works. Destructive by design → **clone-and-convert a twin, never
  gamble the live VM.**
- **`nixos-infect`** — "surgery on a running patient." Rejected; too risky.

**Day-2 deploy tool** *(research-informed)*
- **`deploy-rs` (CHOSEN)** — its **magic rollback** (auto-reverts if it can't reconnect in ~30s) is
  the decisive feature for an LLM: a config that kills SSH *self-heals* instead of bricking the host.
- **Colmena** — simpler, weaker auto-rollback. **NixOps** — legacy, skip.

**Secrets** *(research-informed)*
- **`sops-nix` (CHOSEN)** — rides the existing sops+age (same `.sops.yaml`, host SSH key as age
  identity), decrypts to tmpfs so nothing hits the world-readable `/nix/store`. **agenix** would fork
  our secrets format — rejected. One secrets format lab-wide. See [secrets](../../docs/design/secrets.md).

**Services on NixOS** *(research-informed)*
- **Keep compose + Arcane unchanged** via `virtualisation.docker.enable`. NixOS owns the host, Arcane
  owns the services. Moving services to `oci-containers` would break the GitOps loop — rejected.

**Impermanence ("erase your darlings")**
- Real anti-persistence security benefit, but state-enumeration-heavy. **Decision: defer** to a later
  hardening phase, not the first pilot.

## 3. The plan
- **Scope / non-goals:** stand up a NixOS flake for an **ops-VM twin**, validate, then cutover.
  **Non-goals:** any workload host, impermanence, moving services off Arcane — all later/out.
- **Hosts & tiers touched:** ops VM. Rebuilding it is **root-level (T2+)** on the agent's own box and
  changes the host-management model ⇒ **MUST PR `docs/system-design.md`** and lands a step on the
  autonomy ratchet.
- **Rollback posture:** build the twin **in parallel**; keep the current ops VM until the twin is
  proven; **PBS snapshot before cutover**. deploy-rs magic-rollback covers day-2 mistakes.
- **Grants / human actions:** ⚠ hard checkpoints throughout — this is the agent reprovisioning its
  own host; Ali is hands-on for the cutover.

### Phase 0 — research gate  `[ ]` not started
Blocked until the research brief is read **and** basic agent Nix fluency is demonstrated (write +
`nixos-rebuild build` a trivial module without stalling on cryptic errors). Exit: go/no-go recorded.

### Phase 1 — parallel NixOS twin of the ops VM  (~1–2h+)   `[ ]` not started
New VM; flake defining the ops toolchain (docker, `bin/ops`, SSH CA trust, timers) with sops-nix;
`nixos-anywhere` provision; deploy-rs for day-2; validate the nightly + Arcane paths run on it.
**⚠ hard checkpoints:** snapshot, parallel-run, human-approved cutover. Exit: twin passes a full
nightly + a deploy-verify; cutover plan approved. **Also PRs `docs/system-design.md`.**

<!-- Later phases (post-pilot): workload-host migration; impermanence hardening — each its own directive. -->

## 4. ▶ Execute prompt
```
Read planning/projects/SKY-007-nixos-host-definition-piloted-on-the-ops-vm.md and execute Phase <N>.
Follow AGENTS.md: plan loudly then run quietly, never merge your own PRs, request the
narrowest host / shortest grant the phase needs, and checkpoint at the listed human/grant
steps. When the phase's exit criteria are met, do the "Phase close-out" at the bottom.
```

## 5. Phase close-out (resume material)
- [ ] Land the work via **PR** (agent never merges its own) — including the `docs/system-design.md` change.
- [ ] Write/refresh a memory `SKY-007-progress` (what shipped, what's next, gotchas) + a MEMORY.md pointer.
- [ ] Bump this file's frontmatter (`current_phase`, `status`, `updated`) and flip the phase box to `[x]`.
- [ ] `bin/plan list` to refresh the roadmap index.
- [ ] Paste the **Continue prompt** below to resume in a fresh session:
```
Continue planning/projects/SKY-007-nixos-host-definition-piloted-on-the-ops-vm.md at Phase <N+1>.
Prereqs carried from the last phase: <…>. Resume context from memory [[SKY-007-progress]].
Follow AGENTS.md as above.
```

## 6. Status log
- 2026-08-17 — created (draft) from the declarative-future brainstorm §5. Pilot on the ops VM only;
  toolchain picks (nixos-anywhere + deploy-rs + sops-nix, keep Arcane) taken from the research brief
  `planning/scratchpad/research/2026-08-17-nixos-fleet.md`. Pairs with SKY-008 (Tofu makes the box, Nix defines it).
