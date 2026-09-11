# Project Progress

> Compact derived state for agent intake. The active directive and accepted evidence decide project
> status; correct this file when they conflict.

## Goal

Reach full agent control safely: Git remains rebuildable truth, authored changes remain human-merged,
and each capability earns autonomy through recorded verification and rollback evidence.

## Overall Progress

- The operating constitution, trust tiers, GitOps loop, generated inventory, runbooks, and directive
  lifecycle are established.
- Several infrastructure and engine directives remain active; [`planning/README.md`](../planning/README.md)
  is the generated roadmap for their exact state.
- SKY-026 is in progress. Phases 1–4 established Main-directed routes, native specialist roles,
  batching, repair ownership, independent verification, compact agent memory, Archivist closure,
  and recorded token accounting. Phase 5 implementation was merged in PR #252; bounded review-handoff
  fix PR #253 must receive fresh manual acceptance review while still open, before human merge.

## Current Position

SKY-026 Phase 5 implementation is on `main` at
`61f805cf3116450ac42f1e72b88f59b08410da5c` via PR #252. A Main-only Light PR-state task, the Phase-4
Medium session, and the Phase-3/Phase-5 Heavy sessions provide traceable route evidence. Heavy used two
concurrent non-overlapping Executor packages; natural defects returned to their owning Executor and
the same Tester passed the recheck. The digest and context map have distinct on-demand roles, the
unused checkpoint is removed, and current construction guidance uses SKY-026 only. The remaining
review-process defect is bounded in open PR #253: implementation/fix sessions must stop after publishing
their PR, while Ali manually starts acceptance review in a separate fresh chat against that open PR.
No production authority or live host is involved.

## Next Milestone

Manually review open PR #253 in a fresh separate chat. If FIX, return the paste-ready prompt to the
original fix session, update the same PR, and review again fresh. If `ACCEPT SKY-026`, human-merge #253,
then perform the bounded final closeout: update durable agent memory to the merged accepted state, mark
Phase 5 done, set `current_phase: 5`, archive the directive through the planning lifecycle, refresh the
roadmap, and keep authored merge human-only. The closeout does not automatically trigger another
acceptance review unless it introduces substantive implementation changes.
