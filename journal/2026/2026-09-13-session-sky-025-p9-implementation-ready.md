---
date: 2026-09-13
time: 12:33:38            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: SKY-025 P9 implementation ready
tier_touched: []        # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-025, PR #256] # SKY-###, PR #NNN, ADR NNNN, hosts — anything to cross-link
thread_status: none     # none | open | resolved | unknown; digest shows only explicit open
# resolves: [<episode-basename>, …]   # optional: close earlier episodes' open threads (append-only-safe)
---

# 2026-09-13 · session · SKY-025 P9 implementation ready

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (journal/README.md). Distillation happens at READ time, never here. -->

## What happened
Started P9 from merged `main` commit `250bb48` in the sibling
`/home/aliammar/skynet-sky-025-p9` worktree because the primary checkout contained user-owned
generated inventory and documentation changes. Created `phase/sky-025-p9`; no credential, host, or
live endpoint was contacted.

Added `src/skynet/render.py` and `src/skynet/memory.py`, exposed their commands through the installed
`skynet` CLI, and changed current nightly render callers to invoke that package. The existing renderer
and recall shell names became forwarding shims. The factual renderer retained its nine-page contract,
P8 SQLite query path, and collection freshness refusal. Digest, context-map, and runbook-catalog
rendering moved into the same package. `bin/new journal` and the nightly journal writer stayed in Bash
because the active migration map assigns their ownership to P21.

Companion review found that a node name could escape the generated page directory and that sequential
per-file replacement could expose a mixed factual page set. The implementation now validates every
node-derived basename and publishes a staged complete tree by moving the old tree to a sibling backup,
with rollback if replacement fails. Opened PR #256 at implementation commit `b4d8fbf`.

## Actions & outcomes
- `ruff check src` and strict `mypy src/skynet` → passed.
- `nix build --no-write-lock-file --no-link .#skynet` → passed.
- Installed digest/context/catalog rendering and recall smokes → passed; repeated digest/context output
  was byte-identical, no-match recall exited 0, and malformed-regex recall exited 2.
- Installed factual render against committed evidence → refused with exit 3 because the collection
  receipt is stale; the same installed command against disposable receipt-consistent evidence rendered
  all nine pages.
- Normalized old/new factual renderer comparison → zero differences across all nine pages.
- Malformed JSON, `../../escape` as a node name, and an injected failure after the old tree moved →
  nonzero failure with the complete prior page tree unchanged; unrelated generated content survived.
- Shell syntax, `scripts/secret-scan.sh`, `scripts/check-invariants.sh`, and staged diff checks → passed.
- Original `/home/aliammar/skynet` dirty generated/inventory files → left untouched.

## Graveyard — tried & abandoned
- Building in the primary checkout → abandoned because its unrelated uncommitted generated state is
  user-owned; used the sibling worktree instead.
- Migrating `bin/new journal` and the nightly writer in P9 → abandoned because the accepted caller map
  assigns those mutations to P21; P9 owns journal-derived reads and recall.
- Joining node names directly beneath `docs/generated` → abandoned after review demonstrated path
  traversal; safe page basenames are now validated before filesystem use.
- Replacing factual pages one at a time → abandoned because readers could observe mixed generations;
  complete-tree staging, backup, replacement, and rollback now define publication.

## Follow-ups / open threads
- A fresh session must review open PR #256. Accepted SKY-025 progress remains 8/24 until that review
  records ACCEPT and bounded same-PR closeout advances the directive.
- GitHub CI and automated repository tests remain embargoed. The committed collection receipt remains
  stale, so factual rendering continues to refuse it until a later legitimate collection refresh.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
