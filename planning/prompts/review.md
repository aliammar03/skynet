---
summary: "Independently review the exact open SKY-025 phase PR before human merge; accept it read-only or return one paste-ready fix prompt."
---

# Review open work before merge

> Independent review prompt for the [phase handoff workflow](README.md). Follows the active SKY-025
> directive and the review model in [`../../docs/conventions/construction.md`](../../docs/conventions/construction.md):
> the reviewer never modifies implementation or planning state.

In a **new separate fresh session** using the selected model and effort, review the complete numbered
SKY-025 phase against the exact **open final implementation/fix PR head proposed for merge**. Include
any earlier merged slice PRs required to judge the complete phase. Do not run independent acceptance
reviews of intermediate slices.

1. Read `agent_docs/`, AGENTS.md, planning/README.md, the active SKY-025 directive found by ID, its
   current packet and disposition map if present. Record the selected model/effort when available;
   review is model-agnostic and does not require a particular model or effort. Use repository/PR evidence,
   not an implementation transcript. Load relevant callers, contracts and tests as needed. Read-only
   Investigator workers may gather evidence, but the reviewer owns the verdict.
2. Verify through GitHub that the target PR is **open**, record its URL and exact head SHA, and inspect
   current main plus all earlier merged slice/fix PRs needed for the numbered phase. Confirm every slice
   is implemented. If the complete phase is not yet represented, return the same-phase execution
   continuation without issuing ACCEPT or releasing the next numbered phase.
3. Inspect the complete phase/fix diff against the packet's starting revision and the actual proposed
   result (`current main + exact open PR head`). Account for intervening commits affecting these surfaces.
   Check callers, failure handling, doctrine/runbooks and scope, not merely the PR summary. Run relevant
   checks independently; report commands and unavailable verification explicitly. **Do not modify the
   repository and do not author repair or planning commits.** Existing live/grant boundaries still apply;
   review alone grants no production access.
4. Choose ACCEPT, FIX, or BLOCKED against each exit criterion. CI green alone is insufficient. ACCEPT
   requires satisfied exits; FIX means one or more concrete, fixable implementation defects; BLOCKED
   means missing evidence, access, or an unresolved decision prevents judgment. Do not silently waive an
   exit criterion. There is no reviewer-authored-repair acceptance path.
5. Act on the verdict:
   - **ACCEPT**: return a concise read-only verdict naming the exact reviewed PR and head SHA, critical
     evidence, limitations, and any G1–G6 roadmap decision that the post-merge closeout must carry.
     **Do not commit, push, open a review PR, merge, or update accepted progress yourself.** Ali may
     human-merge only that exact reviewed head. If the head changes, acceptance is stale and a fresh
     review is required before merge.
   - **BLOCKED**: return the blocker, owner, evidence/decision needed to resume, and the exact reviewed
     PR/head. Do not modify the repository and do not release the next phase.
   - **FIX**: your entire final response is **only** one fenced paste-ready fix prompt for the original
     implementation/fix session using the structure below. Leave accepted progress unchanged. The
     original session updates the same open PR, publishes the new head, and stops. Ali then manually
     starts another fresh independent review.
6. After ACCEPT and **human merge**, a separate bounded closeout updates accepted progress,
   `agent_docs`, directive/map/roadmap, G-checkpoint decisions, and only the next 1–2h packet. That
   closeout is not this review and does not automatically launch another acceptance review unless it
   introduces substantive implementation changes.

## ACCEPT response

Return a compact verdict such as:

```text
ACCEPT SKY-025 P<N>
Reviewed PR: <URL>
Reviewed head: <full SHA>
Evidence: <exit criterion → independent result; unavailable checks>
Limitations: <remaining explicitly unverified items, or none>
Post-merge closeout: <required progress/map/roadmap/G-checkpoint/next-packet actions>
```

Do not create a review/planning PR from the reviewer session.

## FIX response

On FIX, emit **only** this block, populated with real findings, with no preamble or prose outside it:

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
- update the same open reviewed SKY-025 branch/PR and report its new exact head;
- do not merge your own PR;
- after publishing the fix, STOP. Do not launch or continue into acceptance review.

When fixed, report the PR URL/commit, changed files, checks run/results, and any remaining limitation.
Then stop. Ali will manually start a fresh independent review session against the updated open PR.
```
