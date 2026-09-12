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
  PR #253 contains the final orchestration/review-lifecycle correction plus SKY-025 migration.
- SKY-025 accepted progress is P6/24. P7 implementation/corrective work is already merged in #235,
  #236, #237 and #239 under the former workflow, so P7 has one legacy integrated-main review remaining.
  P8 is prepared but not executable until P7 ACCEPT.

## Current Position

The canonical normal lifecycle is now:

```text
implement/fix → one open PR → fresh review → ACCEPT marker
→ Ali says "accepted" to original session → bounded closeout on SAME PR
→ CI/final recheck → Ali human-merges that PR once
```

The reviewer resolves/rechecks current target/base + PR-head itself immediately before verdict and posts
a machine-readable acceptance marker on ACCEPT. Ali never carries hashes. The original session fetches
and validates that marker itself before accepted closeout.

Post-ACCEPT closeout is allowed to change only directive/archive/planning state, Main-owned deployment-
state `agent_docs`, append-only journal closure evidence, and generator-owned closure views. It cannot
change source/runtime/config/tests/invariants/AGENTS/doctrine/runbooks/behavioral docs/stable memory or
other substantive work. The closeout commit moves PR head by design and is allowed; a reviewed-base
movement, unexplained head movement, or substantive post-ACCEPT delta invalidates ACCEPT.

On private GitHub Free, the final agent recheck and Ali's later click-to-merge are not atomic. Prompt
merge reduces but does not remove that race window. No paid-plan requirement or manual SHA handling is
part of the workflow.

SKY-025 is migrated accordingly:

- P7 is the sole already-merged legacy exception;
- P7 ACCEPT creates no standalone closeout PR; P8 PR opening bookkeeping records P7 accepted/current
  phase 7;
- a corrective P7 PR uses the normal open-PR lifecycle and never returns to legacy mode;
- from P8 onward one numbered phase owns one open phase PR, all slices stay on it, FIX stays on it,
  ACCEPT is followed by same-PR closeout, then that PR is human-merged once.

## Next Milestone

1. Freshly review open PR #253. The previous ACCEPT is stale because this workflow doctrine was changed
   substantively after that review.
2. If FIX, repair #253 and stop for another fresh review.
3. If ACCEPT, reviewer posts the acceptance marker; Ali returns to the original #253 session and says
   only `accepted`.
4. That session validates the marker, performs bounded SKY-026 closeout on #253 itself, proves the
   post-ACCEPT delta is closeout-only, waits for green CI, and hands #253 back for one human merge.
5. After #253 lands, review SKY-025 P7 using its one-time integrated-main transition.
6. On P7 ACCEPT, start the P8 PR; its opening bookkeeping records P7 accepted/current_phase 7, then P8
   implementation begins.

No production authority or live host change is involved in these handoffs.
