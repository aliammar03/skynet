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
transcripts are not durable handoff state.

1. Execute the authorized phase/slice and publish its authored PR. The implementation/fix session
   reports the handoff and **stops**. It does not start, spawn, or continue into acceptance review.
2. Intermediate slices may be human-merged without independent phase acceptance when the active packet
   explicitly requires multiple slices. Once the complete numbered phase is represented by an **open
   final implementation/fix PR**, Ali manually starts a fresh review chat against that exact open head,
   together with any earlier merged slice PRs needed to judge the whole phase.
3. The reviewer never modifies the repository. FIX returns one paste-ready prompt addressed to the
   original implementation/fix session; that session updates the same open PR, reports the new head,
   and stops. Ali manually starts another fresh reviewer. Repeat until ACCEPT.
4. ACCEPT applies only to the exact reviewed PR head. Ali then human-merges that exact head. Any head
   change after ACCEPT invalidates the verdict and requires fresh review before merge.
5. After the accepted PR is merged, run a bounded closeout to update accepted progress, `agent_docs`,
   map/roadmap, and the next authorized packet. That closeout is not another automatic acceptance
   review unless it introduces substantive implementation changes.

**Execute invocation** (the agent resolves the next packet; add a phase/slice if desired):

```text
Read planning/prompts/execute.md and execute the next authorized SKY-025 packet.
```

**Review invocation** (replace the URL):

```text
Read planning/prompts/review.md and review open SKY-025 implementation/fix PR <URL>.
```

Every authored PR targets `main` and remains human-merged. No stacked future-phase PRs, automatic
sessions, automatic acceptance reviews, or automatic authored merges are needed.
