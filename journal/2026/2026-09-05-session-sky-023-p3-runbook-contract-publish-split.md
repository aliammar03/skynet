---
date: 2026-09-05
kind: session
title: SKY-023 P3 runbook contract and publish split
tier_touched: [T1]
grants: []
refs: [SKY-023, PR #190]
---

# 2026-09-05 · session · SKY-023 P3 runbook contract and publish split

## What happened

Verified PR #190 merged as `707e402`, fast-forwarded local `main`, and created
`docs/sky-023-p3-runbook-context-cleanup`. This was T1 repository work only: no infrastructure
command, credential read, T2 write, or root grant ran.

Two Luna workers made non-overlapping mechanical conversions. One split
`runbooks/publish-service.md` into a compact router plus `publish/internal-route.md`,
`publish/forward-auth.md`, and `publish/public-tunnel.md`. The other converted every diagnosis and
DR leaf to the standard task shape. The lead standardized the remaining leaves, corrected the
Authentik and Cloudflare materialized-token modes in the new publish leaves to `0400 aliammar`,
removed live historical-directive narration where encountered, added a renderer-owned runbook
catalog, and made the context-map renderer recurse through nested runbook directories.

Every runbook leaf now has `summary`, `trigger`, `tier`, `executor`, and `rollback` frontmatter
and exactly `Preconditions`, `Steps`, `Verify`, `Rollback`, and `Evidence` headings. The catalog and
context map contain every leaf. The publish leaves render at 1,258, 1,502, and 1,495 tokens, below
40% of the old 4,910-token monolith. `bash -n`, catalog/contract assertions, the invariant gate,
every `tests/*-test.sh`, and `git diff --check` passed.

The recursive runbook corpus is now 14,276 words. That does not meet SKY-023's 20%-smaller Phase 3
exit target, so the directive remains at Phase 3; this is a bounded checkpoint, not a close-out.

## Follow-ups / open threads

- Continue SKY-023 Phase 3 with the current-truth/editor sweep and substantive runbook pruning;
  then complete digest/nightly consolidation. Do not mark the phase complete until its corpus-size
  and all remaining exit criteria pass.
- The new catalog renderer and nested context-map discovery need the deterministic regression guard
  scheduled for Phase 4.

## Graveyard — tried & abandoned

- Treating the publishing split alone as corpus reduction was abandoned: independently executable
  leaves improve load scope but add metadata and route-specific context, so the measured corpus grew.
