---
summary: "SKY-025 handoffs: one open PR per numbered phase, normal open-PR review for P8+ and corrective P7, no human SHA bookkeeping."
---

# SKY-025 phase handoffs

Governed by the active SKY-025 directive and
[`../../docs/conventions/construction.md`](../../docs/conventions/construction.md).

| Prompt | Use |
|---|---|
| [Execute](execute.md) | Implement/repair the currently authorized numbered phase on its one open phase PR, then STOP |
| [Review](review.md) | Normal read-only review of an open P8+ phase PR or corrective P7 PR, plus the one-time already-merged P7 migration |

## Normal open-PR flow

This flow applies to every P8+ numbered phase PR and to any bounded corrective P7 PR created after the
one-time legacy P7 review returns FIX.

```text
Ali starts implementation / bounded corrective P7 work
        ↓
one open PR for the work
(P8+ internal slices stay on the phase PR)
        ↓
implementation/fix session reports PR + STOP
        ↓
Ali starts fresh review chat
        ↓
reviewer resolves + rechecks base/head itself
        ├── FIX → same PR → STOP → fresh review
        └── ACCEPT of the exact pair verified immediately before verdict
               ↓
          prompt human merge if no change is known
               ↓
        bounded closeout
               ↓
          next phase / state
```

**No intermediate P8+ implementation slice is merged before phase review.** If P8A/P8B or a later
phase needs multiple sessions, they continue on the same open numbered-phase PR. A corrective P7 PR is
already bounded repair work and uses this same normal open-PR review path.

Ali supplies only the phase/PR identity. The reviewer obtains revision identities from GitHub, reviews
the exact base+head pair, and rechecks both immediately before verdict; Ali never copies or compares
commit hashes. Known movement of either revision before merge makes ACCEPT stale and requires fresh
review.

On the intended private GitHub Free setup there is no mechanical/atomic guarantee that the reviewed
pair cannot move after the final recheck and before Ali later clicks Merge. Prompt merge after ACCEPT
reduces but does not remove that race window. The current workflow does not require a paid GitHub
upgrade, manual SHA comparison, or a helper that pretends the read/check and GitHub merge are atomic.

## One-time P7 migration

P7 implementation/corrective PRs #235, #236, #237 and #239 were already merged before this workflow
became current. P7 therefore gets one fresh read-only review of the already-integrated result on
current `main`. This is the only merge-first exception.

- ACCEPT → bounded P7 closeout, then the prepared P8 packet becomes executable.
- FIX → one bounded corrective P7 PR. That new PR uses the **normal open-PR flow above** and never
  returns to the integrated-main legacy review.

Current invocation:

```text
Read planning/prompts/review.md and review SKY-025 P7 using the one-time already-merged transition.
```

After P7 closeout, implementation becomes:

```text
Read planning/prompts/execute.md and execute the next authorized SKY-025 packet.
```

Normal open-PR review requires only a PR number:

```text
Read planning/prompts/review.md and review SKY-025 PR #<number>.
```

Every newly opened authored PR, including a corrective P7 PR and every P8+ phase PR, remains
human-merged and receives fresh external review before merge. Prompts never start another session
automatically.
