---
id: SKY-020
title: Firewall-as-code — OPNsense config to T2 via OpenTofu
status: in-progress
horizon: long
created: 2026-09-01
updated: 2026-09-01
phases: 6
current_phase: 1
tier_touched: [T2, T3]   # moves the OPNsense boundary — the constitution PR is ADR 0006 / PR #137.
related:
  - docs/system-design.md
  - docs/decisions/0006-opnsense-read-is-t1-write-stays-t3.md
  - planning/projects/SKY-018-eight-layer-reconciliation-entity-spine-the-analyze-phase-and-the-verification-toolchain.md
  - "[[opnsense-readonly-and-gitbackup]]"
  - "[[SKY-020-progress]]"
---

# SKY-020 · Firewall-as-code — OPNsense config to T2 via OpenTofu

> Make OPNsense firewall config a reviewed `tofu plan`: the agent proposes alias/rule changes as a
> PR, a human merges, the saved-plan executor pushes them via the API — the same T2 GitOps loop as
> managed guest envelopes. The tier decision is **ADR 0006** (config T2, node-root/reboot/self-leash T3); this
> directive is the **build**.

> **Status: idea.** Long horizon. Promote with `bin/plan start SKY-020`. Gated on the ADR 0006 /
> PR #137 constitution merge landing first.

## 1. Problem / motivation

OPNsense is the one device the agent most often needs to reason about and cannot touch. Today firewall
config is read-only through a git mirror; every change is a human clicking through the OPNsense UI, and
the agent can only *propose in prose*. ADR 0006 moves firewall **config** to T2 — but a tier decision
without a mechanism is just a promise. The mechanism has to be **reviewable at the diff level** (not a
`config.xml` restore blob), **reuse the existing T2 machinery** (saved-plan review and scoped apply),
and **be unable to widen the agent's own leash** — the firewall is the meta-boundary, so a bad rule
could open the network or the agent's own reach. That last constraint is the whole reason this is its
own directive and not a one-session hack.

## 2. Key decisions (full rationale in ADR 0006)

- **Mechanism = the OpenTofu OPNsense provider**, not raw `config.xml` restore. Resource-level plans
  read like every other T2 change; a config-restore blob is all-or-nothing and unreviewable. **CHOSEN.**
- **Reuse the saved-plan model:** a standing T2 **write** API key used *only* by the scoped executor
  on a merged and approved plan; the agent never applies an unmerged plan. **CHOSEN.**
- **The self-leash set is T3 forever**, enforced two ways: every change is human-merged (a human sees
  any plan touching it), and a **conftest/Rego gate on `tofu plan -json`** hard-denies it. That gate is
  **SKY-018 P7** — this directive consumes it rather than rebuilding it. **CHOSEN.**
- **Reboot/halt stays a hard checkpoint** at every tier (lab-wide outage). Not a tofu resource. **CHOSEN.**

## 3. The plan

- **Scope:** firewall **aliases + rules** as `tofu/` resources, PR-gated apply, the self-leash gate,
  and tested apply+rollback. Plus the near-term **T1 live-read** cutover of `collect-firewall.sh`.
- **Non-goals:** interface/VLAN/NAT/VPN config (later, if ever), node root, reboot automation, and
  anything in the self-leash set (human-merged forever). No autonomy promotion (that's SKY-017).
- **Hosts & tiers touched:** the ops VM + OPNsense API. Moves the OPNsense boundary → the constitution
  PR is **ADR 0006 / #137** (must merge first). The T2 write key is a **⚠ credential checkpoint** (Ali).
- **Rollback posture:** every phase additive; `git revert` restores. `apply` snapshots config first and
  reverts on failure (Phase 5). The read collector degrades to the mirror.
- **Grants / human actions:** Ali merges #137; Ali mints two OPNsense API keys (read `svc-skynet-recon`,
  write `svc-skynet-tofu`); normal PR merges thereafter.

### Phase 1 — T1 live-read cutover  (~1–2h)   `[x]` done 2026-09-01 (PR #139)
The near-term win, independent of the write layer. Shipped as a **new** `scripts/collect-opnsense.sh`
→ `inventory/opnsense.json` (rather than munging the mirror-parsed `firewall.json`): live aliases,
rules, ARP neighbours, interfaces, firmware via `svc-skynet-recon`. Verified TLS by **deriving the SNI
from the pinned cert** (`OPNsense.internal`); degrades to `exit 0` with no creds/unreachable. Read-only
proven live: a valid `addItem` → `denied for write access (user-config-readonly set)`, nothing created.
The mirror (`collect-firewall.sh`) stays the git-truth config source; the live read runs alongside it.
Exit: live firewall inventory with no mirror lag; mirror still the git-truth backstop; no creds ⇒ mirror. ✅
Done: Ali created the read-only `svc-skynet-recon` key + the reachability rule (rule 360 dest `(self)`,
`PORT_OPS_API` += 443); PRs #138 (credential) + #139 (collector).

### Phase 2 — provider spike + one imported alias  (~1–2h)   `[ ]` not started
Adopt the OPNsense tofu provider (evaluate `browningluke/opnsense` vs alternatives; pin it). With the
T2 write key, **import one existing alias** as a resource and show a clean `tofu plan` (no diff).
Exit: `tofu plan` is clean for one real alias; the provider auths with the scoped write key.
⚠ Credential checkpoint: Ali creates the T2 write key (`svc-skynet-tofu`, config-write, NOT node root).

### Phase 3 — import the estate  (~1–2h)   `[ ]` not started
Import the current **41 aliases + 29 rules** as tofu resources (`import`, never recreate). Reconcile
`tofu plan` to clean against reality. Leave interfaces/NAT/VPN observed-only, on purpose.
Exit: `tofu plan` clean for every declared alias/rule; no resource recreation; excluded areas untouched.

### Phase 4 — the self-leash gate (consumes SKY-018 P7)  (~1–2h)   `[ ]` not started
`policy/firewall/self-leash.rego` over `tofu plan -json`: **deny** any plan that creates/edits/deletes a
rule or alias in the self-leash set (`ROLE_OPS_*`, `ROLE_OPS_PRIV_TARGETS`, block-other-DNS, the
`svc-skynet-*` accounts). `conftest verify` unit tests. Wired into CI + the apply wrapper. Report-only
one cycle, then enforce.
Exit: a PR whose plan touches the self-leash set fails CI; `conftest verify` passes; a benign plan passes.

### Phase 5 — apply + rollback wrapper  (~1–2h)   `[ ]` not started
`scripts/opnsense-apply.sh`: snapshot the current config (API backup) → apply the **saved** plan (never
a re-planned one) → verify reachability → **restore the snapshot on failure**. `destroy`/reboot refused
outright. Tested **in the failure case**, not just reasoned about (ADR 0005 §3).
Exit: a deliberately-bad apply auto-reverts to the snapshot with no human action.

### Phase 6 — first change through the loop + graduation  (~1–2h)   `[ ]` not started
Make one real, benign firewall change end-to-end: edit `tofu/`, open a PR, human-merge, `apply`.
Document the loop in the network + access-and-trust spokes. Hand a track record to SKY-017.
Exit: a firewall change lands via PR→merge→apply; the loop is documented; `apply` starts human-gated.

## 4. ▶ Execute prompt
```
Read planning/projects/SKY-020-firewall-as-code-opnsense-config-to-t2-via-opentofu.md and execute Phase <N>.
Follow AGENTS.md: plan loudly then run quietly, never merge your own PRs, request the narrowest
host / shortest grant the phase needs, and checkpoint at the listed human/credential steps.
Phase 1/2 need Ali-created OPNsense API keys — stop and wait there. When the phase's exit
criteria are met, do the "Phase close-out" below.
```

## 5. Phase close-out (resume material)
- [ ] Land the work via **PR** (agent never merges its own).
- [ ] Write/refresh a memory `SKY-020-progress` (what shipped, what's next, gotchas) + a MEMORY.md pointer.
- [ ] Bump this file's frontmatter (`current_phase`, `status`, `updated`) and flip the phase box to `[x]`.
- [ ] `bin/plan list` to refresh the roadmap index.
- [ ] Paste the **Continue prompt** below to resume in a fresh session:
```
Continue planning/projects/SKY-020-firewall-as-code-opnsense-config-to-t2-via-opentofu.md at Phase <N+1>.
Prereqs carried from the last phase: <…>. Resume context from memory [[SKY-020-progress]].
Follow AGENTS.md as above.
```

## 6. Status log
- 2026-09-01 — created (draft). Spun out of the OPNsense tier decision (ADR 0006 / PR #137): firewall
  read+diagnostics T1, config T2 via OpenTofu, node-root/reboot/self-leash T3. Gated on #137 merging;
  the self-leash gate consumes SKY-018 P7; reuses the SKY-008 tofu model.
- 2026-09-01 — **#137 merged; P1 done.** `svc-skynet-recon` read key (group `skynet-recon`, "System:
  Deny config write") minted by Ali; reachability opened (rule 360 dest `(self)` + `PORT_OPS_API` += 443,
  OPNsense GUI on 443/all-ifaces via the `.90.1` VLAN-90 iface). `secrets/opnsense.env.sops` (#138) +
  `scripts/collect-opnsense.sh` (#139) → `inventory/opnsense.json` (59 aliases, 129 rules, 42 ARP, 17
  ifaces, firmware). Read-only PROVEN live (write → `user-config-readonly` denial). Cert SAN is
  `OPNsense.internal` (collector derives SNI from the cert). **Next: P2 — the OPNsense tofu provider spike.**
