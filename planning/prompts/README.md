---
summary: "SKY-025 handoffs: one open PR per numbered phase, durable newest-verdict review state, same-PR accepted closeout, one human merge, plus the one-time legacy P7 gate."
---

# SKY-025 phase handoffs

Governed by the active SKY-025 directive and
[`../../docs/conventions/construction.md`](../../docs/conventions/construction.md).

| Prompt | Use |
|---|---|
| [Execute](execute.md) | Implement/repair the currently authorized numbered phase on its one open phase PR, then STOP |
| [Review](review.md) | Fresh review of an open P8+ phase PR or corrective P7 PR, plus the historical one-time P7 transition |

## Normal open-PR flow

This applies to every P8+ numbered phase PR and any corrective P7 PR.

```text
implementation / repair
        ↓
one open PR for the numbered phase
        ↓
implementation/fix session reports PR + STOP
        ↓
Ali starts fresh review
        ↓
reviewer resolves + rechecks base/head
        ↓
reviewer posts one durable verdict marker
(ACCEPT / FIX / BLOCKED)
        ↓
newest applicable verdict wins
        ├── FIX/BLOCKED → no closeout
        └── ACCEPT → Ali tells original session "accepted"
                         ↓
              original session validates newest marker
              + bounded closeout on SAME PR
                         ↓
                    CI + final recheck
                         ↓
                 Ali human-merges ONCE
```

There is no closeout-only PR after normal acceptance. A newer FIX or BLOCKED marker supersedes every
older ACCEPT, even for the same base/head. A malformed newest applicable marker fails closed. Only a
newest well-formed ACCEPT marker whose reviewed base/head still match the live PR can authorize
closeout.

The reviewer records revision identities; Ali supplies only the PR or phase identity and later the word
`accepted`. Ali never copies or compares commit hashes.

Private GitHub Free still leaves a non-atomic race between the final agent recheck and Ali's click to
merge. Prompt merge minimizes but does not remove it.

## One-time legacy P7 transition

P7 implementation/corrective PRs #235, #236, #237 and #239 were already merged before this workflow.
Merged PR **#239** is the durable legacy P7 review-state anchor. Every legacy P7 review posts one
`skynet-legacy-acceptance:v1` marker there with `verdict=ACCEPT`, `FIX`, or `BLOCKED` plus the reviewed
`integrated_main`.

- P8 reads only the newest applicable #239 marker.
- The newest verdict must be ACCEPT and current `main` must still equal `integrated_main`.
- Newer FIX/BLOCKED supersedes older ACCEPT; later `main` movement also stales ACCEPT.
- ACCEPT creates no standalone P7 closeout PR. The natural P8 PR records P7 accepted /
  `current_phase: 7` as opening bookkeeping.
- FIX creates one bounded corrective P7 PR. That PR uses the normal open-PR flow above and never returns
  to the legacy path.

Legacy P7 review invocation, only while the directive still shows P7 pending:

```text
Read planning/prompts/review.md and review SKY-025 P7 using the one-time legacy transition.
```

Normal open-PR review needs only a PR number:

```text
Read planning/prompts/review.md and review SKY-025 PR #<number>.
```

Prompts never start another session automatically and authored PRs remain human-merged.
