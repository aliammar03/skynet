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
  and recorded token accounting. Phase 5 implementation was merged in PR #252 and awaits fresh manual
  acceptance review after bounded review-handoff fix PR #253 is human-merged.

## Current Position

SKY-026 Phase 5 implementation is on `main` at
`61f805cf3116450ac42f1e72b88f59b08410da5c` via PR #252. A Main-only Light PR-state task, the Phase-4
Medium session, and the Phase-3/Phase-5 Heavy sessions provide traceable route evidence. Heavy used two
concurrent non-overlapping Executor packages; natural defects returned to their owning Executor and
the same Tester passed the recheck. The digest and context map have distinct on-demand roles, the
unused checkpoint is removed, and current construction guidance uses SKY-026 only. The remaining
review-process defect is bounded in PR #253: implementation/fix sessions must stop after publishing
their PR, while Ali manually starts acceptance review in a separate fresh chat. No production
authority or live host is involved.

## Next Milestone

Human-merge PR #253, then manually start a fresh independent SKY-026 review in a separate chat against
current `main`, merged PR #252, and merged PR #253. After `ACCEPT SKY-026`, perform the bounded final
close-out: mark Phase 5 done, set `current_phase: 5`, archive the directive through the planning
lifecycle, refresh the roadmap, and keep authored merge human-only.
