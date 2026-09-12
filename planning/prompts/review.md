---
summary: "Fresh SKY-025 review: every open-PR verdict is durable, newest verdict wins, and the one-time legacy P7 transition uses the same fail-closed rule on merged PR #239."
---

# Review SKY-025

Follow the active SKY-025 directive and
[`../../docs/conventions/construction.md`](../../docs/conventions/construction.md).

The reviewer is **implementation-read-only**. Ali provides only a PR number, or `P7` for the historical
one-time transition. Never ask Ali for commit hashes. The reviewer's only repository mutation is the
machine-readable review-state comment described below. The reviewer never edits Git content.

## Normal open-PR review

Use this for every P8+ numbered phase PR and for any corrective P7 PR.

1. Read `agent_docs/`, `AGENTS.md`, `planning/README.md`, the active SKY-025 directive/map, and the
   target open PR. Inspect relevant callers/contracts/tests as needed.
2. Resolve from GitHub:
   - target branch;
   - **reviewed base SHA** = current target-branch tip;
   - **reviewed head SHA** = current PR head.
3. Review the actual integration represented by that base+head pair and run proportionate independent
   checks. Green CI supports review but does not replace it.
4. Immediately before verdict, resolve base and head again. If either moved, refresh affected evidence
   against the new pair.
5. Choose ACCEPT, FIX, or BLOCKED.
6. Before returning, post exactly one `skynet-acceptance:v1` marker to the PR conversation for that
   verdict:

```text
<!-- skynet-acceptance:v1
scope=SKY-025 P<N>
verdict=<ACCEPT|FIX|BLOCKED>
base=<full reviewed base SHA>
head=<full reviewed head SHA>
-->
```

For corrective P7 use `scope=SKY-025 P7 corrective`.

**Newest applicable marker wins.** Older markers are audit history only. A newer FIX or BLOCKED marker
supersedes every older ACCEPT, even when base and head are unchanged. A malformed newest applicable
marker fails closed. Any superseded or mismatched ACCEPT is stale. The implementation/fix session must
never create or forge review-state markers.

On **private GitHub Free**, the final agent recheck and Ali's later click-to-merge are not atomic. Prompt
merge minimizes but does not eliminate that race. Never require Ali to compare hashes or claim the
review state makes that interval atomic.

### ACCEPT

Ali does not copy or compare hashes. After ACCEPT, Ali tells the original implementation/fix session
only `accepted`. That session fetches the markers itself, selects the newest applicable one, requires
`verdict=ACCEPT`, verifies current base/head still match it, and performs bounded closeout on this same
PR before merge.

Post-ACCEPT closeout may change only the closure bookkeeping envelope defined by construction doctrine:
directive/archive/planning state, Main-owned deployment-state `agent_docs`, append-only journal closure
evidence, and generator-owned closure views. Source/runtime/config/tests/invariants/AGENTS/doctrine/
runbooks/behavioral docs/stable memory or other substantive changes require fresh review.

Return:

```text
ACCEPT SKY-025 P<N>
PR: #<number> <URL>
Review binding: base <full SHA>; head <full SHA>
Review-state marker: posted to PR
Evidence: <exit criterion → independent result>
Limitations: <explicit limitations or none>
Next: tell the original implementation/fix session "accepted". It will validate the newest marker, close out the SAME PR, and hand that PR back for one human merge.
```

### FIX

The FIX marker posted above immediately revokes any older ACCEPT for the same PR state. Final response
must be only one fenced repair prompt:

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

The BLOCKED marker posted above immediately revokes any older ACCEPT for that PR state. Report the exact
missing prerequisite/evidence. Do not mutate Git content, merge, or release the next phase.

## One-time legacy P7 review

This exists only for the historical P7 implementation already merged in #235, #236, #237 and #239
while accepted progress remains 6/24. A new corrective P7 PR uses the normal open-PR review above and
never returns to this path.

Merged PR **#239** is the durable legacy P7 review-state anchor. Every legacy P7 verdict posts exactly
one marker there:

```text
<!-- skynet-legacy-acceptance:v1
scope=SKY-025 P7
verdict=<ACCEPT|FIX|BLOCKED>
integrated_main=<full reviewed main SHA>
anchor_pr=239
-->
```

1. Resolve current `main` and review the complete integrated P7 result, including #235, #236, #237,
   #239 and later P7-owned changes.
2. Run proportionate independent checks.
3. Immediately before verdict, resolve `main` again and refresh affected evidence if it moved.
4. Post exactly one marker above for ACCEPT, FIX, or BLOCKED.

The newest applicable marker on #239 is authoritative. Older markers are audit history only. A newer
FIX/BLOCKED supersedes every older ACCEPT. P8 may start only when the newest marker is well formed,
`verdict=ACCEPT`, and its `integrated_main` still equals current `main`.

### P7 ACCEPT

Return:

```text
ACCEPT SKY-025 P7 — one-time legacy transition
Review binding: integrated main <full SHA>
Legacy review-state marker: posted to merged PR #239
Merged evidence: #235, #236, #237, #239 + <later P7-relevant commits if any>
Evidence: <exit criterion → independent result>
Limitations: <explicit unverified items, or none>
Next: start P8. The P8 session will validate the newest #239 marker itself before advancing P7 state.
```

Do not create a standalone P7 closeout PR. The natural P8 PR carries the small P7 accepted /
`current_phase: 7` transition as opening bookkeeping.

### P7 FIX

The FIX marker supersedes any older ACCEPT. Return one bounded repair prompt creating **one corrective
P7 PR**. That corrective PR uses the normal open-PR review above. P8 remains blocked until the repair is
accepted and merged.

### P7 BLOCKED

The BLOCKED marker supersedes any older ACCEPT. Report the blocker and keep P8 blocked.
