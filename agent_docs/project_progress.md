# Project Progress

> Compact derived state for agent intake. The active directive and accepted evidence decide project
> status; correct this file when they conflict.

## Goal

Reach full agent control safely: Git remains rebuildable truth, authored changes remain human-merged,
and each capability earns autonomy through recorded verification and rollback evidence.

## Overall Progress

- The constitution, trust tiers, GitOps loop, generated inventory, runbooks, directive lifecycle, and
  native SKY-026 construction model are established.
- SKY-026 remains in progress. Phases 1–4 are accepted. Open PR #253 contains the Phase-5 workflow
  overhaul plus a repair for the lifecycle tests that failed during the first accepted-closeout attempt.
- That earlier ACCEPT is now stale because repairing those tests was a substantive post-ACCEPT change.
  SKY-026 has therefore returned to implementation-ready / pending fresh review rather than remaining
  archived prematurely.
- SKY-025 accepted progress remains P6/24. P7 implementation/corrective work is already merged in #235,
  #236, #237 and #239 under the former workflow, so P7 has one legacy integrated-main review remaining.
  P8 is prepared but not executable until P7 ACCEPT.

## Current Position

The canonical normal lifecycle is:

```text
implement/fix → one open PR → fresh review → ACCEPT marker
→ Ali says "accepted" to original session → bounded closeout on SAME PR
→ CI/final recheck → Ali human-merges that PR once
```

The reviewer resolves/rechecks current target/base + PR-head itself immediately before verdict and posts
a machine-readable acceptance marker on ACCEPT. Ali never carries hashes. The original session fetches
and validates that marker itself before accepted closeout.

The first real #253 closeout validated the marker and changed only sanctioned bookkeeping, but final CI
then exposed that `tests/test_agent_docs.py` still hard-coded SKY-026's active `planning/projects/`
location. That test failed exactly when closeout moved the directive to `planning/archive/`. The repair
now selects whichever one of the active/archive paths exists and asserts there is exactly one location.
Because the test itself is a substantive surface, the previous ACCEPT became stale by doctrine.

Post-ACCEPT closeout remains limited to directive/archive/planning state, Main-owned deployment-state
`agent_docs`, append-only journal closure evidence, and generator-owned closure views. Source/runtime/
config/tests/invariants/AGENTS/doctrine/runbooks/behavioral docs/stable memory or any other substantive
post-ACCEPT change requires a fresh review.

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

1. Finish green CI on the repaired open PR #253.
2. Run one fresh external review of that current PR head. The prior ACCEPT must not be reused.
3. If FIX, repair #253 and stop for another fresh review.
4. If ACCEPT, reviewer posts a new acceptance marker; Ali returns here and says only `accepted`.
5. The original session then reruns bounded closeout on the same PR and hands #253 back for one human
   merge if the closeout-only delta and final CI are green.
6. After #253 lands, run the one-time SKY-025 P7 integrated-main review, then start P8 on P7 ACCEPT.

No production authority or live host change is involved in these handoffs.
