---
summary: "Fresh read-only SKY-025 review: normal open phase PRs bind ACCEPT to reviewer-resolved base+head; P7 has one legacy integrated-main transition."
---

# Review SKY-025

Follow the active SKY-025 directive and
[`../../docs/conventions/construction.md`](../../docs/conventions/construction.md).

The reviewer is read-only. **Ali provides only `P7` or a PR number. Never ask Ali for commit hashes.**

## Mode A · normal P8+ open phase PR

Use this for P8 and every later numbered phase.

1. Read `agent_docs/`, AGENTS.md, planning/README.md, the active SKY-025 directive/map, and the target
   open phase PR. Inspect relevant callers/contracts/tests as needed.
2. Confirm there is exactly one open PR representing the numbered phase. Internal slices must be on
   this same PR; they must not have been separately merged under the new P8+ workflow.
3. Resolve from GitHub:
   - target branch;
   - **reviewed base SHA** = current target-branch tip;
   - **reviewed head SHA** = current phase PR head.
4. Review the actual integration result for that base+head pair. Run relevant independent checks. CI
   green is supporting evidence, not acceptance by itself.
5. Immediately before verdict, resolve base and head again. If either moved, refresh the affected
   review against the new pair. GitHub mergeability or an unchanged head alone is insufficient.
6. Choose ACCEPT, FIX, or BLOCKED against the phase exits.

### Normal ACCEPT

ACCEPT belongs only to the reviewer-resolved base+head pair. The verdict records both as audit evidence,
but **Ali does not compare or shuttle them**. Human merge is valid only while the pair remains current;
movement of either requires fresh review.

Use:

```text
ACCEPT SKY-025 P<N>
PR: #<number> <URL>
Review binding (automatic): base <full SHA>; head <full SHA>
Evidence: <exit criterion → independent result>
Limitations: <explicit unverified items, or none>
Next: human-merge this PR, then bounded closeout releases P<N+1>.
```

### Normal FIX

The final response must be only one fenced text block containing a complete repair prompt:

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
Then stop. Ali will manually start a fresh review of that PR. The reviewer will resolve Git revisions itself.
```

### BLOCKED

Report the exact missing prerequisite/evidence. Do not mutate the repository, merge, or release the next
phase.

## Mode B · one-time P7 already-merged transition

Use this only while accepted progress remains 6/24 and #235, #236, #237 and corrective #239 are already
merged. **Do not require a nonexistent open P7 PR.**

1. Resolve current `main` from GitHub and record it as the reviewed integrated revision.
2. Review the complete **already-integrated P7 result**, including #235, #236, #237, #239 and any later
   commit touching P7-owned surfaces (Omada, certs, routes, recon, their callers/tests/docs).
3. Re-run independent checks proportionate to P7 exits and inspect the corrective behavior that #239
   introduced. Do not treat its green CI as a substitute for inspection.
4. Immediately before verdict, resolve `main` again. If it moved, inspect the delta and refresh affected
   evidence before verdict.
5. Choose ACCEPT, FIX, or BLOCKED.

### P7 ACCEPT

```text
ACCEPT SKY-025 P7 — one-time legacy transition
Review binding (automatic): integrated main <full SHA>
Merged evidence: #235, #236, #237, #239 + <later P7-relevant commits if any>
Evidence: <exit criterion → independent result>
Limitations: <explicit unverified items, or none>
Next: bounded P7 closeout records current_phase 7 and releases the prepared P8 packet.
```

This verdict truthfully accepts the current integrated P7 result. It does **not** claim those merged PRs
were reviewed pre-merge.

### P7 FIX

Return only one fenced repair prompt. It must create **one bounded corrective P7 PR**. Once open, that
corrective PR immediately follows Mode A: fresh pre-merge review, FIX on the same PR, ACCEPT before human
merge.

No future phase may use Mode B.
