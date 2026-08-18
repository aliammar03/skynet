---
id: SKY-012
title: Runbooks as executable capabilities
status: draft
horizon: short
created: 2026-08-18
updated: 2026-08-18
phases: 1
current_phase: 0
tier_touched: [T1, T2]   # writing capabilities is T1 repo work; a capability RUNS at its runbook's
                         # existing tier (T2/T2+). No new trust boundary, no blast-radius move —
                         # promoting a capability to auto-approve is a separate ratchet PR to AGENTS.md.
related:
  - docs/system-design.md
  - AGENTS.md
  - runbooks/README.md
  - docs/conventions/scripts.md
  - docs/design/gitops-loop.md
  - planning/scratchpad/2026-08-17-declarative-future-and-agent-cognition.md
  - planning/archive/SKY-010-default-lean-context-load-on-demand.md
  - planning/projects/SKY-011-machine-enforced-invariants-and-the-ambiguity-layering-doctrine.md
  - "[[SKY-012-progress]]"
---

# SKY-012 · Runbooks as executable capabilities

> Promote the **deterministic** half of each runbook from *prose the agent reads and interprets* to
> *a capability the agent runs*. Cuts procedural read-cost (the way SKY-010 cut retrieval-cost) and
> removes interpretation latitude from steps that never needed judgement — leaving the runbook as a
> thin judgement shell around a tested script.

## 1. Problem / motivation

A runbook today is engine-neutral markdown the agent **reads, loads into context, then interprets**
step by step. That carries two costs:

- **Procedural read-cost.** Every execution loads the whole runbook — SKY-010's context map measured
  them at up to ~1.6K tokens each (`publish-service` 1636, `backup` 1183, `restore-service` 1105).
  The agent pays that to re-derive steps it has run many times.
- **Interpretation latitude.** Many runbook steps are *deterministic* — clone the golden template,
  assign the VLAN/IP by the naming rule, run `provision-restic.sh`, `git revert` + let Arcane
  converge. These don't need an LLM to *interpret*; they need a script to *run*. Prose leaves room to
  execute a mechanical step slightly wrong; a tested capability cannot be misread.

This is the same lever as **SKY-011** ("format follows enforcement" — rigor comes from a
deterministic consumer, not from the LLM re-reading prose) applied to procedures, and the concrete
form of the scratchpad principle **"diagnose imperatively, fix declaratively / no orphan fixes."**
Skynet already leans this way (`provision-vm` calls `provision-restic.sh`; the deploy loop is
`gitops-deploy.sh` + Arcane) — this makes it the *norm*, not the exception.

## 2. Approach — what we'd build

For each **deterministic** runbook, split it in two:

- **The capability** — an idempotent script (`scripts/` or `bin/`, house style per
  [scripts.md](../../docs/conventions/scripts.md)) that performs the mechanical steps end-to-end,
  fails safe, and declares its tier. The agent *runs* it instead of reading + retyping the steps.
- **The judgement shell** — the prose that *remains* in the runbook is only the decisions,
  the plan, and the hard checkpoints. It names its capability (`Executor:` line, as
  `deploy-service.md` already does) and stays catalogued in `runbooks/README.md` + the context map.

So a runbook stops being "instructions to interpret" and becomes "a decision wrapper around a tested
command." Read-cost drops to the shell; the mechanical core is enforced by being code.

## 3. Scope & boundaries

- **In:** the repeatable, deterministic procedures — deploy, publish, provision, backup, the
  restore *happy path*, update-guests. Each gets a capability + a slimmed judgement shell + a test on
  the `vm-docker-dmz` bench where feasible.
- **Out (stays prose — deliberately):** DR runbooks and diagnosis/forensics. Incident response is
  inherently judgement and imperative, and the agent is *good* at it — the declarative-future note's
  contrarian guardrail (*don't over-automate*) applies. A capability is for what repeats, not for
  what surprises you.
- **No new trust.** A capability runs at its runbook's existing tier; it mints no new standing
  credential and moves no blast-radius boundary. Making a capability *auto-approved* on the nightly
  is a **separate** ratchet PR to `AGENTS.md` (§3), one capability at a time — the leash stays in git.

## 4. Relationship to other directives

- **SKY-010** cut *retrieval* cost (load-on-demand + the scout); this cuts *procedural* cost — the
  sibling it explicitly flagged for its own `SKY-###`.
- **SKY-011** ("format follows enforcement") is the doctrine: a capability is a procedure made
  rock-solid by a deterministic consumer. This is that doctrine applied to runbooks; capabilities are
  natural targets for the same test/lint gate.
- **Autonomy ratchet** (`AGENTS.md` §2/§3): tested capabilities are the *unit* that graduates onto
  the auto-approve list — you can't safely auto-approve a prose step, but you can a tested script.

## 5. When promoted to a project

Likely phasing (sketch — fill in at `bin/plan start`): (P1) a pilot — convert one runbook
(`publish-service` or `update-guests`) to a capability + judgement shell, prove the pattern + a bench
test; (P2) convert the rest of the deterministic set; (P3) document the capability/judgement-shell
convention in `scripts.md` + `docs.md`, and wire capability tests into the CI gate. Each phase is a
PR; DR/diagnosis runbooks are left untouched.

## 6. Status log
- 2026-08-18 — created (draft) as the sibling idea SKY-010 flagged: promoting deterministic runbooks
  to executable capabilities to cut procedural read-cost and interpretation latitude. Horizon short
  (fits today's system; no new trust boundary). Grounded in the declarative-future scratchpad §2
  ("better imperative work") and the SKY-011 "format follows enforcement" doctrine.
