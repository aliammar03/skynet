---
id: SKY-011
title: Machine-enforced invariants and the ambiguity-layering doctrine
status: in-progress
horizon: short
created: 2026-08-18
updated: 2026-08-18
phases: 3
current_phase: 1
tier_touched: [T1]     # repo files, read-only greps, a CI/pre-commit check. No blast radius moves.
                       # BUT it amends the constitution (adds a doctrine + wires enforcement onto the
                       # hard laws) ⇒ Phase 1 PRs docs/system-design.md — not to widen a dial, to
                       # record a principle. The enforcement gate only *asserts* the existing
                       # boundary; it never moves it.
related:
  - docs/system-design.md
  - docs/decisions/            # new ADR 0003 lands here
  - inventory/proxmox-core.json
  - inventory/proxmox-network.json
  - AGENTS.md                  # §6 Judgement Day checklist — the hard laws this gate enforces
  - .githooks/
  - planning/scratchpad/2026-08-17-declarative-future-and-agent-cognition.md
  - planning/projects/SKY-010-default-lean-context-load-on-demand.md
  - planning/ideas/SKY-008-opentofu-provisioning-layer-vm-and-ct-lifecycle-plus-dns.md
  - planning/ideas/SKY-007-nixos-host-definition-piloted-on-the-ops-vm.md
  - "[[SKY-011-progress]]"
---

# SKY-011 · Machine-enforced invariants and the ambiguity-layering doctrine

> The rigor of a rule comes from **who enforces it, not what format it's in**. An LLM reads YAML with
> the same latitude it reads prose — so a constraint is only "rock solid" once a *deterministic,
> non-LLM* process consumes it. This directive writes down the organizing principle
> (**ambiguity-tolerance layering; format follows enforcement**) as an ADR, then closes the concrete
> gap it exposes: the hard laws (excluded guests never pooled, blast radius = the declared pool set,
> no plaintext secrets) are enforced today by **nothing but the agent's memory**. Make a dumb script
> fail the PR instead.

## 1. Problem / motivation

Skynet's roadmap already leans hard on two good instincts — *shrink the always-loaded context*
(SKY-010) and *push the declarative boundary down* (SKY-007 Nix, SKY-008 Tofu). But a question kept
recurring: should the system design itself be rewritten "machine-readable" so the agent interprets it
less loosely? Working that through surfaced a principle none of the existing directives states
outright, and a safety gap that follows directly from it.

**The principle — format follows enforcement.** Converting an invariant from prose to a schema buys
nothing if the *only* consumer is still the LLM: it interprets `never_pool: [5001]` with exactly the
latitude it interprets the sentence "VM 5001 never joins any pool." You gain rigor only when a
**deterministic, non-LLM process** reads the machine-readable form. Three invariants are already
rock-solid, and none of it is because of formatting:

- the CA private key lives on Ali's workstation ⇒ the agent *cannot* mint root (guaranteed by physics);
- `git revert` → Arcane reconciles ⇒ rollback is deterministic;
- render scripts are the only writer of generated dirs ⇒ "never hand-edit" is structurally true.

**The gap.** Meanwhile the blast-radius laws are prose repeated across `AGENTS.md §6`,
`docs/system-design.md §2/§3`, and this file's own warnings — and enforced by **nothing**:

| Hard law (today: prose only) | What enforces it now | What *should* |
|---|---|---|
| VM 5001 / CT 635 / CT 837 / VM 2020 never join a pool | the agent remembering | a script reads `inventory/*.json`, fails the PR if an excluded VMID appears in a pool |
| Write blast radius = the declared `ops-managed` pool **set** | prose + a PR ceremony | the declared set lives in data; the gate asserts observed == declared |
| Secrets sops-encrypted or 0600 — never plaintext | the agent remembering | a grep for plaintext-secret patterns fails the PR |

This is precisely the exposure that grows the instant **SKY-008 (Tofu)** can touch pool membership:
pool membership *is* the blast-radius dial, so an agent proposing a `tofu apply` needs a dumb gate
behind it that a mis-generated plan can't talk its way past. The gate must exist **before** the
declarative-infra bets, not after.

**The doctrine also frames those bets.** "Ambiguity-tolerance layering" says: sort every artifact by
how much interpretation it can safely tolerate, and let that decide format *and* enforcement —
machine-*enforced* below (state, constraints, provisioning), natural-language *above* (judgment,
rationale), a thin retrieval pipe between (SKY-010). It's the missing spine that SKY-004/006/007/008/010
all silently assume; writing it down stops a future session from "helpfully" schematizing the
constitution and calling it safety.

## 2. Brainstorm — options considered

**What "machine-readable" should mean here**
- **Option A — rewrite `system-design.md` into a schema.** Convert invariants/tiers/exclusions to
  structured data the agent parses. *Tradeoff:* the LLM still interprets it with full latitude, so no
  rigor is gained; the constitution's job is to *constrain judgment*, which is a natural-language act;
  and you lose the human-legible law. Rejected.
- **Option B — leave everything as prose, rely on the agent.** *Tradeoff:* the status quo; the hard
  laws stay enforced by memory alone, exactly the gap. Rejected.
- **Decision: split by consumer (CHOSEN).** Extract only the *machine-checkable* constraints into
  typed data that a **deterministic gate** reads; keep the constitution, ADRs, and rationale as
  authored prose. Format follows enforcement: schematize a thing only when a non-LLM process will
  consume it.

**Where the invariant data lives**
- **Option A — inside `system-design.md`** as a fenced block. *Tradeoff:* mixes law (prose) with
  machine input; the renderer/gate would have to parse markdown. Rejected.
- **Option B — a new authored data file** (`invariants.json` at repo root). *Tradeoff:* one more
  top-level file — but it is *authored constraint* (desired truth), cleanly distinct from
  `inventory/` (observed truth) and from `docs/generated/` (machine-owned). **CHOSEN.** Each entry
  carries a one-line `why` so the *load-bearing* rationale rides with the constraint (an agent that
  knows 5001 is excluded but not *why* may one day "helpfully" pool it).

**How the gate runs**
- **Option A — nightly report-only.** *Tradeoff:* a violation is caught hours after it's committed —
  too late; the point is to block the bad PR. Rejected as the *primary* path.
- **Option B — a git hook + CI check that fails non-zero (CHOSEN).** Wire `check-invariants.sh` into
  `.githooks/` (already present) and the PR path so a violating change *cannot* land. Deterministic,
  engine-neutral, no LLM in the loop. The nightly can *also* run it as defense-in-depth.

**Does the doctrine belong in an ADR or the constitution?**
- **Decision: both, in their roles (CHOSEN).** The full reasoning → **ADR 0003** (durable, curated
  decision memory, per the memory spoke). A one-paragraph pointer in `system-design.md §2` so the
  constitution references the principle without absorbing the argument. Same ADR-vs-constitution split
  the system already uses.

## 3. The plan
- **Scope / non-goals:** an ADR stating the layering/enforcement doctrine + a one-para constitution
  pointer (Phase 1); an authored `invariants.json` registry of machine-checkable constraints with
  per-entry `why` (Phase 2); a deterministic `scripts/check-invariants.sh` wired into the git-hook/CI
  path so violations fail the PR (Phase 3). **Non-goals:** rewriting the constitution or any spoke into
  a schema (explicitly rejected — §2); building Tofu/Nix themselves (SKY-008/007 — this only lays the
  guardrail they'll need); the context-map/`bin/recall` work (SKY-010's lane); any new standing
  credential or blast-radius change (there is none — the gate only *asserts* the existing boundary).
- **Hosts & tiers touched:** ops VM only — repo files, read-only greps over `inventory/`, a CI/hook
  script. **T1**, no blast radius moves. Phase 1 PRs `docs/system-design.md` to *record the doctrine*
  (a principle, not a widened dial); Phases 2–3 are additive repo files.
- **Rollback posture:** fully additive/reversible. `git revert`; `invariants.json` is data;
  `check-invariants.sh` is read-only and can be unwired from `.githooks/` in one line. A gate that
  proves too strict is loosened by editing the registry, in a PR, in the open.
- **Grants / human actions:** none. Lands via PR like everything else (agent never merges its own).

### Phase 1 — the doctrine: ADR 0003 + constitution pointer  (~1–2h)   `[x]` done
Write the organizing principle down before building anything, so the build has a spine to cite.
Steps:
1. Author **`docs/decisions/0003-ambiguity-layering-and-format-follows-enforcement.md`** (follow the
   ADR house style; amend-in-place per conventions). Capture: the ambiguity-tolerance ladder
   (state → constraints → provisioning → procedures → directives → judgment); **format follows
   enforcement** (schematize only what a non-LLM consumer reads); machine-*enforced* below,
   natural-language *above*; the constitution/ADRs/rationale stay authored prose; state/reference are
   *generated from* data. Note it as the spine tying SKY-004/006/007/008/010 together.
2. Add a one-paragraph pointer in `docs/system-design.md` **§2** (invariants): the hard laws should be
   *machine-enforced wherever a deterministic check exists*, and name ADR 0003 as the doctrine. Do
   **not** convert §2/§3 to data — reference, don't rewrite.
3. Cross-link: add ADR 0003 to the `related:` of SKY-007/008/010 where it clarifies "what to
   schematize"; the digest will surface it as a recent decision automatically (`render-digest.sh`).

Exit criteria: ADR 0003 exists and is `accepted`; `system-design.md §2` points to it in one
paragraph without being rewritten; the doctrine names the directives it frames.
Grants / human actions: **⚠ constitution PR** — Phase 1 edits `docs/system-design.md`; land via PR,
Ali merges (agent never merges its own).

### Phase 2 — the invariant registry: `invariants.json`  (~1–2h)   `[ ]` not started
Extract the machine-checkable constraints into one authored source of truth.
Steps:
1. Write **`invariants.json`** (repo root; authored *desired* truth — distinct from observed
   `inventory/` and machine-owned `docs/generated/`). Schema, roughly:
   - `excluded_guests`: `[{vmid, name, tier: T3, why}]` — 5001 (OPNsense), 635, 837, 2020 (Unraid) —
     "never joins any pool; seen at T1, touched never."
   - `ops_managed_pools`: the declared blast-radius **set** (the dial's current position, with `why`).
   - `t3_targets`: the never-standing-credential list (OPNsense, Mgmt Caddy, Authentik, node root,
     Unraid root, Technitium settings) — for future checks; documented now.
   - `secret_patterns`: the plaintext-secret signatures the gate greps for.
   Each top-level entry carries a one-line `why` so rationale rides with the constraint.
2. Document the file in a short `docs/conventions/` note (or extend the existing docs spoke): what it
   is, that it's **authored** (not generated), and that changing `ops_managed_pools` is a
   `system-design.md` PR (it *is* the dial). Tag `[testable]` — Phase 3 makes it enforceable.
3. Sanity-check the registry against reality: the excluded VMIDs and the pool set must match today's
   `inventory/proxmox-core.json` / `proxmox-network.json` (read-only). Record any mismatch as a finding,
   don't silently "fix" inventory (it's observed truth).

Exit criteria: `invariants.json` exists, validates as JSON, encodes the four constraint classes with
per-entry `why`, and matches current inventory; the convention note explains it and flags the pool-set
PR ceremony.
Grants / human actions: none.

### Phase 3 — the enforcement gate: `check-invariants.sh` + hook/CI  (~1–2h)   `[ ]` not started
Make the constraints fail a bad PR deterministically — no LLM in the loop.
Steps:
1. Write **`scripts/check-invariants.sh`** — read-only, engine-neutral (matches the `render-*.sh`
   house style), exits non-zero with a precise message on any violation. Assertions:
   - no `excluded_guests[].vmid` appears as a member of any pool in `inventory/*.json`;
   - the set of `ops-managed` pools observed in inventory == `ops_managed_pools` (drift either way is
     a violation — an undeclared pool is as bad as a missing one);
   - `git grep` finds none of `secret_patterns` in tracked non-encrypted files (respect `.sops.yaml`
     coverage; allow `*.sops.*` / documented fixtures).
2. Wire it into the **`.githooks/`** pre-commit path (already the repo's hook home) *and* leave a
   documented one-liner for a CI/PR gate, so the check runs both locally and on the PR. Fast, no
   secrets, no network.
3. Prove it: add a throwaway commit that violates one rule (e.g. a fake pool member 5001) on a scratch
   branch, show the gate blocking it, revert. Seed a journal `session` entry recording the gate
   catching a planted violation (episodic evidence it works).

Exit criteria: `check-invariants.sh` passes clean on `main`, fails with a clear message on a planted
violation, and runs from the git-hook path (+ a documented CI hook); a journal entry demonstrates the
block. The hard laws are now enforced by a script, not by memory.
Grants / human actions: none.

## 4. ▶ Execute prompt
> Paste into a fresh Skynet session to run this directive. Swap `<N>` for the phase to run.
```
Read planning/projects/SKY-011-machine-enforced-invariants-and-the-ambiguity-layering-doctrine.md
and execute Phase <N>. Follow AGENTS.md: plan loudly then run quietly, never merge your own PRs,
request the narrowest host / shortest grant the phase needs, and checkpoint at the listed
human/grant steps (Phase 1 edits the constitution — land it by PR). When the phase's exit
criteria are met, do the "Phase close-out" at the bottom.
```

## 5. Phase close-out (resume material)
Run this every time a phase finishes successfully — it's what makes the next session cold-startable:
- [ ] Land the work via **PR** (agent never merges its own).
- [ ] Write/refresh a memory `SKY-011-progress` (what shipped, what's next, gotchas) + a MEMORY.md pointer.
- [ ] Bump this file's frontmatter (`current_phase`, `status`, `updated`) and flip the phase box to `[x]`.
- [ ] `bin/plan list` to refresh the roadmap index.
- [ ] Paste the **Continue prompt** below to resume in a fresh session:
```
Continue planning/projects/SKY-011-machine-enforced-invariants-and-the-ambiguity-layering-doctrine.md
at Phase <N+1>. Prereqs carried from the last phase: <…>. Resume context from memory
[[SKY-011-progress]]. Follow AGENTS.md as above.
```

## 6. Status log
*(One dated line per milestone — cite PR numbers; convert relative dates to absolute. Newest last.)*
- 2026-08-18 — created (draft) and promoted to **projects/** from a session re-examining "should the
  system design be machine-readable?". Landed the reframe: **format follows enforcement** — an LLM
  interprets schemas with the same latitude as prose, so rigor comes only from a deterministic
  non-LLM consumer. Scoped three phases: doctrine ADR (0003) + constitution pointer; an authored
  `invariants.json` registry; a `check-invariants.sh` gate wired into the hook/CI path that fails a
  PR violating a hard law. Sequenced **before** SKY-008 (Tofu), whose pool-touching plans need the
  gate behind them. Sibling context: the `declarative-future-and-agent-cognition` scratch note.
- 2026-08-18 — **Phase 1 done** (PR pending). Authored ADR 0003
  (`0003-ambiguity-layering-and-format-follows-enforcement`, `accepted`): the ambiguity-tolerance
  ladder (state → constraints → provisioning → procedures → directives → judgment), **format follows
  enforcement** (schematize only what a non-LLM consumer reads), machine-enforced below / prose
  above, and the named anti-pattern of rewriting the constitution into a schema. Added a
  one-paragraph pointer as new `system-design.md §2c` (references the doctrine, does *not* rewrite
  §2a/§2b). Cross-linked ADR 0003 into `related:` of SKY-007/008/010. Next: Phase 2 —
  `invariants.json`.
