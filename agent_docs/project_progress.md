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
reviewer resolves current target/base + PR-head revisions from GitHub, reviews that pair, and rechecks
both immediately before verdict. ACCEPT approves that exact last-verified pair. If either revision is
known to move before merge, ACCEPT is stale and fresh review is required. Ali never carries hashes
between sessions.

On the intended private GitHub Free setup, no repository mechanism in the current workflow can
mechanically or atomically freeze the reviewed base/head pair between the reviewer's final recheck and
Ali's later human merge. Prompt merge after ACCEPT reduces but does not eliminate that race window.
This limitation is explicit; SKY-026 does not require a paid GitHub upgrade, manual SHA comparison, or
a helper that falsely claims atomicity. A future enforceable up-to-date-branch/atomic mechanism may
strengthen the contract without being a prerequisite today.

SKY-025 is fully migrated for future work:

- P7 is the sole already-merged legacy exception;
- any corrective P7 PR created after a legacy FIX uses the normal open-PR review mode, never the legacy
  integrated-main mode;
- from P8 onward one numbered phase owns one open phase PR;
- internal slices remain on that same PR and are not separately merged;
- FIX stays on the same PR; ACCEPT precedes human merge;
- the active directive/map are lean current-state documents and P8A/P8B are already prepared.

## Next Milestone

1. Freshly review open PR #253. If FIX, repair the same PR and stop again. If `ACCEPT SKY-026`, merge it
   promptly unless a repository/PR change is known; any known movement of the reviewed base or head
   makes the verdict stale and requires fresh review. The private-GitHub-Free race window between the
   reviewer's final recheck and the later merge remains an explicit limitation.
2. Run the bounded SKY-026 post-merge closeout/archive. That closeout hands current construction focus
   back to SKY-025.
3. Freshly review SKY-025 P7 using its one-time already-merged transition. No PR number or SHA is needed.
4. On P7 ACCEPT, bounded closeout records `current_phase: 7` and releases the prepared P8 packet.
5. Begin P8 on one open `SKY-025 P8` PR.

No production authority or live host change is involved in these handoffs.
