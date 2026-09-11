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

SKY-026 Phase 5 implementation is on `main` via merged PR #252. A Main-only Light PR-state task, the
Phase-4 Medium session, and the Phase-3/Phase-5 Heavy sessions provide traceable route evidence. Heavy
used two concurrent non-overlapping Executor packages; natural defects returned to their owning
Executor and the same Tester passed the recheck. The digest and context map have distinct on-demand
roles, the unused checkpoint is removed, and current construction guidance uses SKY-026 only. Open
PR #253 owns the remaining review-process correction: implementation/fix sessions stop after publishing
their PR; Ali manually starts a separate fresh reviewer; that reviewer resolves and rechecks the
current target/base + PR-head integration pair directly from GitHub. Ali supplies the PR identity,
not hashes to shuttle between sessions. No production authority or live host is involved.

SKY-025 has a separate one-time migration issue: its P7 implementation/fix PRs were already merged
before the new pre-merge lifecycle. The active SKY-025 directive defines one read-only review of the
already-integrated P7 result; a P7 FIX opens a corrective PR and returns to the normal pre-merge path.

## Next Milestone

Ali manually starts a fresh separate review of open PR #253. The reviewer resolves the current Git
revision pair itself. If FIX, return the paste-ready prompt to the original fix session, update the same
PR, and review again fresh. If `ACCEPT SKY-026`, human-merge #253 while the reviewer-confirmed pair is
still current, then perform the bounded final closeout: update durable agent memory to the merged
accepted state, mark Phase 5 done, set `current_phase: 5`, archive the directive through the planning
lifecycle, refresh the roadmap, and keep authored merge human-only. The closeout does not automatically
trigger another acceptance review unless it introduces substantive implementation changes.
