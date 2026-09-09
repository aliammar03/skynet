---
summary: "Review a merged SKY-025 phase, repair bounded defects with Luna workers, and publish its verdict and next packet."
---

# Review merged work and define the next packet

> Independent review prompt for the [phase handoff workflow](README.md). Follow the active SKY-025 directive.

In a fresh session using the selected model and effort, review the complete numbered SKY-025 phase, including all its
implementation slice PRs and any fix PRs. Do not run independent acceptance reviews of slices.

1. Read AGENTS.md, planning/README.md, the active SKY-025 directive found by ID, its packet and
   disposition map if present. Record the selected model/effort when available; review is model-agnostic
   and does not require a particular model or effort. Use repository evidence rather
   than an implementation transcript; load relevant callers, contracts and tests as needed.
2. Verify through GitHub that every supplied implementation/fix PR merged into main. Record their
   URLs and actual merge SHAs, plus the current main SHA. If unmerged, stop with the missing
   prerequisite; do not accept a branch result as a merged phase.
   Confirm every slice of the numbered phase is implemented; otherwise return the same-phase
   execution continuation without issuing a phase verdict or releasing the next phase.
   Create an isolated review branch from that main SHA before making any repairs or planning edits.
3. Inspect the complete phase and fix diffs against the packet's starting revision, and the actual
   implementation on current main. Account for intervening commits affecting these surfaces.
   Check callers, failure handling, doctrine/runbooks and scope, not merely the PR summary.
   Run relevant checks independently; report commands and unavailable verification explicitly.
   Fix bounded defects within the reviewed phase directly in the review branch. Use Luna High
   workers for scoped implementation, tests and repetitive edits, and Luna Medium for bounded
   inspection; keep at most two helpers and retain judgment/integration with the reviewer.
   Inspect every worker diff and recheck the complete phase's affected exits after repairs.
   Existing live/grant boundaries still apply; review alone does not grant production access.
4. Choose ACCEPT, FIX, or BLOCKED against each exit criterion. CI green alone is insufficient.
   ACCEPT requires satisfied exits; FIX means concrete implementation defects with bounded repair;
   BLOCKED means missing evidence, access, or an unresolved decision prevents judgment. Do not
   silently waive an exit criterion. ACCEPT may include reviewer-authored repairs that pass those
   checks: identify their commit(s) and publish them with the verdict. Acceptance and the next
   packet take effect when Ali merges that combined PR; no additional review session is required
   for those verified repairs. Use FIX only for unresolved defects requiring a separate packet.
5. Publish the verdict from the review branch in the directive's
   existing status/progress area, with links and compact evidence. Follow its journal requirements.
   Keep one current actionable packet and preserve prior evidence in git/journal:
   - ACCEPT: update accepted progress, map and roadmap as needed, then flesh out only the next
     1–2h packet. At G1–G6 reconsider and prune/reorder the remaining roadmap. After the final
     phase, follow the completion/archive gate; do not invent another phase.
   - FIX: leave accepted progress unchanged; write only a bounded fix packet and its checks.
   - BLOCKED: leave accepted progress unchanged; record the blocker, owner and evidence/decision
     needed to resume. Do not release a next implementation packet.
6. Each released packet specifies goal, exact files/surfaces, interfaces, exclusions, recommended
   execution model/effort, optional scoped Luna assignments, check commands and expected results,
   live/grant boundaries, and exit criteria. Use the phase table's recommendation unless evidence
   warrants a change; record the reason. Split oversized work into implementation slices;
   the execution lead details the remaining slices and review covers the whole numbered phase.
7. Before publishing, recheck main. If it moved, inspect relevant changes and refresh affected
   checks/packet assumptions; record the final reviewed SHA. Commit, push, and open a review PR
   to main, including any verified repairs and planning updates. Do not implement the next phase,
   and never merge your PR.

Use title: `SKY-025 P<N> review: <ACCEPT|FIX|BLOCKED>`.
Use these compact PR body fields:

```text
Reviewed: <implementation/fix PR URLs and full merge SHAs>
Main reviewed: <full SHA>
Reviewer repairs: <commit(s), fixes and validation; or none>
Verdict: <ACCEPT | FIX | BLOCKED>
Evidence: <exit criterion → independent check/result; unavailable checks>
Findings: <concrete defects with file references, or none>
Released packet: <next phase/slice or fixes; model/effort; or none if blocked/final>
Checkpoint decisions: <G checkpoint changes and reasons, if applicable>
Handoff: after Ali merges this planning PR, start a new <assigned model/effort> task:
Read planning/prompts/execute.md and execute SKY-025 <released packet>.
```

For BLOCKED, replace the execution handoff with the required unblock action and review invocation.
For final acceptance, report completion instead. Return the PR URL, verdict and handoff. If
publishing is unavailable, preserve the branch/commit and PR body and report the access blocker.
