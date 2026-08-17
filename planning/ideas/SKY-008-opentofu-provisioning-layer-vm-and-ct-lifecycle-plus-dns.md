---
id: SKY-008
title: OpenTofu provisioning layer: VM and CT lifecycle plus DNS
status: draft
horizon: long
created: 2026-08-17
updated: 2026-08-17
phases: 3
current_phase: 0
tier_touched: [T2, T2+]   # a new scoped provisioning token + creating/destroying guests moves the
                          # blast-radius dial ⇒ MUST PR docs/system-design.md.
related:
  - docs/system-design.md
  - docs/design/access-and-trust.md
  - docs/design/network.md
  - docs/design/secrets.md
  - runbooks/provision-vm.md
  - planning/scratchpad/2026-08-17-declarative-future-and-agent-cognition.md
  - planning/scratchpad/research/2026-08-17-opentofu-provisioning.md
  - "[[SKY-007-progress]]"
  - "[[SKY-008-progress]]"
---

# SKY-008 · OpenTofu provisioning layer: VM and CT lifecycle plus DNS

> Push the declarative boundary down into *provisioning*: declare ops-managed VMs/CTs and DNS records
> as OpenTofu resources with a real dependency graph and `plan`-before-apply diffs — replacing the
> imperative `provision-vm.md` path. Tofu makes the box exist; [SKY-007](SKY-007-nixos-host-definition-piloted-on-the-ops-vm.md) defines what's on it.

## 1. Problem / motivation
Provisioning is the most imperative corner of Skynet: `runbooks/provision-vm.md` + scripts, run by
hand. There's no declared infra, no dependency graph, no plan-diff, and firewall/DNS are only
*mirrored* into git after the fact. `tofu plan` is a near-perfect LLM primitive — agent proposes,
human reads the exact diff, apply — and it's the same propose/dispose shape Skynet already runs.
(Thesis §5; research brief `research/2026-08-17-opentofu-provisioning.md`.)

## 2. Brainstorm — options considered

**Tool**
- **OpenTofu (CHOSEN)** over Terraform — open licence, native (≥1.7) state/plan encryption we can key
  from sops+age (below).

**Proxmox provider** *(research-informed)*
- **`bpg/proxmox` (CHOSEN)** — actively maintained, declares everything needed (VM-from-template +
  cloud-init, LXC, pools, ACLs/tokens, storage, SDN). **`Telmate/proxmox`** is legacy/narrow — rejected.
- **⚠ The one trap that would break the trust model:** bpg's *snippet-based* cloud-init uploads files
  over **SSH/PAM to the node** — a standing node-SSH dependency. **Use only API-native cloud-init
  fields** (IP/DNS/SSH-key injection through the token); never the snippet-upload feature. PCI/hardware
  passthrough needs `root@pam` → stays manual.

**Token / blast radius** *(research-informed)*
- **CHOSEN:** a dedicated `svc-tofu` user + **privilege-separated API token, ACL'd to the
  `ops-managed` pool path** (not `/`), with a purpose-built VM/Pool/Datastore operate role, **no
  `Sys.Modify` / no `root@pam`.** Cannot escalate to node-root or touch OPNsense (5001 is
  pool-excluded anyway). The token itself is provisioned out-of-band.

**State** *(research-informed)*
- **CHOSEN:** local backend on the ops VM, encrypted with OpenTofu's native **PBKDF2 passphrase**
  state/plan encryption, passphrase held in **sops+age** — no new KMS. State **contains cloud-init
  secrets** → treat as secret-bearing; **back up the passphrase** (lose it = unrecoverable state).

**DNS (Technitium)** *(research-informed)*
- **CHOSEN (pending vendor pin):** a community provider (`kenske/technitium`, 2025-11, or `kevynb`) —
  all single-maintainer/pre-1.0, so **pin + vendor**, point at a **zone-scoped** token (never server
  settings / T3). Fallback: generic `Mastercard/restapi` against the Technitium HTTP API for zero
  third-party trust. Or defer DNS to a later phase.

**Scope line** *(research-informed)*
- Under tofu: **only in-pool VM/CT lifecycle + DNS records.** Out: **OPNsense, all pool-excluded
  guests (5001/635/837/2020), node-level config, template bootstrap, and the tofu token itself.**
  Pool-membership changes remain a `docs/system-design.md` PR regardless of who makes them.

## 3. The plan
- **Scope / non-goals:** declared lifecycle of ops-managed guests + (optionally) DNS records.
  **Non-goals:** anything at the scope line above.
- **Hosts & tiers touched:** Proxmox API via `svc-tofu` (**T2**); the new standing token + guest
  create/destroy moves the blast-radius dial ⇒ **MUST PR `docs/system-design.md`** + an autonomy-ratchet step.
- **Rollback posture:** `git revert` the tofu config; **`destroy` is a ⚠ hard checkpoint, never
  auto-approved.** Import-first (P1) changes nothing live.
- **Grants / human actions:** Ali mints the scoped `svc-tofu` token (T2+/out-of-band); ⚠ checkpoints
  on every `apply` that creates/destroys until a pair is graduated.

### Phase 1 — read-only skeleton + import  (~1–2h)   `[ ]` not started
Scoped `svc-tofu` token, encrypted-state tofu skeleton, **import one existing ops-managed guest** and
prove `plan` shows **no drift**. **Also PRs `docs/system-design.md`** (new token + tool). Exit: clean
`plan` on an imported guest; nothing mutated.

### Phase 2 — provision a throwaway guest  (~1–2h)   `[ ]` not started
Create + destroy a disposable guest (docker-dmz-class) via API-native cloud-init; prove the full
lifecycle. **⚠ `destroy` checkpoint.** Exit: create/destroy round-trips cleanly from declared state.

### Phase 3 — DNS records (optional)  (~1–2h)   `[ ]` not started
Pin/vendor a Technitium provider (or restapi fallback) against a zone-scoped token; declare a test
record. Exit: a DNS record is tofu-managed within T2 zones only.

## 4. ▶ Execute prompt
```
Read planning/projects/SKY-008-opentofu-provisioning-layer-vm-and-ct-lifecycle-plus-dns.md and execute Phase <N>.
Follow AGENTS.md: plan loudly then run quietly, never merge your own PRs, request the
narrowest host / shortest grant the phase needs, and checkpoint at the listed human/grant
steps. When the phase's exit criteria are met, do the "Phase close-out" at the bottom.
```

## 5. Phase close-out (resume material)
- [ ] Land the work via **PR** (agent never merges its own) — including the `docs/system-design.md` change.
- [ ] Write/refresh a memory `SKY-008-progress` (what shipped, what's next, gotchas) + a MEMORY.md pointer.
- [ ] Bump this file's frontmatter (`current_phase`, `status`, `updated`) and flip the phase box to `[x]`.
- [ ] `bin/plan list` to refresh the roadmap index.
- [ ] Paste the **Continue prompt** below to resume in a fresh session:
```
Continue planning/projects/SKY-008-opentofu-provisioning-layer-vm-and-ct-lifecycle-plus-dns.md at Phase <N+1>.
Prereqs carried from the last phase: <…>. Resume context from memory [[SKY-008-progress]].
Follow AGENTS.md as above.
```

## 6. Status log
- 2026-08-17 — created (draft) from the declarative-future brainstorm §5. Provider/token/state/DNS
  decisions taken from the research brief `planning/scratchpad/research/2026-08-17-opentofu-provisioning.md`
  (bpg provider, snippet-upload trap, pool-scoped `svc-tofu` token, sops-keyed encrypted state). Pairs with SKY-007.
