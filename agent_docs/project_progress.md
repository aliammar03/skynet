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
  overhaul plus the final review-process repair: every ACCEPT/FIX/BLOCKED verdict is now durable and
  the newest applicable verdict is authoritative.
- SKY-025 accepted progress remains P6/24 in repository state. Corrective P7 PR #254 contains the final
  route-source fail-closed fix and is ready for human merge after fresh acceptance. P8 is prepared and
  remains blocked until P7 is truthfully closed.

## Current Position

The normal lifecycle is deliberately small and ends in **one human merge**:

```text
implement/fix → one open PR → fresh review → durable verdict marker
→ newest verdict must be ACCEPT
→ Ali says "accepted" → bounded closeout on SAME PR
→ CI/final recheck → Ali human-merges that PR once
```

Every final reviewer verdict posts one machine-readable `skynet-acceptance:v1` marker with scope,
reviewed base, reviewed head, and verdict. The newest applicable marker wins. A newer FIX/BLOCKED or a
malformed newest marker blocks closeout even if an older ACCEPT exists for the same revisions.

Ali never carries hashes. The original session resolves review state itself before accepted closeout.
Post-ACCEPT closeout remains limited to directive/archive/planning state, Main-owned deployment-state
`agent_docs`, append-only journal closure evidence, and generator-owned closure views. Substantive
post-ACCEPT changes require fresh review.

On private GitHub Free, the final agent recheck and Ali's click-to-merge are not atomic. Prompt merge
reduces but does not remove that race window. No paid-plan requirement or manual SHA handling is part of
the workflow.

SKY-025 uses the same simple rule for corrective P7 and all P8+ PRs. The historical already-merged P7
path remains a one-time compatibility gate only; once a corrective P7 PR exists, that PR uses normal
open-PR review and never returns to the legacy path.

## Next Milestone

1. Merge accepted corrective P7 PR #254 first.
2. Fresh-review the repaired current head of PR #253 if following the lifecycle strictly; its older
   ACCEPT is stale and must not be reused.
3. Once both land, continue SKY-025 at P8 and record the P7 accepted/current-phase transition in the
   natural P8 PR as already planned.

No production authority or live host change is involved in these handoffs.
