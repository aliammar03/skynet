# Project Progress

> Compact derived state for agent intake. The active directive and accepted evidence decide project
> status; correct this file when they conflict.

## Goal

Reach full agent control safely: Git remains rebuildable truth, authored changes remain human-merged,
and each capability earns autonomy through recorded verification and rollback evidence.

## Overall Progress

- The constitution, trust tiers, GitOps loop, generated inventory, runbooks, directive lifecycle, and
  native SKY-026 construction model are established.
- SKY-026 is externally accepted and its bounded same-PR closeout is complete on PR #253. All five
  phases are accepted; the directive is archived in this PR and now awaits the single human merge that
  publishes the accepted implementation plus closeout bookkeeping to `main`.
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

PR #253 exercised that handoff for SKY-026: the reviewer ACCEPT marker matched the then-current base and
head, after which Main changed only the sanctioned closure-bookkeeping surfaces on the same PR. No
source/runtime/config/tests/invariants/AGENTS/doctrine/runbooks/behavioral docs/stable memory or other
substantive work was added after ACCEPT.

Post-ACCEPT closeout is allowed to change only directive/archive/planning state, Main-owned deployment-
state `agent_docs`, append-only journal closure evidence, and generator-owned closure views. The
closeout commit moves PR head by design; a reviewed-base movement, unexplained head movement, or
substantive post-ACCEPT delta invalidates ACCEPT.

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

1. Human-merge accepted PR #253 once, provided the final closeout head remains green and the target base
   has not moved from the reviewer-approved base.
2. After #253 lands, run the one-time SKY-025 P7 integrated-main review.
3. On P7 ACCEPT, start the P8 PR; its opening bookkeeping records P7 accepted/current_phase 7, then P8
   implementation begins.

No production authority or live host change is involved in these handoffs.
