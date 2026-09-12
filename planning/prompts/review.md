---
summary: "Fresh read-only SKY-025 review: normal open-PR mode approves a reviewer-resolved base+head pair; P7 has one legacy integrated-main transition."
---

# Review SKY-025

Follow the active SKY-025 directive and
[`../../docs/conventions/construction.md`](../../docs/conventions/construction.md).

The reviewer is read-only. **Ali provides only `P7` or a PR number. Never ask Ali for commit hashes.**

## Mode A · normal open-PR review

Use this mode for:

- every P8+ numbered phase PR; and
- any bounded corrective P7 PR created after a legacy P7 FIX verdict.

A corrective P7 PR is ordinary new open-PR work. It never falls back into the one-time integrated-main
legacy review mode below.

1. Read `agent_docs/`, AGENTS.md, planning/README.md, the active SKY-025 directive/map, and the target
   open PR. Inspect relevant callers/contracts/tests as needed.
2. For a P8+ numbered phase, confirm there is exactly one open PR representing that numbered phase.
   Internal slices must be on this same PR; they must not have been separately merged under the new
   workflow. For a corrective P7 PR, confirm the PR is the bounded repair created from the legacy P7 FIX.
3. Resolve from GitHub:
   - target branch;
   - **reviewed base SHA** = current target-branch tip;
   - **reviewed head SHA** = current PR head.
4. Review the actual integration result for that base+head pair. Run relevant independent checks. CI
   green is supporting evidence, not acceptance by itself.
5. Immediately before verdict, resolve base and head again. If either moved, refresh the affected
   review against the new pair. GitHub mergeability or an unchanged head alone is insufficient.
6. Choose ACCEPT, FIX, or BLOCKED against the applicable phase/repair exits.

### Normal ACCEPT

ACCEPT approves the exact reviewer-resolved base+head pair verified immediately before the verdict. The
verdict records both as audit evidence, but **Ali does not compare or shuttle them**. If either revision
is known to change before merge, the ACCEPT is stale and a fresh review is required.

On the intended private GitHub Free setup, this approval is **not** a mechanical or atomic guarantee
that the later human merge will use the same pair. A race window remains between the reviewer's final
recheck/ACCEPT and Ali later clicking Merge. Prompt human merge after ACCEPT reduces that window but
does not eliminate it. Do not require a paid GitHub upgrade, manual SHA comparison, or a helper that
claims false atomicity. If future repository configuration provides enforceable up-to-date-branch
protection or an equivalent atomic guarantee, the doctrine may strengthen this contract then.

Use:

```text
ACCEPT SKY-025 P<N>
PR: #<number> <URL>
Review binding (automatic): base <full SHA>; head <full SHA>
Evidence: <exit criterion → independent result>
Limitations: private GitHub Free leaves a race window between this final recheck/ACCEPT and later human merge; <other explicit unverified items, or none>
Next: human-merge this PR promptly if no repository/PR change is known; any known base/head movement makes this ACCEPT stale and requires fresh review. Then run bounded closeout.
```

For a corrective P7 PR, the title/verdict may say `SKY-025 P7 corrective`, but it uses this same normal
open-PR review contract.

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

Use this only for the historical P7 implementation already merged in #235, #236, #237 and corrective
#239 while accepted progress remains 6/24. **Do not use Mode B for a new corrective P7 PR.** Do not
require a nonexistent open PR for the historical merged work.

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

Return only one fenced repair prompt. It must create **one bounded corrective P7 PR**. Once that new PR
is open, review it with **Mode A, the normal open-PR review**, exactly like a future phase PR: resolve
and recheck base+head, FIX on the same PR, ACCEPT before human merge. It must never return to Mode B.

No future phase may use Mode B.
