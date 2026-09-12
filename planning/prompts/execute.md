---
summary: "Execute the currently authorized SKY-025 numbered phase on one open phase PR, then stop for fresh review."
---

# Execute SKY-025

Follow the active SKY-025 directive and
[`../../docs/conventions/construction.md`](../../docs/conventions/construction.md).

## 1. Resolve the gate first

Read `agent_docs/`, AGENTS.md, planning/README.md, the active SKY-025 directive, and
`planning/sky-025-map.md` before broad exploration.

If the directive still says **P7 review pending / accepted progress 6 of 24**, do not implement P8.
Return only the current P7 review invocation from the directive. P8 becomes executable only after a
truthful P7 ACCEPT and bounded closeout records `current_phase: 7`.

Otherwise execute the single authorized packet in the directive.

## 2. One numbered phase = one open PR

From P8 onward, every numbered phase owns one branch/PR targeting `main`.

- Start from current remote `main` unless an open PR already exists for this numbered phase.
- If the phase already has an open PR, reuse it. Never create a second phase PR just because work is
  continuing in another session.
- Internal lettered slices are bounded working units on the same phase PR. Do not merge them separately.
- Preserve unrelated work and existing trust/live boundaries.
- Never begin the next numbered phase before the current one is externally ACCEPTed, human-merged, and
  closed out.

The implementation session may record Git revisions as evidence in the PR, but must never ask Ali to
copy, compare, or carry commit hashes between chats.

## 3. Route and implement

Use the directive's Light/Medium/Heavy recommendation and native SKY-026 construction contract.
Delegate bounded work through the current native roles when useful. Workers do not merge and gain no
production authority.

Implement only the authorized phase/slice. Update affected callers, behavioral tests, packaging, and
current documentation together. If the phase needs more than one internal slice, continue on the same
open phase PR until the complete numbered phase is implementation-ready.

Do not silently weaken an exit criterion, widen live authority, invent validation, or turn temporary
migration compatibility into a second permanent engine.

## 4. Verify

Run the focused checks needed for the changed surface, then the phase's required full gates. Report
exact commands/results and any skipped or unavailable validation. In Heavy work, use the independent
Tester contract and return ordinary defects to the owning Executor before handoff.

## 5. Handoff and STOP

When the complete numbered phase is implementation-ready:

- update Main-owned `agent_docs` truthfully as **implementation ready / pending fresh review**;
- commit/push the phase PR;
- report the PR URL/number, changed files, verification results, and limitations;
- **STOP**.

Do not start, spawn, or continue into final acceptance review. Ali manually starts a fresh review chat.
The reviewer resolves the current target/base and PR head directly from GitHub and rechecks them before
verdict.

Use PR title:

```text
SKY-025 P<N>: <outcome>
```

For a reviewer-requested repair, keep the same open PR and title family:

```text
SKY-025 P<N> fix: <outcome>
```

A compact PR body is enough:

```text
Phase: P<N> <outcome>
Why/changes: <implemented behavior + affected callers/docs>
Exit evidence: <criterion → command/result or explicit gap>
Limitations: <remaining unverified/live/recovery boundaries>
Review status: implementation ready / pending fresh review
Review handoff: Read planning/prompts/review.md and review SKY-025 PR #<number>.
```

If publishing is unavailable, preserve the branch/commit and report the blocker. Do not merge your own
work.
