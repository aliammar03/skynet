---
id: SKY-028
title: Convention lint gate in skynet check
status: draft
horizon: short
created: 2026-09-26
updated: 2026-09-26
phases: 1
current_phase: 0
tier_touched: [T1]     # T1 | T2 | T2+ | T3 — if it hits T2+/T3 or moves a blast-radius boundary,
                       # the plan MUST also PR docs/system-design.md (the constitution).
related:               # authoritative files this directive touches
  - docs/conventions.md
---

# SKY-028 · Convention lint gate in skynet check

> Turn the `[testable]` convention rules into `skynet check` failures, so drift is blocked
> before merge instead of caught in review. Builds on SKY-025 Phase 12 (`skynet check`).

<!-- HOW TO USE THIS TEMPLATE (delete this block once the directive is fleshed out).
  `skynet plan` stamps this file for every new directive and auto-fills id / title / created /
  updated / status / horizon — so editing THIS file raises the floor for all future plans.
  The conventions that keep directives uniform (all proven in SKY-001 / SKY-003):
    • Sizing — one phase = one reviewable PR. Anything bigger ⇒ split it.
    • Decisions — one block per decision in §2; mark the winner (CHOSEN); keep the roads
      not taken so nobody re-litigates them.
    • Checkpoints — flag every T3 / destructive / credential / leaves-scope step as a
      ⚠ hard checkpoint (Ali acts; the agent stops and waits).
    • One PR per phase — it carries the work, `bin/check` evidence, its tier, and the §4 Status update.
    • Frontmatter — keep parsed keys value-only (NO inline `#` on title/phases/current_phase);
      `current_phase` = last COMPLETED phase (0 = not started); bump `phases` as you add them.
-->

## 1. Problem / motivation
What's wrong, missing, or worth improving today. The pain, concretely.

## 2. Brainstorm — options considered
*(The "we talked it through" record — one block per decision. Mark the winner (CHOSEN) and
preserve the roads not taken, with the tradeoff that killed each, so they stay killed.)*
- **Option A —** … tradeoffs.
- **Option B —** … tradeoffs.
- **Decision:** chose **X (CHOSEN)** because … .

<!-- Repeat the block for each independent decision (engine, placement, tier, TLS, …). -->

## 3. The plan
- **Scope / non-goals:** what's in, what's explicitly out.
- **Hosts & tiers touched:** … (drives grants + whether `docs/system-design.md` needs a PR).
- **Rollback posture:** how we back out (`git revert`, disable a timer, `docker compose down`, …).
- **Grants / human actions:** the narrowest host + shortest duration per phase.

### Phase 1 — <name>   `[ ]` not started   · review: Light | Full
Steps:
1. …
2. …

Exit evidence (how we know it's done): … — for a write path, name the failure-case test.
Grants / human actions: … — mark any T3 / destructive / credential step a **⚠ hard checkpoint**.

<!-- Add Phase 2, Phase 3, … Each phase is one PR. The tier is Full if the phase touches anything
     on the Full list in docs/conventions/construction.md. -->

## 4. Status
Current: Phase 0 not started. Next: Phase 1.
<!-- The phase PR itself updates this block, the phase box, and the frontmatter
     (`current_phase`, `status`, `updated`) — merge is completion. Run `skynet plan list` in the same PR. -->

## 5. Prompts
Execute / review: [`planning/prompts/`](../prompts/README.md) with this directive's path.

## 6. Status log
*(One dated line per milestone — cite PR numbers; convert relative dates to absolute. Newest last.)*
- 2026-01-01 — created (draft).

## From scratchpad
# Deferred: lint gate for convention enforcement (Style C)

**Status:** parked 2026-08-17. Split off from the "Convention bedrock" plan, which is
proceeding as **A→B only** (doctrine spine + golden templates). This is the **C** layer —
the executable contract that blocks drift before merge. Revive once A+B exist and there's
enough written law worth guarding.

## Why parked, not dropped
A→B makes new stuff *born correct* and gives one authoritative definition. C only pays off
*after* the rules are written and testable — it asserts the same rules the doctrine states and
the templates embed. Building it before the doctrine settles would hard-code rules still in flux.

## The idea (Style C, from the layered A→B→C choice)
`bin/lint` turns the P1 doctrine rules (each tagged testable/not) into machine checks.
Candidate first batch — all unambiguous:

- **Naming/slugs** — `SKY-###-kebab.md`, hostnames lowercase role-first, branch grammar
  (`phase/ deploy/ fix/ inventory/`).
- **Layout** — required files per artifact type (e.g. a `compose/<svc>/` has `compose.yaml`
  + `.env.git`; `.env.sops` when secrets exist).
- **Compose** — image is digest-pinned (no floating `latest`), every service has `env_file: .env`.
- **Scripts** — `#!/usr/bin/env bash`, `set -euo pipefail`, header block (purpose/tier/usage).
- **Generated dirs** — no hand-edits staged under `inventory/**` or `docs/generated/**`.
- **Frontmatter** — directive/service/ADR frontmatter validates against its schema.

## Wiring (facts as of 2026-08-17)
- Enforcement today = pre-commit only: `core.hooksPath=.githooks` → `.githooks/pre-commit`
  → `skynet check`. Extend the hook to run `bin/lint` **after** it.
- **No GitHub Actions CI exists.** A `.github/workflows/lint.yml` is the one piece that adds a
  new dependency but is what makes a *PR* go red (not just a local commit). Decide if wanted.
- Run `bin/lint` **report-only in `scripts/nightly.sh` first** (drift as a nightly signal),
  then promote rules warn→block **one PR at a time** — the autonomy-ratchet discipline applied
  to conventions. Never flip the whole gate on at once.

## Ratchet / ordering
1. Land A (doctrine) + B (templates) first.
2. Backfill existing artifacts to green (else the gate can't enforce cleanly).
3. `bin/lint` report-only in nightly.
4. Promote rules to blocking one PR at a time; optional GH Actions check last.

## To revive
`bin/plan idea planning/scratchpad/2026-08-17-lint-gate-convention-enforcement.md`
(promotes this note into a proper SKY-### idea). Likely a follow-on to the A→B convention directive.
