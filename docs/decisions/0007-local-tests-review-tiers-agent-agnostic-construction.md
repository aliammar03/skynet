# ADR 0007 — Local tests, Light/Full review tiers, agent-agnostic construction

- **Status:** accepted
- **Date:** 2026-09-23
- **Supersedes:** the SKY-025 repository-test embargo; the SKY-026 Main-worker construction doctrine

## Context

During SKY-025 the repository test suite was deleted under a test/CI embargo, while every phase paid a
fixed review cost: a machine-readable acceptance marker, a same-PR closeout, three journal entries,
and updates to four progress trackers. Construction doctrine named six Codex roles with pinned models.
The remaining SKY-025 work is the write paths (deploy, Tofu, backup, restore), where an untested
"success" does real damage, and AGENTS.md makes failure-tested rollback the price of autonomy.

## Decision

1. **Tests come back, locally.** A small offline pytest suite in `tests/` runs through `bin/check`
   and the pre-commit hook. GitHub CI stays off. Behavior that protects something has a test; every
   write path gets a failure-case test.
2. **Two review tiers.** Light (read-only code, refactors, deletions, tests, docs, planning): green
   `bin/check` and Ali's merge. Full (production writes, trust boundary, gates, this contract): also
   failure-case tests, live smoke evidence, and a fresh-session verdict comment. When unsure, Full.
3. **Agent-agnostic construction.** One session owns a change on one PR. Delegation is the engine's
   business. Every engine configured for `aliammar` must refuse or human-gate PR merge and root
   grants; `invariants.json` lists the engines and the gate checks them.
4. **One progress tracker.** The active directive's status block, updated by the phase PR itself.
   Merge is completion; there is no closeout step.

## Consequences

- `.codex/agents/`, the token-report skill, `agent_docs/`, and the SKY-025 map are deleted.
- SKY-025 shrinks from 14 remaining phases to 7 larger ones, ordered by risk.
- Human merge, the auto-approve list (still empty), trust tiers, and the self-leash are unchanged.
- The evidence for any future A4 promotion is a failure-case test plus recorded live evidence.
