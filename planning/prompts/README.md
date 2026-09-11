---
summary: "SKY-025 handoffs: execute bounded packets, independently review complete numbered phases before human merge."
---

# Phase handoffs

> Reusable SKY-025 prompts, governed by [planning](../README.md), the active directive, and
> [`../../docs/conventions/construction.md`](../../docs/conventions/construction.md).

| Prompt | Session | Produces |
|---|---|---|
| [Execute](execute.md) | New task with the packet's execution model/effort | Implementation or fix PR, then STOP |
| [Review](review.md) | Fresh operator-started task with the selected model/effort | Read-only ACCEPT/BLOCKED verdict, or one paste-ready FIX prompt |

Select the model and effort when starting each task. Prompts cannot switch the running model or
launch the next session. Use a fresh task for independent review; do not resume the implementation
conversation. `agent_docs/` plus the active directive provide compact cross-session orientation; chat
transcripts are not durable handoff state. **Ali supplies only the PR/phase identity. The reviewer
resolves and records Git SHAs itself; Ali never has to copy or compare them manually.**

1. Execute the authorized phase/slice and publish its authored PR. The implementation/fix session
   reports the PR handoff and **stops**. It does not start, spawn, or continue into acceptance review.
2. Intermediate slices may be human-merged without independent phase acceptance when the active packet
   explicitly requires multiple slices. For normal future work, once the complete numbered phase is
   represented by an **open final implementation/fix PR**, Ali manually starts a fresh review chat for
   that PR together with any earlier merged slices needed to judge the whole phase.
3. The reviewer resolves the target branch, current base/main SHA, and current PR head SHA from GitHub,
   reviews that exact integration pair, and rechecks both immediately before verdict. Movement of
   either invalidates the old integration conclusion. GitHub mergeability or an unchanged head alone
   is not sufficient. The reviewer never modifies the repository.
4. FIX returns one paste-ready prompt addressed to the original implementation/fix session; that
   session updates the same open PR and stops. Ali manually starts another fresh reviewer. The handoff
   names the PR, not a SHA for Ali to shuttle between chats. ACCEPT records the reviewer-resolved
   base+head pair; human merge is valid only while both remain unchanged.
5. **One-time P7 migration:** P7's #235, #236, #237 and corrective #239 were already merged before this
   pre-merge lifecycle became current. P7 therefore receives one fresh read-only review of its
   already-integrated current-main result without inventing a nonexistent open PR. ACCEPT proceeds to
   bounded P7 closeout; FIX opens one corrective P7 PR, which then follows the normal pre-merge path.
   This exception does not apply to future phases.
6. After a normal accepted PR is human-merged, or after the one-time P7 legacy review ACCEPTs, run a
   bounded closeout to update accepted progress, `agent_docs`, map/roadmap, and the next authorized
   packet. Closeout is not another automatic acceptance review unless it introduces substantive
   implementation changes.

**Execute invocation** (the agent resolves the next packet; add a phase/slice if desired):

```text
Read planning/prompts/execute.md and execute the next authorized SKY-025 packet.
```

**Normal review invocation** (a PR number is enough):

```text
Read planning/prompts/review.md and review SKY-025 PR #<number>.
```

**Current P7 transition invocation:**

```text
Read planning/prompts/review.md and review SKY-025 P7 using the one-time already-merged transition.
```

Every authored PR targets `main` and remains human-merged. No stacked future-phase PRs, automatic
sessions, automatic acceptance reviews, automatic authored merges, or human SHA bookkeeping are
needed.
