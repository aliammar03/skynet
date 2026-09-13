# Latest Session Work

> Derived closure handoff. The active directive, current Git/PR state, and accepted evidence win any
> conflict; Main updates this at implementation-ready, paused/blocked, and accepted same-PR closeout.

## Detailed Current State

The entity/cache phase is implementation-ready on **PR #255** and pending one fresh external review.
Accepted numbered progress remains 7/24. The authored PR is open and unaccepted; implementation stops
until a fresh reviewer returns FIX or ACCEPT.

The reviewer records its verdict in a machine-readable acceptance marker. Only the newest applicable
ACCEPT releases bounded closeout on this same PR before one human merge. Private GitHub Free leaves a
non-atomic race window between the final recheck and Ali's merge click; prompt merge reduces but does
not remove it.

The phase replaces shell entity derivation, audit, cache build, and ad-hoc query logic with packaged
Python. Forwarding-only shell entries remain for demonstrated invariant, renderer, and legacy test
callers, with later caller cleanup already assigned in planning.

## Session Changes

- Added packaged entity derivation/audit for guest, service, node, vhost, and network identities.
- Moved route guest resolution from a Bash subprocess to the entity module.
- Added an atomic 14-table SQLite projection and packaged query command; failed rebuilds retain the
  previous valid cache and ordinary query/render callers retain collection freshness gates.
- Kept the two maintained SQL views and migrated operator/query/renderer callers to Python behavior.
- Repaired service auditing so valid standalone Docker containers are ignored while malformed labels
  still fail and undeclared Compose projects remain running-unmapped holes.
- Updated focused behavior, package, shell-caller, and lifecycle-state tests.

## Verification

- Supported full Python suite after the review repair: 329 passed.
- Packaged Nix application/check build: passed; installed console tests: 12 passed.
- Focused entity/cache/route/CLI/collection suites, Ruff, strict mypy, hard invariants, construction, entity,
  repository-surface, and `git diff --check`: passed.
- A complete isolated T1 collection succeeded across all 11 collectors. Freshness, entity audit,
  representative queries, maintained renderer views, and explicit query failure then passed against
  those observations; the temporary worktree and outputs were removed.
- No root grant, T2/T3 action, service/timer change, persistent inventory/docs rewrite, or production
  mutation occurred.

## Pending Work and Blockers

- Fresh external review of PR #255 is required; internal verification is not external acceptance.
- Unchanged baseline temporal-hygiene matches and runbook-catalog drift remain outside this phase.

## Next Entry Point

Read `planning/prompts/review.md` and review PR #255.
