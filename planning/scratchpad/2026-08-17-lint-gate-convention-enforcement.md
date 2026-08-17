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
  → `scripts/secret-scan.sh`. Extend the hook to run `bin/lint` **after** secret-scan.
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
