---
date: 2026-09-09
time: 23:30:35            # local HH:MM:SS; orders same-day episodes in the digest
kind: incident          # session | incident | decision
title: SKY-025 P7c shell-only unavailable path
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-025, "PR #237", scripts/collect-network-gear.sh, tests/entity-test.sh]
thread_status: resolved # none | open | resolved | unknown; digest shows only explicit open
# resolves: [<episode-basename>, …]   # optional: close earlier episodes' open threads (append-only-safe)
---

# 2026-09-09 · incident · SKY-025 P7c shell-only unavailable path

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (journal/README.md). Distillation happens at READ time, never here. -->

## What happened
GitHub Actions' shell-only `entity derivation (L0 identity)` job reported
`collect-network-gear reports unavailable without creds — expected [3], got [126]` on PR #237.
The P7a compatibility shim now forwarded to `bin/skynet`; that launcher needs Nix, but the identity
job deliberately does not install Nix. The same command in the NixOS worktree returned 3 because
the Python collector observed the nonexistent test credential file after Nix launched.

## Actions & outcomes
- Ran `OMADA_SECRET_FILE=/nonexistent/omada.env ./scripts/collect-network-gear.sh` in the P7c
  worktree → 3 with the collector's unavailable message.
- Read `.github/workflows/checks.yml` → entity derivation runs only checkout plus
  `bash tests/entity-test.sh`; its separate Python job installs Nix.
- Added the credential-readability unavailable preflight to the compatibility shim, before the Nix
  launcher → it emits the existing unavailable result and exits 3 without opening credentials.
- `bash tests/entity-test.sh` → 47 passed, 0 failed.
- `nix develop --no-write-lock-file -c pytest -q tests/test_omada.py tests/test_collection.py tests/test_recon.py`
  → 78 passed.

## Graveyard — tried & abandoned
Negative results are memory too. Anything attempted that did NOT work — and *why* — so a future
cold agent doesn't re-walk the dead end. Leave a single "— nothing abandoned —" line only if the
episode genuinely tried no path it dropped.

- Depend on the Python collector to provide the unavailable result for every shell caller →
  abandoned because shell-only CI intentionally has no Nix runtime.

## Follow-ups / open threads
- Push the corrective commit to PR #237 and wait for GitHub Actions; P7 remains review pending.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
