---
date: 2026-09-10
time: 22:19:55
kind: session
title: SKY-026 Phase 4 continuity and token accounting
tier_touched: [T1]
grants: []
refs: [SKY-026, PR-249, PR-250, viettran-edgeAI/codex_workflow@6d9b06f73bee7f899001b0bb102c70529a24313f]
thread_status: open
---

# 2026-09-10 · session · SKY-026 Phase 4 continuity and token accounting

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (journal/README.md). Distillation happens at READ time, never here. -->

## What happened

Ali requested SKY-026 Phase 4 only. Main used the directive's Medium route with one persistent
Companion and Archivist assignments. No Senior Executor was justified because implementation and
verification stayed with Main. No production host, credential, grant, or T2/T3 action was touched.

The local branch initially started from `83760ca`. PR #249 had merged commit `495883b` into `main` ten
seconds before this session began, but local `main` had not fetched it. That commit reversed the earlier
continuity decision and made the six donor-style `agent_docs/` files an explicit Phase-4 requirement.
PR #250 first appeared DIRTY against GitHub; fetching `origin/main` exposed the concurrent decision.
Main merged current `origin/main` into the existing branch, discarded the conflicting no-`agent_docs`
assumptions, and kept PR #250 as the one review surface.

The donor repository was cloned to `/tmp/sky026-p4-donor`. Its current HEAD matched the directive's
pinned `6d9b06f73bee7f899001b0bb102c70529a24313f`. Main read the six `project_docs` templates, Medium/Heavy
closure contracts, Archivist contract, and deployment-token reporter/parser/tests.

## Actions and evidence

- Archivist populated stable `project_overview.md`, `project_core_tech.md`, and
  `project_structure.md`; Main populated progress, reusable decisions/lessons, and latest-session
  handoff. The set contains exactly six files and no donor bootstrap markers.
- Construction doctrine, Companion/Archivist roles, planning mechanics, and the construction runbook
  now enforce higher-authority conflict repair and the Main/stable-memory ownership split.
- Complete, paused, and blocked closure shapes each leave one latest-session next entry point.
- Digest, context map, and optional checkpoint remain Phase-5 evaluation candidates: recent episode
  view, routing/load-cost index, and disposable in-flight state respectively.
- The donor-derived reporter lives at `.agents/skills/deployment-token-report/`. It uses Codex rollout
  ancestry and recorded cached-input/input/output counts only; missing ancestry, first-commentary
  boundary, or incomplete evidence fails closed. No price is estimated.
- `codex debug prompt-input` exposed the project-local skill from `.agents/skills` on Codex 0.153.4.
- Focused verification passed: 13 Python memory/reporter tests and 46 construction shell checks.
- Full verification passed: 271 pytest tests, Ruff, strict mypy over 14 source files, the full
  pre-commit suite, and `git diff --check`.
- `bin/plan list` rendered SKY-026 at 4/5, still `in-progress`; owned digest/context renderers ran.

## Cold-start comparison

Two fresh ephemeral read-only Codex sessions were run without workers or Internet access.

- Path A read six `agent_docs/` files plus SKY-026: 7 files, 47,527 bytes, zero follow-up reads and
  zero extra Main wakeups. It recovered the trust/merge posture, Phase 4 complete on PR #250, and the
  Phase-5 continuation with no conflict.
- Path B read the generated digest, context map, and SKY-026: 3 files, 50,156 bytes, zero follow-up
  reads and one reported Main wakeup. It recovered the same current position and continuation.

This is one bounded comparison, not a universal benchmark. Path A used four more files but 2,629 fewer
bytes and supplied stable architecture/technology/structure/lesson context directly. Path B retained
distinct value for recent episodic/open-thread discovery and on-demand routing.

## Failures and corrections

- The first implementation followed stale local Phase-4 text and rejected `agent_docs/`; the fetched
  merged directive disproved it, so that design was removed before closure.
- The first Nix full-gate invocation could not write its user fetcher cache inside the workspace
  sandbox. It was rerun with the narrow approved Nix command prefix; the repository checks passed.
- The authority-boundary test initially compared wrapped Markdown blockquote text without removing
  continuation markers. The test normalization was corrected; the source documents were unchanged.
- This deployment's marker was emitted after Main's first commentary because the reporter contract did
  not exist at start. Closing accounting must therefore report the exact boundary limitation and must
  not reuse the later marker or a diagnostic total.

## Graveyard — tried and abandoned

- The stale no-`agent_docs` continuity design and directive-only handoff were abandoned after PR #249
  established the authoritative opposite decision.
- `.codex/skills/deployment-token-report/` was abandoned before commit because the installed harness
  did not discover project skills there; `.agents/skills/` was the verified repository surface.

## Follow-ups / open threads

- Ali must review and merge authored PR #250. Then execute SKY-026 Phase 5; no Phase-5 work occurred.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
