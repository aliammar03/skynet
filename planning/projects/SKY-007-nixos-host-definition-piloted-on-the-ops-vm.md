---
id: SKY-007
title: NixOS host definition, piloted on the ops VM
status: in-progress
horizon: long
created: 2026-08-17
updated: 2026-08-21
phases: 5   # Phase 0 (gate) + Phase 1 split into 1a–1d (scoped 2026-08-21)
current_phase: 1
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

### Phase 0 — research gate  `[x]` DONE (2026-08-21) → **GO**
Blocked until the research brief is read **and** basic agent Nix fluency is demonstrated (write +
`nixos-rebuild build` a trivial module without stalling on cryptic errors). Exit: go/no-go recorded.
- Research brief `research/2026-08-17-nixos-fleet.md` read.
- **Fluency demo:** wrote a flake pinned to `nixos-25.05` (module system + option + `pkgs.hello` +
  a declared `systemd.services` unit) and ran `nix build .#…system.build.toplevel` inside an
  **ephemeral `nixos/nix` container** (zero footprint on the ops VM — see note). Clean eval (no
  infinite-recursion / attr-missing), exit 0, closure `nixos-system-sky007-demo-25.05.20260102`.
- **Location correction:** the fluency demo does **not** run on the live ops VM. Do it in a throwaway
  container; the real NixOS conversion happens only on the Phase-1 twin — "never gamble the live VM"
  applies from Phase 0 onward, not just at cutover.
- **Finding (feeds the Phase-1 system-design PR):** the ops VM currently grants the agent
  **passwordless `sudo`** — a standing root path on the agent's own host. SKY-007's thesis (collapse
  root-hardening into reviewed Nix modules) should account for / narrow this.
- **Exit: GO.** Fluency shown without stalling; toolchain picks stand. Proceed to Phase 1.

### Phase 1 — parallel NixOS twin of the ops VM  *(scoped 2026-08-21; split into 1a–1d)*
> **VM 9090 is never touched until the twin is proven.** Build in parallel on a temp IP, validate,
> then a human-approved cutover. Blast radius stays on a throwaway twin the whole way.

**What the twin must reproduce (ground truth from the live 9090):**
guest = VMID 9090 on `server-proxmox-core`, VLAN 90, 4 vCPU / 8 GB / ~100 GB, static `10.10.90.90`
(+`.99`) · docker (Arcane/compose run **unchanged** — Arcane lives on docker-dmz, ops VM only
calls its API) · the four timers now in `scripts/systemd/` (`skynet-nightly`, `skynet-cli-update`,
`skynet-restic-backup@`, `skynet-pbs-gdrive`) · SSH `TrustedUserCAKeys = ca/skynet_ops_ca.pub` so
`bin/grant-root` certs verify · secrets (`/opt/skynet-ops/secrets/*` 0600 + in-git `.env.sops`).

**Design decisions locked at scoping:**
- **Fresh VM, not a clone** as the `nixos-anywhere` target — the flake is the sole source of truth,
  no snowflake carryover. Match 9090's virtio disk/NIC profile.
- **sops-nix via `sops.age.keyFile`** = the existing lab age key (from the survival kit), **not** the
  host-SSH-key age identity — keeps one age key lab-wide (per [secrets](../../docs/design/secrets.md)).
  The age key is the bootstrap secret (chicken-and-egg): placed at provision time, stays in the kit.
- **Agent CLIs (codex/claude) stay npm-global** in `~ali`, not packaged in Nix — "the runtime is a
  replaceable part; the contract is the machine" (system-design §4). Nix owns nodejs/git/gh/sops/age/
  rclone/restic/docker; packaging the npm CLIs is the exact friction the research brief warned off.
- **Sudo becomes a least-privilege module.** Today the ops user holds standing passwordless `sudo`
  (ALL). The flake narrows it (`security.sudo.extraRules`, NOPASSWD, scoped to the commands ops
  actually needs — its own `systemctl skynet-*`, the grant-root cert path). Collapsing standing root
  into a reviewed diff *is* SKY-007's thesis.
- **Retire the stray VMID 999** ("vm-skynet-ops" duplicate, `community-script` tag) at cutover.

#### Phase 1a — flake + `nix build` green in CI   `[ ]` not started  (~1–2h, no infra)
Author the in-repo flake (`hosts/vm-skynet-ops/` or `nix/`): nixpkgs pinned `nixos-25.05`,
qemu-guest + disko + static-IP modules, docker, the four timers as `systemd.services/.timers`, sshd
+ baked CA pubkey, the narrowed-sudo module, sops-nix wired to the lab age key, deploy-rs output.
Add a CI job that runs `nix build .#…system.build.toplevel` (the Phase-0 fluency check, now gated).
**Lands the `docs/system-design.md` PR** (host layer = a flake; sudo-as-module; twin/cutover model +
autonomy-ratchet step; twin joins `ops-managed` → blast-radius count +1). **No infra touched.**
Exit: flake builds green in CI; system-design PR opened.

#### Phase 1b — provision the twin via `nixos-anywhere`   `[ ]` not started  (~1–2h, ⚠ grant)
Create the fresh twin VM (temp IP, e.g. `10.10.90.91`); `nixos-anywhere` kexec + disko installs the
flake over SSH. **⚠ hard checkpoints:** creating the VM shell (confirm the `operate` token's
OpsOperator ACL — scoped to `/pool/ops-managed` — can allocate a new VMID, else Ali creates the
shell); placing the survival-kit **age key** at provision time. Exit: twin boots, reachable on the
temp IP, `nixos-rebuild`/deploy-rs can reach it.

#### Phase 1c — validate on the twin   `[ ]` not started  (~1–2h, twin only)
Prove the ops role runs on the twin: `bin/ops collect` (collectors hit the read APIs), a full
report-only nightly dry-run, git/gh auth + PR-open path, timers fire, docker up, sops-nix secrets
decrypt to tmpfs. Then a **deploy-rs round-trip**: trivial config change deployed, and an
intentional SSH-breaking change **auto-reverts** (magic rollback proven). Exit: nightly green on the
twin + magic-rollback demonstrated.

#### Phase 1d — cutover   `[ ]` not started  (~1h, ⚠ Ali hands-on)
**PBS snapshot 9090 first.** Stop 9090; move `10.10.90.90` (+`.99`) + DNS to the twin; rename twin →
`vm-skynet-ops`; retire VMID 999. Keep 9090 stopped-but-present as instant rollback for a few days,
then archive. Exit: the twin *is* the ops VM, a nightly has run on it in place, rollback window
observed. **Pilot complete → the workload-host go/no-go is now evidence-based.**

<!-- Later phases (post-pilot, each its own directive): workload-host migration; impermanence hardening. -->

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
- 2026-08-21 — promoted ideas → projects. **Phase 0 research gate: GO.** Fluency demo built a full
  NixOS 25.05 system closure from a trivial flake in an ephemeral `nixos/nix` container (exit 0, no
  stalls). Corrected the demo location off the live ops VM. Logged a passwordless-sudo finding for the
  Phase-1 system-design PR. Next: Phase 1 — parallel NixOS twin. See `[[SKY-007-progress]]`.
- 2026-08-21 — **Phase 1 scoped** against the live 9090 (toolchain, timers, CA trust, secrets,
  sizing). Split into **1a–1d** (flake+CI / provision / validate / cutover) — was over the ~1–2h
  budget. Decisions locked: fresh VM (not clone); sops-nix via lab-age keyFile; CLIs stay npm-global;
  sudo narrowed to a least-privilege module; retire stray VMID 999 at cutover. 1a lands the
  `docs/system-design.md` PR and touches no infra. Next: execute Phase 1a.
