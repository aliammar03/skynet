---
summary: "Engine-agnostic execute and review prompts for any directive phase."
---

# Directive handoff prompts

Paste into a fresh session on any engine. Both follow
[`../../docs/conventions/construction.md`](../../docs/conventions/construction.md).

| Prompt | Use |
|---|---|
| [Execute](execute.md) | Implement the directive's next phase on one PR, then stop |
| [Review](review.md) | Fresh-session review of a Full-tier PR; posts one verdict comment |

```text
Read planning/prompts/execute.md and execute the next phase of SKY-###.
Read planning/prompts/review.md and review PR #<number>.
```

```text
execute → PR (bin/check + tier) → Light: Ali merges
                                → Full: fresh review → FIX: same PR, re-review
                                                     → ACCEPT: Ali merges
```
