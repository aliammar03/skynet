---
summary: "Agent-agnostic construction: one session owns a change end to end on one PR, proves it with bin/check, and gets a Light or Full review before one human merge."
---

# Spoke · Construction

> How Skynet gets built. Any engine that can read [`AGENTS.md`](../../AGENTS.md), edit files, and run
> commands can do it. Construction grants **zero production authority**.
> Governed by [`../conventions.md`](../conventions.md).

Tags: **[testable]** = a deterministic gate asserts it; **[manual]** = holds by review.

## The loop

```text
read AGENTS.md + active directive → branch → implement → bin/check green → PR (tier + evidence)
   → review (Light or Full) → FIX? same PR, same loop → Ali merges once
```

1. **Intake.** Read `AGENTS.md` and the active directive in `planning/projects/`. Then read only the
   code, docs, and runbooks the change touches. There is no other mandatory memory. `[manual]`
2. **One change, one branch, one PR.** A directive phase is one PR. Reuse an open PR for the same
   phase instead of opening a second. `[manual]`
3. **Progress rides with the work.** The PR updates the directive's status block and roadmap row
   itself. Merge is the moment a phase is done; there is no separate closeout. `[manual]`
4. **Prove it.** Run `bin/check` (ruff, mypy, pytest, invariant gate) and paste the result in the PR.
   Add or update a test for every behavior the change adds or fixes. `[testable]`
5. **Stop at the PR.** The authoring session opens the PR and reports it. It never reviews or merges
   its own PR. `[manual]`

## Review tiers

The PR description names its tier. If any file or behavior in the Full list is touched, the PR is
Full. When unsure, it is Full. `[manual]`

| Tier | Applies to | Required before merge |
|---|---|---|
| **Light** | Read-only code (collectors, renderers, queries), refactors, deletions of dead code, tests, docs, planning, generated views | `bin/check` green + a PR description that teaches. Ali reviews the diff and merges; an agent review is optional. |
| **Full** | Anything that writes to production (T2 actuators, deploy, publish, Tofu/saved plans, snapshots, backup/restore, secrets handling); trust tiers, leash, `invariants.json`, gates, `.githooks/`; `AGENTS.md` §1–3/§6; `docs/system-design.md` | Light, plus: a failure-case test for every write path (the rollback or refusal is exercised, not just the happy path), live smoke evidence when the phase has a live step, and a **fresh-session review** that posts one verdict comment on the PR. |

**Fresh-session review** (Full). A separate session, on any engine, that did not author the change:

- reads the PR diff, its tests, and the directive phase's exit evidence;
- runs `bin/check` on the PR head;
- posts one PR comment ending in `Verdict: ACCEPT` or `Verdict: FIX`, with a paste-ready fix list;
- never edits the branch.

A FIX goes back to the authoring session on the same PR. A new push needs a new verdict. Ali merges
after the newest verdict is ACCEPT. No hashes are copied between sessions; the PR head is the
record. `[manual]`

## Delegation is the engine's business

An engine may split work across its own sub-agents, parallel workers, or none. Skynet defines no
roles, models, capsules, or worker counts, and no doctrine depends on one vendor's features.
Whatever the engine does internally, the output is the same: one PR, `bin/check` evidence, the tier's
review. `[manual]`

## Trust

- Construction is **unprivileged**: it runs as the `aliammar` account and holds no production
  credentials, root grants, or T2/T3 authority. Sub-agents inherit that and nothing more. `[manual]`
- Every engine configured for `aliammar` must refuse or human-gate `gh pr merge` and both
  `grant-root` spellings. `invariants.json` → `construction.engines` lists them and
  `skynet check` checks each engine's block in `nix/home/aliammar.nix`. Adding an
  engine means adding its entry. `[testable]`
- Production actions follow AGENTS.md §2 (plan loudly, run quietly) and the trust tiers, never this
  spoke. `[manual]`

## Evidence

- **Tests** live in `tests/`, run offline in seconds, and use `tmp_path` copies of repository truth.
  They cover behavior that protects something: parsing refusals, freshness gates, saved-plan policy,
  rollback, the invariant gate. No snapshot tests of prose. `[manual]`
- **Journal.** Write one `journal/` episode when something non-obvious happens (an incident, a dead
  end, a decision). Routine phases need none; the PR is the record. `[manual]`
- GitHub CI stays off. The local suite and the pre-commit hook are the gate. `[manual]`
