---
date: 2026-09-09
time: 10:56:35            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: SKY-025 P5a PBS inventory
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-025, planning/sky-025-map.md]
thread_status: open
---

# 2026-09-09 · session · SKY-025 P5a PBS inventory

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (journal/README.md). Distillation happens at READ time, never here. -->

## What happened
Started `phase/sky-025-p5a` in `/tmp/skynet-sky-025-p5a` from remote-main
`faf961ab3accb9466385da32efa9bb6185c77f3b` after the merged P4 ACCEPT planning PR. Replaced
the PBS shell parser, curl client and jq projection with `src/skynet/pbs.py` plus the explicit
`skynet collect pbs` CLI. The retained `scripts/collect-pbs.sh` forwards to the packaged command.

The new collector accepts literal PBS assignments only, normalizes one equals separator to PBS's
colon token separator, keeps the configured connection address distinct from verified SNI, accepts
the existing CA-file trust mode, and pins a fingerprint before accepting bootstrap certificate
material. It retrieves datastore status, namespaces and snapshots with GET-only requests, then
atomically writes the existing group/count/latest-verification shape only after all responses
validate. Default collection now writes `collection-pbs.json` under the existing receipt; default
status requires the PBS marker as well as the four Proxmox markers. No production host or API was
used: fake HTTPS connections, synthetic credentials and temporary repositories were the only
transport/output boundaries.

## Actions & outcomes
- `nix develop --no-write-lock-file -c pytest -q` → 117 passed. This includes actual CLI/fake-HTTPS
  PBS CA/fingerprint SNI paths, malformed/null/timeout retention, valid empty snapshots, latest
  verification projection, literal credential refusal, and default PBS marker failure/refusal.
- `nix develop --no-write-lock-file -c ruff check src tests/test_*.py` → all checks passed.
- `nix develop --no-write-lock-file -c mypy src/skynet` → success, no issues in 7 source files.
- The first Nix test attempt found an unstaged package-source omission; staging the new source/test
  paths exposed endpoint and stale expectation defects, which were repaired before the passing run.
- `nix build --no-write-lock-file --no-link .#checks.x86_64-linux.skynet` → passed the packaged
  outside-checkout smoke and installed behavioral suite.
- `nix flake check --no-write-lock-file --no-build` → passed evaluation; Nix emitted its existing
  `system` rename warning.
- `bin/skynet doctor --json` → runtime success; `collect-status` against an empty temporary repo →
  unavailable, exit 3.
- `.githooks/pre-commit` → all enforced invariant, shell safety, Python, lint and type gates passed;
  the five directive-paused documentation suites were not run. `git diff --cached --check` passed.

## Graveyard — tried & abandoned
Negative results are memory too. Anything attempted that did NOT work — and *why* — so a future
cold agent doesn't re-walk the dead end. Leave a single "— nothing abandoned —" line only if the
episode genuinely tried no path it dropped.

- Preserve the shell collector's per-endpoint `null` fallbacks → abandoned because they could turn a
  failed datastore read into zero snapshots or an apparently verified state.
- Treat fingerprint bootstrap as trust of the observed leaf → abandoned because only the configured
  fingerprint can authorize a bootstrap certificate; the normal verified request follows the match.

## Follow-ups / open threads
- Regenerated digest, context map and roadmap after this entry. Commit, push and open the P5a PR.
  After Ali merges it, detail only P5b Docker; review both P5 slices together before P6.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
