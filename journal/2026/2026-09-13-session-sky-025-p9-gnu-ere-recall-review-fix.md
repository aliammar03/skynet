---
date: 2026-09-13
time: 12:58:47            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: SKY-025 P9 GNU ERE recall review fix
tier_touched: []        # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-025, PR #256] # SKY-###, PR #NNN, ADR NNNN, hosts — anything to cross-link
thread_status: none     # none | open | resolved | unknown; digest shows only explicit open
# resolves: [<episode-basename>, …]   # optional: close earlier episodes' open threads (append-only-safe)
---

# 2026-09-13 · session · SKY-025 P9 GNU ERE recall review fix

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (journal/README.md). Distillation happens at READ time, never here. -->

## What happened
Continued the original P9 session after independent review found that `src/skynet/memory.py` compiled
recall terms with Python `re`, while the established `bin/recall` used case-insensitive GNU grep ERE.
The mismatch changed observable expressions: `[[:space:]]` and `[[:digit:]]+` no longer had their
prior meanings, while Python-only constructs could acquire new meanings.

Changed the packaged Python owner to invoke GNU grep for expression validation and per-file matching.
Terms remain raw OR branches; GNU grep returns matching lines so Python retains ranking, summaries,
token costs, excerpts, truthful total count, and the 20-result display cap. Added GNU grep to the Nix
runtime wrapper so installed behavior does not depend on the host `PATH`. Kept `bin/recall` unchanged
as a forwarding shim. No host, live endpoint, credential, or production state was contacted.

## Actions & outcomes
- Source recall against a disposable corpus → `[[:space:]]`, `[[:digit:]]+`, and the two-term
  `context rot|default-lean` query matched with GNU ERE semantics; no-match exited 0 and malformed `[`
  exited 2 with an explicit error.
- Installed recall with `PATH=/nonexistent` → matched source output for POSIX classes, alternation,
  no-match, cap, and generated-exclusion queries; malformed `[` exited 2.
- A 23-file cap corpus → reported all 23 matching files and displayed exactly 20.
- Ranking corpus → three matching lines ranked before single-line matches; equal hit counts ranked by
  estimated token cost, then path. A single LF-delimited record containing a Unicode line separator
  counted once, matching GNU grep rather than Python `splitlines()` behavior.
- Generated-only `hiddenmatch` → no matches; corpus hashes before and after recall were identical.
- `bin/recall 'context rot' 'default-lean'` → byte-matched the installed packaged command for the same
  checkout.
- Ruff, strict mypy, Nix package build, shell syntax, diff checks, secret scan, and hard invariants →
  passed under the repository test and GitHub CI embargo.

## Graveyard — tried & abandoned
- Python `re` as a replacement for the shell scout's regex engine → abandoned because its dialect is
  not GNU grep ERE and silently changes established retrieval results.

## Follow-ups / open threads
- Push the repair to open PR #256, then stop for Ali to start a new independent review. Accepted
  SKY-025 progress remains 8/24; this session does not accept or merge the phase.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
