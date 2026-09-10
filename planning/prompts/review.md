---
summary: "Independently review a merged SKY-025 phase and either accept it with the next packet or return one paste-ready fix prompt — the reviewer never repairs."
---

# Review merged work and define the next packet

> Independent review prompt for the [phase handoff workflow](README.md). Follows the active SKY-025
> directive and the review model in [`../../docs/conventions/construction.md`](../../docs/conventions/construction.md):
> the reviewer never modifies the implementation.

In a fresh session using the selected model and effort, review the complete numbered SKY-025 phase, including all its
implementation slice PRs and any fix PRs. Do not run independent acceptance reviews of slices.

1. Read AGENTS.md, planning/README.md, the active SKY-025 directive found by ID, its packet and
   disposition map if present. Record the selected model/effort when available; review is model-agnostic
   and does not require a particular model or effort. Use repository evidence rather
   than an implementation transcript; load relevant callers, contracts and tests as needed. Read-only
   Investigator workers may gather evidence, but the reviewer owns the verdict.
2. Verify through GitHub that every supplied implementation/fix PR merged into main. Record their
   URLs and actual merge SHAs, plus the current main SHA. If unmerged, stop with the missing
   prerequisite; do not accept a branch result as a merged phase.
   Confirm every slice of the numbered phase is implemented; otherwise return the same-phase
   execution continuation without issuing a phase verdict or releasing the next phase.
   For an ACCEPT or BLOCKED verdict, create an isolated review branch from that main SHA before
   making any planning edits. A FIX verdict makes no repository changes at all.
3. Inspect the complete phase and fix diffs against the packet's starting revision, and the actual
   implementation on current main. Account for intervening commits affecting these surfaces.
   Check callers, failure handling, doctrine/runbooks and scope, not merely the PR summary.
   Run relevant checks independently; report commands and unavailable verification explicitly.
   **Do not modify the implementation and do not author repair commits** — the reviewer never repairs
   its own findings. Existing live/grant boundaries still apply; review alone grants no production access.
4. Choose ACCEPT, FIX, or BLOCKED against each exit criterion. CI green alone is insufficient.
   ACCEPT requires satisfied exits; FIX means one or more concrete, fixable implementation defects;
   BLOCKED means missing evidence, access, or an unresolved decision prevents judgment. Do not
   silently waive an exit criterion. There is no reviewer-authored-repair acceptance path: a phase
   with a fixable defect is FIX, never ACCEPT.
5. Act on the verdict:
   - **ACCEPT** — publish the verdict from the review branch in the directive's existing
     status/progress area, with links and compact evidence, and follow its journal requirements.
     Update accepted progress, map and roadmap as needed, then flesh out only the next 1–2h packet.
     At G1–G6 reconsider and prune/reorder the remaining roadmap. After the final phase, follow the
     completion/archive gate; do not invent another phase.
   - **BLOCKED** — publish from the review branch: leave accepted progress unchanged and record the
     blocker, owner and the evidence/decision needed to resume. Do not release a next packet.
   - **FIX** — make no commit and no PR. Your entire final response is **only** one fenced paste-ready
     fix prompt for the original implementation session (structure below). Leave accepted progress
     unchanged. The original session fixes and lands a bounded fix PR; after it merges, a fresh
     independent reviewer reviews the complete phase again. Repeat until ACCEPT.
6. Each released (ACCEPT) packet specifies goal, exact files/surfaces, interfaces, exclusions, recommended
   Main model/effort, check commands and expected results, live/grant boundaries, and exit criteria.
   Worker routing, capsules, ownership, batching, verification and repair follow
   [`../../docs/conventions/construction.md`](../../docs/conventions/construction.md); do not restate
   a second orchestration system. Use the phase table's recommendation unless evidence warrants a
   change; record the reason. Split oversized work into implementation slices; Main details the
   remaining slices and review covers the whole numbered phase.
7. For ACCEPT/BLOCKED, before publishing recheck main. If it moved, inspect relevant changes and
   refresh affected checks/packet assumptions; record the final reviewed SHA. Commit, push, and open a
   review PR to main with the planning updates. Do not implement the next phase, and never merge your PR.

## ACCEPT or BLOCKED review PR

Use title: `SKY-025 P<N> review: <ACCEPT|BLOCKED>`.
Use these compact PR body fields:

```text
Reviewed: <implementation/fix PR URLs and full merge SHAs>
Main reviewed: <full SHA>
Verdict: <ACCEPT | BLOCKED>
Evidence: <exit criterion → independent check/result; unavailable checks>
Findings: <concrete defects with file references, or none>
Released packet: <next phase/slice; model/effort; or none if blocked/final>
Checkpoint decisions: <G checkpoint changes and reasons, if applicable>
Handoff: after Ali merges this planning PR, start a new <assigned model/effort> task:
Read planning/prompts/execute.md and execute SKY-025 <released packet>.
```

For BLOCKED, replace the execution handoff with the required unblock action and review invocation.
For final acceptance, report completion instead. Return the PR URL, verdict and handoff. If
publishing is unavailable, preserve the branch/commit and PR body and report the access blocker.

## FIX response

On FIX, emit **only** this block, populated with real findings — no preamble, no findings list or
prose outside it:

```text
Continue the original SKY-025 implementation session and fix the independent review findings below.
Do not redesign unrelated work and do not self-accept the phase.

Review findings:
- <specific defect + evidence/reference>

Required fixes:
- <bounded required outcome>

Verification required:
- <specific affected tests/gates; run the relevant full repo gates after focused checks pass>

Git/PR handling:
- create one bounded SKY-025 fix branch/PR from current main; do not merge your own PR.

When fixed, report the PR URL/commit, changed files, checks run/results, and any remaining
limitation. Then stop. The result will be reviewed again in a fresh independent review session.
```
