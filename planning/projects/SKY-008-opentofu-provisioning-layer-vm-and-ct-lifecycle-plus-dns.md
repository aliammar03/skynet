---
id: SKY-008
title: OpenTofu provisioning layer: VM and CT lifecycle plus DNS
status: active
horizon: long
created: 2026-08-17
updated: 2026-09-02
phases: 3
current_phase: 3
tier_touched: [T2, T2+]   # a new scoped provisioning token + creating/destroying guests moves the
                          # blast-radius dial ⇒ MUST PR docs/system-design.md.
related:
  - docs/system-design.md
  - docs/decisions/0003-ambiguity-layering-and-format-follows-enforcement.md  # the gate a pool-touching plan needs behind it
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

### Phase 1 — read-only skeleton + import  (~1–2h)   `[x]` done
Scoped `svc-tofu` token, encrypted-state tofu skeleton, **import one existing ops-managed guest** and
prove `plan` shows **no drift**. **Also PRs `docs/system-design.md`** (new token + tool). Exit: clean
`plan` on an imported guest; nothing mutated.

### Phase 2 — provision a throwaway guest  (~1–2h)   `[x]` done
Create + destroy a disposable guest (docker-dmz-class) via API-native cloud-init; prove the full
lifecycle. **⚠ `destroy` checkpoint.** Exit: create/destroy round-trips cleanly from declared state.
Landed as a **permanent base template** `ubuntu-2404-base` (9000) + a throwaway clone (10099) proving
clone→boot→destroy. New follow-up: extend tofu to the **network node** (standalone — own `svc-tofu`).

### Phase 3 — DNS records + declarative LXC import  (~1–2h)   `[~]` LXC done, DNS staged
**LXC import — DONE (2026-09-02):** CT 240 imports zero-drift (see status log + [[SKY-008-progress]]).
**DNS — STAGED (Ali's call):** the DNSSEC read bug in `kevynb/technitium` v0.4.0 only affects the
*signed* zone, so we split by zone:
- **`aliammar.net` (unsigned Forwarder + A overrides) — DONE:** 10 admin vanity A records imported +
  9 app-service A records created (the apps-Caddy vhosts → 10.10.100.35; the `*.aliammar.net` wildcard
  is now retired — Ali deleted it 2026-09-02),
  tofu-managed zero-drift (`tofu/dns-aliammar-net.tf`, `technitium_record` for_each). v0.4.0 reads the
  unsigned zone fine.
- **`tdns.home.aliammar.net` (DNSSEC-signed resolver zone) — deferred until a kevynb release** carries
  the fix (commit `b2f6b89c`, 2026-08-20; v0.4.0 is still latest). We chose NOT to un-sign it — its
  TLSA/DANE records depend on the signing.
Open blocker for full lifecycle: the scoped token can *add/modify* but **not delete** records
(`tofu destroy` on a record fails) — Ali to add record-delete. A leftover `tofu-test` record in the
signed zone also awaits that grant (or a manual delete).

Two remaining declarative surfaces, deferred out of P2:
- **DNS (Technitium):** pin/vendor a Technitium provider (or restapi fallback) against a zone-scoped
  token; declare a test record. A DNS record is tofu-managed within T2 zones only.
- **Declarative LXC import:** prove a clean zero-drift import of an existing `ops-managed` container
  (P2 proved clone→destroy but not import — bpg's `proxmox_virtual_environment_container` tends to
  drift on `operating_system.template_file_id`, absent from a live container's config; find the
  `ignore_changes`/config shape that lands `plan` = No changes).

Exit: a DNS record is tofu-managed within T2 zones, **and** an existing LXC imports with zero drift.

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
- 2026-08-26 — promoted to active, Phase 1 in progress. Built: `tofu/` skeleton (bpg/proxmox ~0.111,
  PBKDF2 encrypted state, API-native only), vm-docker-dmz resource from live API config, sops-encrypted
  passphrase + token placeholder, `scripts/tofu-env.sh` wrapper, NixOS base.nix +opentofu. PRd
  `docs/system-design.md` (T2 row + extension point + growth direction) and `access-and-trust.md`
  (`svc-tofu`/`TofuProvisioner` pveum stanza). Human checkpoint: Ali mints the token + applies NixOS
  rebuild, then import/plan to prove zero drift.
- 2026-08-26 — Phase 1 DONE. Token minted, `tofu init` + `import server-proxmox-core/10015` +
  `plan` = **"No changes. Your infrastructure matches the configuration."** on first attempt.
  One harmless warning: `VM.GuestAgent.Audit` — the TofuProvisioner role correctly omits guest-agent
  privs. Follow-up: add tofu sops files to sops-nix decryption (binary format) so tofu-env.sh works
  without sudo.
- 2026-08-27 — Phase 2 DONE (core node). Built permanent template `ubuntu-2404-base` (9000); proved
  clone→boot→destroy via throwaway 10099; `plan` clean after removal. Roles: `TofuProvisioner`
  (lifecycle, pool-scoped) + new config-only `TofuVmConfig` at `/vms` (no Allocate/PowerMgmt).
  Constitutional change PR'd: excluded-guests line now "never pooled/destroyed/stopped" (tofu keeps
  config-only reach over co-located Unraid 2020). Nodes are **standalone, not clustered** → ACLs
  per-node. Full run + ACL saga in [[journal 2026-08-27 SKY-008 P2]].
- 2026-08-27 — **Network node done too** (same PR). Standalone .10 → 2nd provider alias `proxmox.network`,
  own `svc-tofu` (Ali mirrored core incl blanket `/vms` → config-reach over 5001/635/837, never
  destroy/stop), sops secret `tofu-proxmox-network.env` + combined CA bundle in `tofu-env.sh`. Proved
  lifecycle by cloning the disused cloudflared LXC 1033 → 1099, destroyed both. LXC-clone gotcha: stop
  the source first. [[journal 2026-08-27 SKY-008 network node]]. Next: P3 DNS.
- 2026-09-02 — **P3 split.** **LXC import DONE:** CT 240 imported as `proxmox_virtual_environment_container.pbs`
  (`tofu/lxc-pbs.tf`), zero-drift `plan` after pinning the fields bpg can't round-trip on import
  (`ignore_changes`: operating_system/template_file_id, description, initialization, pool_id, vm_id,
  timeout_*) and matching the read-back `console` block. This is the import technique SKY-018 P11 +
  SKY-020 reuse. **DNS deferred:** `kevynb/technitium` v0.4.0 can't refresh a DNSSEC-signed zone
  (numeric `DNSKEY.protocol`; fix on `main` @ `b2f6b89c`, unreleased). `add` proven (record created +
  verified live, then removed); token also lacks record-delete. Full DNS recipe + gotchas in
  [[SKY-008-progress]] for a clean resume when kevynb releases. LXC landed via PR (agent never self-merges).
- 2026-09-02 (same session, cont.) — **DNS staged by zone (Ali's call).** Since the v0.4.0 read bug
  only hits *signed* zones, we tofu-manage the **unsigned `aliammar.net`** zone now and defer the
  signed resolver zone. Imported all 11 vanity A records (`tofu/dns-aliammar-net.tf`, `technitium_record`
  for_each; `zone` omitted → inferred, else phantom `+ zone` diff). `plan` = No changes across VMs +
  LXC + DNS. Provider url must OMIT `/api` (client prepends it). Deferred `tdns.home.aliammar.net`
  stays signed (TLSA/DANE depends on it) until kevynb releases. Same branch/PR #143.
