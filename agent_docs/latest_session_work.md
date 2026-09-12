# Latest Session Work

> Derived closure handoff. The active directive, current Git/PR state, and accepted evidence win any
> conflict; Main updates this at implementation-ready, paused/blocked, and accepted same-PR closeout.

## Detailed Current State

SKY-026 Phases 1–4 are accepted. Phase 5 implementation was merged in #252 under the old lifecycle.
Open PR #253 owns the final construction/review workflow correction and SKY-025 migration. SKY-026
remains `in-progress` pending a fresh review of the current #253 state.

The earlier ACCEPT for #253 is intentionally stale because the lifecycle doctrine was substantively
changed afterward at Ali's request. This workflow overhaul itself therefore requires one fresh review
before it can use its new accepted-closeout path.

SKY-025 accepted progress remains P6/24. Historical P7 implementation/fix PRs #235, #236, #237 and
#239 are already merged under the former workflow, so P7 has one legacy integrated-main review left.
P8 is prepared and becomes executable on truthful P7 ACCEPT.

## Session Changes

The normal authored lifecycle is now deliberately one-PR/one-merge:

```text
implement/fix → open PR → fresh review → ACCEPT marker
→ Ali tells original session "accepted"
→ bounded closeout on SAME PR → CI/final recheck → Ali merges once
```

- Reviewer resolves/rechecks target/base + PR-head immediately before verdict. On ACCEPT it posts a
  machine-readable `skynet-acceptance:v1` marker to the PR conversation. Ali never copies or compares
  hashes.
- The original implementation/fix session retrieves and validates the marker itself before closeout.
- Allowed post-ACCEPT Git changes are only directive/archive/planning state, Main-owned
  `project_progress.md` / `project_diary.md` / `latest_session_work.md`, append-only journal closure
  evidence, and generator-owned closure views caused by the state transition.
- Source/runtime/config/tests/invariants/AGENTS/doctrine/runbooks/behavioral docs/stable memory or any
  other substantive post-ACCEPT change makes ACCEPT stale and requires fresh review.
- The bounded closeout commit moves PR head by design and is allowed if Main proves the marker-head..
  final-head delta is closeout-only. Reviewed-base movement or unexplained head movement still makes
  ACCEPT stale.
- There is no normal closeout-only PR and no automatic second review after a valid closeout-only delta.
- Private GitHub Free still leaves a non-atomic race between the last agent recheck and Ali clicking
  Merge. Prompt merge minimizes but does not eliminate it.
- Archivist stable-doc/memory work is pre-review only. Accepted closeout is Main-owned bookkeeping.
- SKY-025 normal phases use this same lifecycle. Historical P7 ACCEPT creates no bookkeeping-only PR;
  the P8 PR begins by recording P7 accepted/current_phase 7 before P8 implementation.
- SKY-026 directive was pruned to current architecture/state instead of retaining obsolete lifecycle
  history.

## Verification

- The substantive one-merge workflow overhaul passed GitHub Actions `checks` run **#649**:
  focused lifecycle contracts **14 passed**; full pytest **286 passed, 1 skipped**; Ruff clean; mypy
  clean across **14 source files**; packaged Nix checks passed.
- Hard invariants and `git diff --check` passed. Entity/digest/DNS-revert/compose-rollback/certificate-
  selector/OpenTofu-rollback/PVE-snapshot/provisioning-truth/construction/nightly-automerge/nightly-
  sequence gates all passed.
- This handoff-only evidence refresh changes no workflow behavior. Review handoff is valid only when
  GitHub checks on the current PR head are green; do not review a red or pending head.
- No production endpoint, credential, root grant, service/timer, inventory, or live infrastructure
  write is involved.

## Pending Work and Blockers

- No implementation work remains before review if current-head CI is green.
- PR #253 requires one fresh external review because the previous ACCEPT predates this substantive
  workflow change.
- After new ACCEPT, Ali returns to the original #253 implementation/fix session and says only
  `accepted`. That session closes out #253 on the same PR and hands it back for one human merge.
- SKY-025 P8 remains blocked only until the one-time P7 integrated-main review returns ACCEPT.

## Next Entry Point

With current-head CI green, Ali starts a **new fresh review of open PR #253**. FIX returns to the same
implementation session. On ACCEPT, the reviewer posts the PR acceptance marker and Ali tells the
original session only `accepted`; that session performs bounded closeout on #253 itself and stops with
the same PR ready for one human merge. After #253 lands, run the one-time SKY-025 P7 review; on P7
ACCEPT, begin P8 and record the P7 state transition as opening bookkeeping in the P8 PR.
