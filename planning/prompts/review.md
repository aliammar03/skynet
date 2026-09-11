---
summary: "Independently review SKY-025 before merge, binding ACCEPT to the reviewer-resolved base+head pair; includes the one-time already-merged P7 transition."
---

# Review SKY-025 work

> Independent review prompt for the [phase handoff workflow](README.md). Follows the active SKY-025
> directive and [`../../docs/conventions/construction.md`](../../docs/conventions/construction.md).
> The reviewer is read-only and resolves Git revision identities from GitHub itself. **Ali never needs
> to supply, copy, or compare commit SHAs by hand.**

Use a **new separate fresh session** with the selected model/effort. For normal future work, review the
complete numbered phase against its open final implementation/fix PR before human merge. The one
exception is the explicit SKY-025 P7 migration below, because its implementation/fix PRs were already
merged before the pre-merge review lifecycle became current policy.

1. Read `agent_docs/`, AGENTS.md, planning/README.md, the active SKY-025 directive found by ID, its
   current packet and disposition map. Use repository/PR evidence, not an implementation transcript.
   Load relevant callers, contracts and tests as needed. Read-only Investigator workers may gather
   evidence, but the reviewer owns the verdict.
2. Resolve review identity from GitHub, without asking Ali for hashes:
   - **Normal open-PR mode:** verify the target PR is open; record its URL/number, target branch,
     **reviewed base SHA** (the current target-branch tip, normally `main`) and **reviewed head SHA**.
     Include earlier merged slice/fix PRs needed to judge the complete numbered phase.
   - **One-time SKY-025 P7 legacy transition:** if P7 is still review-pending and #235, #236, #237 and
     corrective #239 are already merged, do **not** require a nonexistent open P7 PR. Record current
     `main` as the reviewed integrated revision and review the complete P7 result already present in
     `main`, including those merged PRs plus any later commits touching P7-owned surfaces. This
     transition applies only to P7 work merged before the new lifecycle; it is not a future escape
     hatch from pre-merge review.
3. Inspect the actual integration state, not just PR summaries:
   - normal mode: the result of the captured **reviewed base + reviewed head** pair;
   - P7 legacy mode: the captured integrated `main` revision.
   Account for intervening commits affecting the phase. Check callers, failure handling,
   doctrine/runbooks and scope. Run relevant checks independently and report unavailable verification.
   **Do not modify the repository and do not author repair or planning commits.** Review grants no
   production access.
4. Immediately before publishing a verdict, resolve GitHub state again. In normal mode, if either the
   target/base SHA **or** PR head SHA differs from the captured pair, the old integration conclusion is
   stale: refresh the diff/evidence against the new pair and do not issue ACCEPT until the currently
   proposed pair has actually been reviewed. In P7 legacy mode, if `main` moved, inspect the delta and
   refresh affected evidence before verdict. GitHub mergeability or an unchanged head alone is not
   proof that the reviewed integration result is unchanged.
5. Choose ACCEPT, FIX, or BLOCKED against every exit criterion. CI green alone is insufficient.
   - **Normal ACCEPT:** record both reviewer-resolved base SHA and head SHA. Acceptance belongs only to
     that pair. Ali may human-merge only while both still match; movement of either invalidates the
     verdict and requires a fresh review of the new integration state. This is an agent-enforced
     evidence rule, not a request for Ali to manually compare hashes.
   - **P7 legacy ACCEPT:** record the reviewed integrated `main` revision and explicitly label the
     verdict as the one-time merged-work transition. No implementation merge remains; bounded closeout
     may record P7 accepted and release P8.
   - **BLOCKED:** report the blocker and evidence/decision needed. Do not mutate the repo or release the
     next phase.
   - **FIX, normal mode:** return only one paste-ready fix prompt for the original implementation/fix
     session. It updates the same open PR and stops; Ali starts another fresh reviewer. The fix handoff
     names the PR, not a SHA for Ali to shuttle around.
   - **FIX, P7 legacy mode:** return one paste-ready prompt to create a bounded corrective P7 PR. Once
     that corrective PR exists, it follows the normal pre-merge lifecycle above.
6. After normal ACCEPT and human merge, or after P7 legacy ACCEPT, a separate bounded closeout updates
   accepted progress, `agent_docs`, directive/map/roadmap, G-checkpoint decisions, and only the next
   packet. Closeout is not this review and does not automatically launch another acceptance review
   unless it introduces substantive implementation changes.

## ACCEPT response

Normal open-PR review:

```text
ACCEPT SKY-025 P<N>
Reviewed PR: #<number> <URL>
Reviewed base/main: <full SHA resolved by reviewer>
Reviewed PR head: <full SHA resolved by reviewer>
Evidence: <exit criterion → independent result; unavailable checks>
Limitations: <remaining explicitly unverified items, or none>
Post-merge closeout: <required progress/map/roadmap/G-checkpoint/next-packet actions>
```

One-time P7 legacy transition:

```text
ACCEPT SKY-025 P7 — legacy merged-work transition
Reviewed integrated main: <full SHA resolved by reviewer>
Merged P7 evidence: #235, #236, #237, #239 + <later P7-relevant commits, if any>
Evidence: <exit criterion → independent result; unavailable checks>
Limitations: <remaining explicitly unverified items, or none>
Closeout: record P7 accepted and release P8
```

Do not create a review/planning PR from the reviewer session.

## FIX response

For normal open-PR work, emit **only** this block with real findings and no prose outside it:

```text
Continue the original SKY-025 implementation/fix session and fix the independent review findings below.
Do not redesign unrelated work and do not self-accept the phase.

Review findings:
- <specific defect + evidence/reference>

Required fixes:
- <bounded required outcome>

Verification required:
- <specific affected tests/gates; run the relevant full repo gates after focused checks pass>

Git/PR handling:
- update the same open reviewed SKY-025 PR;
- do not merge your own PR;
- after publishing the fix, STOP. Do not launch or continue into acceptance review.

When fixed, report the PR URL/number, changed files, checks/results, and any remaining limitation.
Then stop. Ali will manually start a fresh independent review of that PR; the reviewer will resolve
its current base/head revisions directly from GitHub.
```

For a FIX from the one-time already-merged P7 transition, use the same structure except replace the
first Git/PR bullet with: `open one bounded corrective P7 PR; future review follows normal open-PR mode`.
