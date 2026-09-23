# 🚀 projects — active, executable plans

scratchpad ▸ ideas ▸ backlog ▸ **`projects`** ▸ archive

**This is what you actually run — at most two at a time.** Every directive here is fully planned:
one-PR phases with exit evidence and a review tier, and a `## Status` block naming the next phase,
so a fresh session cold-starts from [`../prompts/`](../prompts/README.md) without losing the thread.

The workflow, start to finish:

1. **Kick off** — paste the directive's ▶ Execute prompt into a new session.
2. **Each phase is one PR** — it carries the work, `bin/check` evidence, its review tier, and the
   directive's own status update, so merge is completion.
3. **Anything touching T2+/T3** or a blast-radius boundary also PRs `docs/system-design.md`.

**→ Out:** shipped or killed, `bin/plan archive SKY-###` retires it to
[`../archive/`](../archive/) — the ID and its history stay meaningful forever.
