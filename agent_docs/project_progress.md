# Project Progress

> Compact derived state for agent intake. The active directive and accepted evidence decide project
> status; correct this file when they conflict.

## Goal

Reach full agent control safely: Git remains rebuildable truth, authored changes remain human-merged,
and each capability earns autonomy through recorded verification and rollback evidence.

## Overall Progress

- The constitution, trust tiers, GitOps loop, generated inventory, runbooks, directive lifecycle, and
  native SKY-026 construction model are established.
- SKY-026 is in progress. Phases 1–4 are accepted; Phase 5 implementation is merged in PR #252. Open
  PR #253 contains the final review-lifecycle correction plus the SKY-025 migration to that lifecycle.
- SKY-025 accepted progress is P6/24. P7 implementation/corrective work is already merged in #235,
  #236, #237 and #239 under the former workflow, so P7 has one bounded legacy integrated-main review
  remaining. P8 is prepared but not executable until P7 ACCEPT + closeout.

## Current Position

Open PR #253 makes external review operator-started and integration-aware: Ali names the PR; the fresh
reviewer resolves current target/base + PR-head revisions from GitHub, reviews that pair, rechecks both
before verdict, and invalidates ACCEPT if either moves. Ali never carries hashes between sessions.

SKY-025 is fully migrated for future work:

- P7 is the sole already-merged legacy exception;
- from P8 onward one numbered phase owns one open phase PR;
- internal slices remain on that same PR and are not separately merged;
- FIX stays on the same PR; ACCEPT precedes human merge;
- the active directive/map are lean current-state documents and P8A/P8B are already prepared.

## Next Milestone

1. Freshly review open PR #253. If FIX, repair the same PR and stop again. If `ACCEPT SKY-026`, human-
   merge it while the reviewer-confirmed integration pair remains current.
2. Run the bounded SKY-026 post-merge closeout/archive. That closeout hands current construction focus
   back to SKY-025.
3. Freshly review SKY-025 P7 using its one-time already-merged transition. No PR number or SHA is needed.
4. On P7 ACCEPT, bounded closeout records `current_phase: 7` and releases the prepared P8 packet.
5. Begin P8 on one open `SKY-025 P8` PR.

No production authority or live host change is involved in these handoffs.
