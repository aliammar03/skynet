---
date: 2026-09-23
time: 16:17:46            # local HH:MM:SS; orders same-day episodes in the digest
kind: decision          # session | incident | decision
title: Process overhaul: tests back, review tiers, agent-agnostic construction
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-025, SKY-026, ADR 0007]  # SKY-###, PR #NNN, ADR NNNN, hosts — anything to cross-link
thread_status: open     # none | open | resolved | unknown; digest shows only explicit open
resolves: [2026-09-06-session-sky-025-phase-handoffs, 2026-09-07-session-sky-025-full-phase-review-boundary, 2026-09-07-session-sky-025-p1-independent-review, 2026-09-07-session-sky-025-p1-repository-map-and-routing, 2026-09-07-session-sky-025-p2-independent-review, 2026-09-07-session-sky-025-p2-package-local-cli, 2026-09-07-session-sky-025-p3a-context-budget-approval, 2026-09-07-session-sky-025-p3a-isolated-core-collector, 2026-09-08-session-sky-025-p3-combined-re-review, 2026-09-08-session-sky-025-p3-freshness-and-process-fixes, 2026-09-08-session-sky-025-p3-independent-review, 2026-09-08-session-sky-025-p3b-default-collection-and-freshness, 2026-09-08-session-sky-025-p4a-network-observations, 2026-09-08-session-sky-025-p4b-operate-token-acl-snapshots, 2026-09-09-session-sky-025-p4-combined-independent-review, 2026-09-09-session-sky-025-p5-combined-independent-review, 2026-09-09-session-sky-025-p5-reviewer-repairs-and-live-reads, 2026-09-09-session-sky-025-p5a-pbs-inventory, 2026-09-09-session-sky-025-p5b-docker-inventory, 2026-09-09-session-sky-025-p6-combined-review-and-live-reads, 2026-09-09-session-sky-025-p6a-dns-python-collection, 2026-09-09-session-sky-025-p6b-ii-opnsense-offline-mirror-parser, 2026-09-09-session-sky-025-p6b-opnsense-live-python-collection, 2026-09-09-session-sky-025-p6c-digest-supersede-stale-await-merge-follow-up, 2026-09-09-session-sky-025-p6c-review-fix-regenerate-stale-agent-and-planning-context, 2026-09-09-session-sky-025-p7a-omada-python-collection, 2026-09-09-session-sky-025-p7b-certificate-and-static-route-observations, 2026-09-09-session-sky-025-p7c-bounded-python-reconnaissance, 2026-09-10-session-sky-025-p7-route-and-recon-review-fixes, 2026-09-10-session-sky-026-p1-transplant-construction-orchestration-contract, 2026-09-10-session-sky-026-permission-ergonomics-fix, 2026-09-10-session-sky-026-phase-4-continuity-and-token-accounting, 2026-09-11-session-sky-026-phase-5-external-review-evidence-fix, 2026-09-12-session-sky-026-closeout-invalidated-by-lifecycle-test, 2026-09-13-decision-sky-025-repository-test-and-github-ci-embargo]  # superseded: P1-P10 merged and accepted, SKY-026 archived, test embargo lifted
---

# 2026-09-23 · decision · Process overhaul: tests back, review tiers, agent-agnostic construction

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (journal/README.md). Distillation happens at READ time, never here. -->

## What happened
Ali asked for a review of the Python transition, then approved an overhaul of the plan and the
construction process. Repository state found at the start (main @ f8072b3):

- SKY-025 at P10/24; Python ~7.0k lines in 19 modules, ruff + strict mypy clean.
- Shell ~2.3k lines in 44 files; ~20 were pure forwarders to `bin/skynet` kept alive until P22.
- Zero tests: P8 (PR #255) deleted 71 test files (~6k lines) under the SKY-025 test/CI embargo.
- Markdown about the work (journal 9.4k, planning 6.5k lines) exceeded the Python itself. P10 added
  764 code lines and 429 process lines, with three journal entries per phase.
- Progress was tracked in four places: the directive, planning/sky-025-map.md,
  agent_docs/project_progress.md (+ diary + latest_session_work), and the journal.
- Construction doctrine (284 lines) was Codex-specific: six named roles in .codex/agents/*.toml with
  pinned models, capsules, a token-report skill, an acceptance-marker protocol, and same-PR closeout.

Decisions Ali made in chat: bring back a minimal pytest suite, add review tiers, make construction
agent-agnostic, collapse progress tracking, make the process simple.

## Actions & outcomes
- tests/: 7 files, 65 offline tests (credentials refusals across 5 parsers, freshness gate incl.
  tamper per observation, cache atomicity, entity law + audit, deploy verify input refusals,
  invariant gate pass + 3 violation cases, CLI) → `pytest` 65 passed in ~2s.
- bin/check (ruff, mypy, pytest, invariant gate) → OK. Pre-commit now also runs pytest.
- check-invariants §6 rewritten: data-driven `construction.engines` in invariants.json; each engine's
  block in nix/home/aliammar.nix must carry the merge/grant-root refusals.
- Deleted .codex/ (config + 6 roles), .agents/skills/deployment-token-report, runbooks/
  construction-delegation.md, agent_docs/ (6 files), planning/sky-025-map.md.
- construction.md rewritten (~80 lines): one loop, Light/Full tiers, fresh-session verdict comment
  for Full, delegation left to the engine. AGENTS.md §0/§3/§4/§6, system-design merge gate/autonomy,
  conventions hub + git/layout/scripts spokes, actuators, memory design, planning README/TEMPLATE,
  prompts rewritten to match.
- SKY-025 directive rewritten: P11–P17 replace P11–P24; "Done means" checklist; shell allowlist and
  delete list; census table folded in from the map; status block is the only tracker.
- ADR 0007 records the decision.

## Graveyard — tried & abandoned
- Editing nix/home/aliammar.nix to make Claude Code and opencode *deny* (not ask) `gh pr merge` and
  `grant-root` → blocked by the authoring harness as self-modification of agent permissions. Left
  unchanged. The invariant gate checks codex (forbidden) and claude-code (ask/deny) only; opencode
  gates `gh pr merge` with ask but has no grant-root rule, so it is not yet a listed engine.
- Running mypy over tests/ → the interpreter mypy used could not import pytest; kept mypy on src/.
- Porting check-invariants.sh to Python in this change → deferred to Phase 12 (Full tier).

## Follow-ups / open threads
- Ali: add grant-root deny/ask rules for opencode in nix/home/aliammar.nix, then list it in
  invariants.json construction.engines.
- Nix changes (devshell + base python3.withPackages pytest) were not built in the authoring
  container (no nix); verify with `nix develop` and a rebuild on the ops VM.
