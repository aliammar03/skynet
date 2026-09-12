---
summary: "Execute the authorized SKY-025 phase on one PR; legacy P7 release requires the newest durable #239 verdict to be ACCEPT and still match current main."
---

# Execute SKY-025

Follow the active SKY-025 directive and
[`../../docs/conventions/construction.md`](../../docs/conventions/construction.md).

## 1. Resolve the gate first

Read `agent_docs/`, AGENTS.md, planning/README.md, the active SKY-025 directive, and
`planning/sky-025-map.md` before broad exploration.

If the directive still says **P7 review pending / accepted progress 6 of 24**, do not implement P8 until
this session independently validates the one-time legacy review state. Do not rely on the previous
review chat and never ask Ali for a revision hash.

1. Fetch all `skynet-legacy-acceptance:v1` markers from merged **PR #239** and select the **newest**
   applicable marker by GitHub conversation order.
2. Require exactly:
   - `scope=SKY-025 P7`;
   - `anchor_pr=239`;
   - one full `integrated_main` SHA;
   - **newest marker `verdict=ACCEPT`**.
3. Resolve current remote `main` yourself immediately before creating/reusing the P8 branch.
4. Require current `main` to equal the newest marker's `integrated_main`. If the newest marker is absent,
   malformed, FIX, BLOCKED, or current `main` differs, report **P7 review stale/not accepted**, keep P8
   blocked, and do not advance P7 state. Never fall back to an older ACCEPT marker.
5. Only after both checks pass, start from that validated `main`, use the natural P8 PR, and make its
   opening bookkeeping record P7 accepted / `current_phase: 7` before P8 implementation. No standalone
   P7 closeout PR is created.

This means a newer FIX/BLOCKED review on the same integrated revision immediately revokes an older
ACCEPT, and any later `main` movement also makes the ACCEPT stale. Chat continuity is irrelevant.

Otherwise execute the single authorized packet in the directive.

## 2. One numbered phase = one open PR

From P8 onward, every numbered phase owns one branch/PR targeting `main`.

- Start from current remote `main` unless an open PR already exists for this numbered phase.
- Reuse an existing phase PR. Never create a second phase PR because work continued in another session.
- Internal lettered slices stay on that same phase PR and are never merged independently.
- Preserve unrelated work and existing trust/live boundaries.
- Never begin the next numbered phase before the current one is externally ACCEPTed and its **same-PR
  closeout has been human-merged**.

Ali never copies, compares, or carries Git revision hashes between chats.

## 3. Route and implement

Use the directive's Light/Medium/Heavy recommendation and native SKY-026 construction contract.
Delegate bounded work through current native roles when useful. Workers do not merge and gain no
production authority.

Implement only the authorized phase/slice. Update affected callers, behavioral tests, packaging, and
current documentation together. If the phase needs multiple internal slices, continue on the same open
phase PR until the complete numbered phase is implementation-ready.

Do not silently weaken an exit criterion, widen live authority, invent validation, or turn temporary
migration compatibility into a second permanent engine.

## 4. Verify

Run focused checks for the changed surface, then the phase's required full gates. Report exact results
and any unavailable validation. In Heavy work, use the independent Tester contract and return ordinary
defects to the owning Executor before handoff.

## 5. Implementation handoff and STOP

When the complete numbered phase is implementation-ready:

- update Main-owned `agent_docs` truthfully as **implementation ready / pending fresh review**;
- commit/push the phase PR;
- report the PR URL/number, changed files, verification results, and limitations;
- **STOP**.

Do not start, spawn, or continue into final acceptance review. Ali manually starts a fresh review chat.
The reviewer resolves current target/base + PR head itself and rechecks both before verdict.

Use PR title:

```text
SKY-025 P<N>: <outcome>
```

For reviewer-requested repair, keep the same PR:

```text
SKY-025 P<N> fix: <outcome>
```

## 6. When Ali returns and says `accepted`

This is **accepted closeout mode**, not a new implementation phase and not another PR.

1. Fetch the latest `skynet-acceptance:v1` marker from this PR conversation yourself.
2. Verify its scope matches this phase/repair, the PR is still open, current target/base equals the
   marker's reviewed base, and current PR head equals the marker's reviewed head **before** closeout.
   If any check fails, report ACCEPT stale and require a fresh review. Never ask Ali for hashes.
3. Apply only bounded closeout bookkeeping on this same PR:
   - mark the accepted directive phase/state;
   - archive/advance planning state as required;
   - update `agent_docs/project_progress.md`, `project_diary.md`, `latest_session_work.md`;
   - append journal closure evidence;
   - run normal generators for closure-derived views when required.
4. Do **not** change source/runtime/config/tests/invariants/AGENTS/doctrine/runbooks/behavioral docs/stable
   agent memory or any substantive implementation surface. If such a change is needed, stop: ACCEPT is
   stale and the same PR needs fresh review after the change.
5. Prove the marker-head..final-head delta is closeout-only, rerun closure-focused gates plus normal CI,
   and recheck target/base still equals the marker base.
6. Push the closeout to this same PR, report it ready for **one human merge**, then STOP.

The closeout commit moves the PR head by design; that allowed bookkeeping movement alone does not
invalidate ACCEPT. Private GitHub Free still leaves a non-atomic race between the final recheck and
Ali clicking Merge, so prefer prompt merge but do not claim atomicity.

A compact pre-review PR body is enough:

```text
Phase: P<N> <outcome>
Why/changes: <implemented behavior + affected callers/docs>
Exit evidence: <criterion → command/result or explicit gap>
Limitations: <remaining unverified/live/recovery boundaries>
Review status: implementation ready / pending fresh review
Review handoff: Read planning/prompts/review.md and review SKY-025 PR #<number>.
```

After accepted closeout, update the body to state `Review status: ACCEPTED; bounded closeout staged on
this same PR; ready for one human merge.`

If publishing is unavailable, preserve the branch/commit and report the blocker. Never merge your own
work and never create a closeout-only PR.
