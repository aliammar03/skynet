---
summary: "SKY-025 handoffs: one open PR per numbered phase, fresh pre-merge review, no human SHA bookkeeping."
---

# SKY-025 phase handoffs

Governed by the active SKY-025 directive and
[`../../docs/conventions/construction.md`](../../docs/conventions/construction.md).

| Prompt | Use |
|---|---|
| [Execute](execute.md) | Implement/repair the currently authorized numbered phase on its one open phase PR, then STOP |
| [Review](review.md) | Fresh read-only review of that open PR, or the one-time already-merged P7 migration |

## Normal P8+ flow

```text
Ali starts implementation
        ↓
one open PR for the numbered phase
(internal slices stay on this PR)
        ↓
implementation/fix session reports PR + STOP
        ↓
Ali starts fresh review chat
        ↓
reviewer resolves + rechecks base/head itself
        ├── FIX → same PR → STOP → fresh review
        └── ACCEPT
               ↓
          human merge
               ↓
        bounded closeout
               ↓
          next phase
```

**No intermediate implementation slice is merged before phase review.** If P8A/P8B or a later phase
needs multiple sessions, they continue on the same open numbered-phase PR.

Ali supplies only the phase/PR identity. The reviewer obtains revision identities from GitHub and owns
the base+head safety check; Ali never copies or compares commit hashes.

## One-time P7 migration

P7 implementation/corrective PRs #235, #236, #237 and #239 were already merged before this workflow
became current. P7 therefore gets one fresh read-only review of the already-integrated result on
current `main`. This is the only merge-first exception.

- ACCEPT → bounded P7 closeout, then the prepared P8 packet becomes executable.
- FIX → one corrective P7 PR, which immediately uses the normal pre-merge workflow above.

Current invocation:

```text
Read planning/prompts/review.md and review SKY-025 P7 using the one-time already-merged transition.
```

After P7 closeout, implementation becomes:

```text
Read planning/prompts/execute.md and execute the next authorized SKY-025 packet.
```

Normal review requires only a PR number:

```text
Read planning/prompts/review.md and review SKY-025 PR #<number>.
```

Every authored PR targets `main`, remains human-merged, and is externally reviewed before merge from
P8 onward. Prompts never start another session automatically.
