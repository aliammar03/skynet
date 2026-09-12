# Project Progress

> Compact derived state for agent intake. The active directive and accepted evidence decide project
> status; correct this file when they conflict.

## Goal

Reach full agent control safely: Git remains rebuildable truth, authored changes remain human-merged,
and each capability earns autonomy through recorded verification and rollback evidence.

## Overall Progress

- The constitution, trust tiers, GitOps loop, generated inventory, runbooks, directive lifecycle, and
  native SKY-026 construction model are established.
- **SKY-026 is complete.** Phases 1–5 are accepted and the directive is archived. PR #253 contains the
  accepted final workflow plus this bounded closeout and is awaiting one human merge.
- The corrective route-observation phase is accepted and merged. **The entity/cache phase is active**
  on its single numbered-phase branch/PR, with accepted repository progress recorded as 7/24.

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
path was a one-time migration bridge; corrective P7 returned to the normal open-PR lifecycle and is now
merged.

## Next Milestone

1. Human-merge accepted PR #253 after this closeout's final CI/base recheck passes.
2. Complete entity derivation/audit and rebuildable SQLite cache/query on the current phase PR.

No production authority or live host change is involved in these handoffs.
