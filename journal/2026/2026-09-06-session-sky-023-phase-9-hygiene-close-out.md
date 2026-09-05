---
date: 2026-09-06
time: 01:26:14            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: SKY-023 Phase 9 hygiene close-out
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-023]         # SKY-###, PR #NNN, ADR NNNN, hosts — anything to cross-link
thread_status: none     # none | open | resolved | unknown; digest shows only explicit open
---

# 2026-09-06 · session · SKY-023 Phase 9 hygiene close-out

## What happened
Completed the final repository-only phase of the reopened directive on vm-skynet-ops. Added
`scripts/hygiene.sh` and the `bin/ops hygiene` entry point. The command runs the temporal-hygiene
and documentation-drift gates, lists unreferenced operator paths as non-destructive review candidates,
and compares current always-loaded/current-authority word and byte counts with the reopening revision
`b6dea99`. Added `tests/hygiene-test.sh` and wired it into pre-commit and CI. Removed the stale
`envsync` claim from the nightly agent prompt.

Started the cold-agent review at README.md, AGENTS.md, and docs/generated/07-context-map.md. The
current runbook catalog routed deploy, LXC/VM provision, restore, publish, backup, and DR to their
current leaf runbooks without opening journal, history, or planning history. `bin/ops hygiene b6dea99`
reported temporal and documentation drift clean; it reported `scripts/collect-firewall.sh` only as an
advisory candidate. It remains the offline/DR parser for a mirrored OPNsense config, not a deletion.

Ran `./.githooks/pre-commit` and `nix flake check --no-write-lock-file`; both exited zero. Nix emitted
the existing `system` to `stdenv.hostPlatform.system` evaluation warning. No host, credential, grant,
or live infrastructure action occurred.

## Actions & outcomes
- `HYGIENE_BASE_REF=HEAD bin/ops hygiene` → temporal and documentation-drift reports passed; test
  confirmed the report headings and clean exit.
- `bin/ops hygiene b6dea99` → current authority measured 80,610 words / 616,458 bytes, down 573 words
  and 3,204 bytes from the reopening revision; always-loaded material measured 3,293 words / 23,184 bytes.
- `./.githooks/pre-commit` → all deterministic repository gates passed, including the new hygiene test.
- `nix flake check --no-write-lock-file` → configuration evaluation passed with the existing rename warning.

## Graveyard — tried & abandoned
- Initial context-budget pipeline used `always_loaded_path && printf` inside a `pipefail` loop; the
  final non-matching path made the report stop after its heading. Rewrote the filters as explicit `if`
  blocks, then reran the report successfully.

## Follow-ups / open threads
- No open hygiene failure. Review `scripts/collect-firewall.sh` only if its documented offline/DR
  trigger changes; `bin/ops hygiene` must not delete it automatically.
