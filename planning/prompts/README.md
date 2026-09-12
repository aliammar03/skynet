---
summary: "SKY-025 handoffs: one open PR per numbered phase, fresh review, same-PR accepted closeout, one human merge, plus durable one-time P7 review state on #239."
---

# SKY-025 phase handoffs

Governed by the active SKY-025 directive and
[`../../docs/conventions/construction.md`](../../docs/conventions/construction.md).

| Prompt | Use |
|---|---|
| [Execute](execute.md) | Implement/repair the currently authorized numbered phase on its one open phase PR, then STOP |
| [Review](review.md) | Fresh review of an open P8+ phase PR or corrective P7 PR, plus the one-time already-merged P7 migration |

## Normal open-PR flow

This applies to every P8+ numbered phase PR and any corrective P7 PR created after the one-time legacy
P7 review returns FIX.

```text
implementation / repair
        ↓
one open PR for the numbered phase
(internal slices stay on it)
        ↓
implementation/fix session reports PR + STOP
        ↓
Ali starts fresh review
        ↓
reviewer resolves + rechecks base/head
        ├── FIX → same PR → STOP → fresh review
        └── ACCEPT → reviewer posts acceptance marker on PR
                         ↓
              Ali tells original session "accepted"
                         ↓
              original session validates marker
              + bounded closeout on SAME PR
                         ↓
                    CI + final recheck
                         ↓
                 Ali human-merges ONCE
                         ↓
                    next phase/state
```

There is **no closeout-only PR** after normal acceptance. Post-ACCEPT Git changes are allowed only for
the bounded closeout bookkeeping envelope defined in construction doctrine. Any substantive change
invalidates ACCEPT and returns the same PR to fresh review.

The reviewer records exact revision identities in the acceptance marker. Ali supplies only the PR or
phase identity and later the word `accepted`; Ali never copies or compares commit hashes. The original
session retrieves and validates the marker itself.

Private GitHub Free still leaves a non-atomic race window between the final agent recheck and Ali's
click-to-merge. Prompt merge minimizes but does not remove it. No paid GitHub feature, manual SHA
handling, or fake-atomic helper is required.

## One-time P7 migration

P7 implementation/corrective PRs #235, #236, #237 and #239 were already merged before this workflow
became current. P7 therefore gets one fresh review of the already-integrated result on current `main`.
This is the only merge-first exception.

Merged PR **#239 remains the durable legacy-acceptance anchor**, generalized into the durable P7
review-state anchor. Every Mode B review posts one `skynet-legacy-acceptance:v1` marker there containing
`scope=SKY-025 P7`, the exact reviewed `integrated_main`, and `verdict=ACCEPT`, `FIX`, or `BLOCKED`.
Ali never carries that revision between chats.

- P8 reads **only the newest** applicable #239 marker. It may start only when that newest verdict is
  ACCEPT **and** current `main` exactly equals its `integrated_main`.
- A newer FIX or BLOCKED supersedes every older ACCEPT even when `main` is unchanged, so an outstanding
  corrective-P7 repair or blocker cannot accidentally release P8.
- Any intervening `main` movement makes the legacy ACCEPT stale.
- ACCEPT creates **no standalone P7 closeout PR**. The natural P8 PR records P7 accepted /
  `current_phase: 7` as opening bookkeeping before P8 implementation.
- FIX creates one bounded corrective P7 PR. That new PR uses the normal open-PR flow above and never
  returns to legacy integrated-main review.

Current P7 invocation:

```text
Read planning/prompts/review.md and review SKY-025 P7 using the one-time already-merged transition.
```

Normal open-PR review needs only a PR number:

```text
Read planning/prompts/review.md and review SKY-025 PR #<number>.
```

Prompts never start another session automatically and authored PRs remain human-merged.
