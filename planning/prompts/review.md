---
summary: "Fresh SKY-025 review: normal open-PR ACCEPT writes a machine-readable marker, then the original session closes out that same PR before one human merge; P7 keeps one legacy integrated-main transition."
---

# Review SKY-025

Follow the active SKY-025 directive and
[`../../docs/conventions/construction.md`](../../docs/conventions/construction.md).

The reviewer is **implementation-read-only**. Ali provides only `P7` or a PR number. Never ask Ali for
commit hashes. The reviewer's only allowed repository mutation is the ACCEPT marker comment described
below; it never edits Git content.

## Mode A · normal open-PR review

Use for:

- every P8+ numbered phase PR; and
- any bounded corrective P7 PR created after a legacy P7 FIX verdict.

A corrective P7 PR is ordinary open-PR work and never falls back to Mode B.

1. Read `agent_docs/`, AGENTS.md, planning/README.md, the active SKY-025 directive/map, and the target
   open PR. Inspect relevant callers/contracts/tests as needed.
2. For P8+, confirm exactly one open PR represents the numbered phase and all internal slices remain on
   it. For corrective P7, confirm it is the bounded repair created from the legacy FIX.
3. Resolve from GitHub:
   - target branch;
   - **reviewed base SHA** = current target-branch tip;
   - **reviewed head SHA** = current PR head.
4. Review the actual integration result for that base+head pair. Run relevant independent checks. Green
   CI supports the review but does not substitute for it.
5. Immediately before verdict, resolve base and head again. If either moved, refresh affected evidence
   against the new pair before any ACCEPT.
6. Choose ACCEPT, FIX, or BLOCKED.

### Normal ACCEPT

ACCEPT approves the exact reviewer-resolved base+head pair verified immediately before verdict. Before
returning the verdict, post exactly one machine-readable acceptance marker to the PR conversation:

```text
<!-- skynet-acceptance:v1
scope=SKY-025 P<N>
verdict=ACCEPT
base=<full reviewed base SHA>
head=<full reviewed head SHA>
-->
```

For corrective P7 use `scope=SKY-025 P7 corrective`. This comment is audit/handoff metadata only. It
does not modify Git content. The implementation/fix session must never create this marker itself.

Ali does **not** copy or compare the marker hashes. After ACCEPT, Ali only tells the original
implementation/fix session that the PR was accepted. That session fetches the marker itself, verifies
current base/head still match it, and performs bounded closeout on this **same PR before merge**.

Post-ACCEPT closeout may change only the closure bookkeeping envelope defined by construction doctrine:
directive/archive/planning state, Main-owned deployment-state `agent_docs`, append-only journal closure
evidence, and generator-owned closure views. The sanctioned closeout commit therefore moves the PR head
by design and does not itself invalidate ACCEPT. Any reviewed-base movement, unexplained head movement,
or source/runtime/config/test/invariant/AGENTS/doctrine/runbook/behavioral-doc/stable-memory/substantive
change invalidates ACCEPT and requires fresh review.

Private GitHub Free still leaves a race window between the final agent recheck and Ali clicking Merge;
no mechanical/atomic merge-time guarantee is claimed. Prompt merge minimizes but does not remove it.
Do not require a paid GitHub feature, manual SHA handling, or a read/check helper that falsely claims
atomicity.

Return:

```text
ACCEPT SKY-025 P<N>
PR: #<number> <URL>
Review binding: base <full SHA>; head <full SHA>
Acceptance marker: posted to PR
Evidence: <exit criterion → independent result>
Limitations: private GitHub Free leaves a non-atomic final-recheck-to-merge race; <other limitations or none>
Next: tell the original implementation/fix session "accepted". It will validate this marker, close out the SAME PR, and hand that same PR back for one human merge.
```

### Normal FIX

Final response must be only one fenced repair prompt:

```text
Continue the original SKY-025 P<N> implementation/fix session and fix the independent review findings below.
Do not redesign unrelated work and do not self-accept the phase.

Review findings:
- <specific defect + evidence/reference>

Required fixes:
- <bounded required outcome>

Verification required:
- <specific affected tests/gates>
- run the relevant full repository gates after focused checks pass

Git/PR handling:
- update the same open SKY-025 P<N> PR;
- do not merge it;
- after publishing the fix, STOP. Do not launch or continue into acceptance review.

When fixed, report the PR URL/number, changed files, checks/results, and any remaining limitation.
Then stop. Ali will manually start a fresh review of that PR. The reviewer resolves Git revisions itself.
```

### BLOCKED

Report the exact missing prerequisite/evidence. Do not mutate Git content, merge, or release the next
phase.

## Mode B · one-time P7 already-merged transition

Use only for historical P7 implementation already merged in #235, #236, #237 and corrective #239 while
accepted progress remains 6/24. **Do not use Mode B for a new corrective P7 PR.**

1. Resolve current `main` and record it as the reviewed integrated revision.
2. Review the complete already-integrated P7 result, including #235, #236, #237, #239 and later commits
   touching P7-owned surfaces.
3. Re-run independent checks proportionate to P7 exits.
4. Immediately before verdict, resolve `main` again. If it moved, inspect the delta and refresh affected
   evidence before verdict.
5. Choose ACCEPT, FIX, or BLOCKED.

### P7 ACCEPT

```text
ACCEPT SKY-025 P7 — one-time legacy transition
Review binding: integrated main <full SHA>
Merged evidence: #235, #236, #237, #239 + <later P7-relevant commits if any>
Evidence: <exit criterion → independent result>
Limitations: <explicit unverified items, or none>
Next: start P8. The P8 implementation PR must record P7 accepted/current_phase 7 as its opening bookkeeping before P8 work. Do NOT create a standalone P7 closeout PR.
```

This accepts the current integrated P7 result without pretending those historical PRs were reviewed
pre-merge. Because there is no open P7 PR to close out, the next natural P8 PR carries the small P7
state transition instead of manufacturing a bookkeeping-only PR.

### P7 FIX

Return only one fenced repair prompt. It must create **one bounded corrective P7 PR**. Once open, review
it with Mode A exactly like future phase PRs. It may never return to Mode B.

No future phase may use Mode B.
