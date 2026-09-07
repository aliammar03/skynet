---
summary: "SKY-025 handoffs: execute bounded packets, independently review complete numbered phases."
---

# Phase handoffs

> Reusable SKY-025 prompts, governed by [planning](../README.md) and the active directive.

| Prompt | Session | Produces |
|---|---|---|
| [Execute](execute.md) | New task with the packet's execution model/effort | Implementation or fix PR |
| [Review](review.md) | New task with Astra Medium | Review and planning PR |

Select the model and effort when starting each task. Prompts cannot switch the running model or
launch the next session. Use a fresh task for independent review; do not resume the implementation
conversation. Git records the handoff, so chat transcripts and optional memory are unnecessary.

1. After this workflow PR merges, start Phase 1 with the execute invocation below. Its detailed
   packet in the merged directive is the initial authorization; no preceding review PR is needed.
2. Review the implementation PR and merge it yourself when ready.
3. If that PR completes only a slice, continue execution within the same numbered phase; the
   execution lead details the remaining packet before work. Once the whole phase is implemented
   and its PRs are merged, start a fresh Astra Medium review with all phase implementation PR URLs.
4. Merge the resulting review/planning PR. ACCEPT releases its next packet; FIX releases only its
   fix packet; BLOCKED releases no implementation until the recorded blocker is resolved and reviewed.
5. Execute that packet in a new task. After a fix PR merges, review the original phase again with
   both the original and fix PR URLs. Repeat until accepted.

**Execute invocation** (the agent resolves the next packet; add a phase/slice if desired):

```text
Read planning/prompts/execute.md and execute the next authorized SKY-025 packet.
```

**Review invocation** (replace the URL):

```text
Read planning/prompts/review.md and review SKY-025 implementation PR <URL>.
```

PR bodies are specified inside each prompt, keeping two reusable files instead of a second template
system. Every PR targets `main`; planning starts from the merged implementation. No stacked future
phase PRs, new GitHub Actions, automatic sessions, or automatic merges are needed.
