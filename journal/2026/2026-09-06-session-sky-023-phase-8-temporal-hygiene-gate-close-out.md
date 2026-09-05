---
date: 2026-09-06
time: 01:13:21            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: SKY-023 Phase 8 temporal-hygiene gate close-out
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-023]         # SKY-###, PR #NNN, ADR NNNN, hosts — anything to cross-link
thread_status: none     # none | open | resolved | unknown; digest shows only explicit open
---

# 2026-09-06 · session · SKY-023 Phase 8 temporal-hygiene gate close-out

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (SKY-006 / journal/README.md). Distillation happens at READ time, never here. -->

## What happened
Verified that Phase 7 merged as `98cc9fb`, fast-forwarded local `main`, and created
`test/sky-023-p8-temporal-hygiene`. This was T1 repository work only: no infrastructure command,
credential access, T2 write, or root grant ran.

Added `tests/temporal-hygiene-test.sh`. It scans current-authority docs, runbooks, live scripts and
entry points, OpenTofu, Nix, hosts, compose/config, and authoring templates. It excludes generated
docs, history, ADRs, planning, journal, and tests. The hard rule rejects numeric `SKY-NNN` references;
the sole exact exception is `bin/plan`'s `SKY-000` template substitution. The narrative rule rejects
only `used to`, `previously`, `formerly`, `retired`, `replaced`, `introduced by`, `validated during`,
and numeric directive-phase notation.

The test creates temporary fixtures for numeric directive provenance, historical narration, and a
current import compatibility rationale. Initial execution found directive comments in
`compose/arcane-manager/.env.git` and `compose/silly/.env.git`, plus two wording collisions:
"what this replaced" in the doctrine and "may be used to" in the Caddy formatting instruction.
All four were rewritten to current-state wording; no allowlist was added.

Wired the test to `.githooks/pre-commit` and the PR checks workflow. Updated the docs and scripts
conventions plus the runbook and script templates with the finished-artifact rule.

## Actions & outcomes
- `bash tests/temporal-hygiene-test.sh` → 5 passed, 0 failed.
- `bash .githooks/pre-commit` → all deterministic checks passed, including the new temporal gate.
- `git diff --check` → no whitespace errors.

## Graveyard — tried & abandoned
Negative results are memory too. Anything attempted that did NOT work — and *why* — so a future
cold agent doesn't re-walk the dead end. Leave a single "— nothing abandoned —" line only if the
episode genuinely tried no path it dropped.

- Broad ban on `legacy`, `imported`, `compatibility`, or `deprecated` → abandoned because those words
  can state a present provider or state constraint; the gate uses only high-signal archaeology phrases.
- Allowlisting the initial collisions → abandoned because each could be rewritten more clearly as a
  current-state rule or instruction.

## Follow-ups / open threads
- Continue SKY-023 at Phase 9; read [[SKY-023-progress]], verify reality, and execute only that phase.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
