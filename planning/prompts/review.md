---
summary: "Independently review a merged SKY-025 phase and publish only its verdict and next bounded packet."
---

# Review merged work and define the next packet

> Independent review prompt for the [phase handoff workflow](README.md). Follow the active SKY-025 directive.

As a fresh Astra Medium session, review the supplied SKY-025 implementation PR and any fix PRs.

1. Read AGENTS.md, planning/README.md, the active SKY-025 directive found by ID, its packet and
   disposition map if present. Confirm the selected model/effort. Use repository evidence rather
   than an implementation transcript; load relevant callers, contracts and tests as needed.
2. Verify through GitHub that every supplied implementation/fix PR merged into main. Record their
   URLs and actual merge SHAs, plus the current main SHA. If unmerged, stop with the missing
   prerequisite; do not accept a branch result as a merged phase.
3. Inspect the complete phase and fix diffs against the packet's starting revision, and the actual
   implementation on current main. Account for intervening commits affecting these surfaces.
   Check callers, failure handling, doctrine/runbooks and scope, not merely the PR summary.
   Run relevant checks independently; report commands and unavailable verification explicitly.
4. Choose ACCEPT, FIX, or BLOCKED against each exit criterion. CI green alone is insufficient.
   ACCEPT requires satisfied exits; FIX means concrete implementation defects with bounded repair;
   BLOCKED means missing evidence, access, or an unresolved decision prevents judgment. Do not
   silently waive an exit criterion. For a fix review, recheck the whole phase's affected exits.
5. Start a planning branch from the reviewed main SHA and publish the verdict in the directive's
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
   warrants a change; record the reason. Split oversized work into reviewed lettered slices.
7. Before publishing, recheck main. If it moved, inspect relevant changes and refresh affected
   checks/packet assumptions; record the final reviewed SHA. Commit, push, and open a planning PR
   to main. Do not implement repairs or the next phase, and never merge your PR.

Use title: `SKY-025 P<N> review: <ACCEPT|FIX|BLOCKED>`.
Use these compact PR body fields:

```text
Reviewed: <implementation/fix PR URLs and full merge SHAs>
Main reviewed: <full SHA>
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
