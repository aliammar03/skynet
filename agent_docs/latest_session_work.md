# Latest Session Work

> Derived closure handoff. The active directive, current Git/PR state, and accepted evidence win any
> conflict; Main updates this at implementation-ready, paused/blocked, and accepted same-PR closeout.

## Detailed Current State

PR **#255** is being republished after Ali imposed a repository-wide automated-test and GitHub CI
embargo for the duration of SKY-025. Accepted numbered progress remains 7/24. The earlier ACCEPT is
stale because this is a substantive post-review change; a fresh review is required after publication.

Every PR is human-merged during the embargo, including generated-only nightly PRs. The nightly
auto-merge executor is fail-closed, while the local secret scan and hard-invariant checker remain.

The P8 entity/cache implementation remains intact. Repository tests, their fixtures, GitHub workflows,
and package/pre-commit test execution are removed as one policy change; a post-transition review owns
the replacement verification architecture.

## Session Changes

- Added packaged entity derivation/audit for guest, service, node, vhost, and network identities.
- Moved route guest resolution from a Bash subprocess to the entity module.
- Added an atomic 14-table SQLite projection and packaged query command; failed rebuilds retain the
  previous valid cache and ordinary query/render callers retain collection freshness gates.
- Kept the two maintained SQL views and migrated operator/query/renderer callers to Python behavior.
- Repaired service auditing so valid standalone Docker containers are ignored while malformed labels
  still fail and undeclared Compose projects remain running-unmapped holes.
- Removed the repository test tree, GitHub workflows, packaged test phase, and test hook wiring.
- Suspended nightly auto-merge and recorded the embargo in constitution, doctrine, runbooks, planning,
  Nix packaging, and agent memory.
- Reconciled remaining present-tense documentation after independent review: current caller maps no
  longer name deleted tests, ADR 0004 now states the suspended decision throughout, and all scanned
  current surfaces agree that every PR is human-merged during the embargo.

## Verification

- Retained secret and hard-invariant controls passed; Ruff, strict mypy, package build, shell syntax,
  diff, and repository-surface checks passed.
- Current-authority scans found no remaining claim that absent GitHub CI is running or that the
  nightly may merge during the embargo; generated digest/context views were refreshed normally.
- Packaged runtime doctor succeeded; direct entity audit reported 39 mapped/excepted/template entities
  with zero holes, and a representative cache query reported 11 containers.
- The prior isolated T1 smoke covered all 11 collectors plus freshness, entity, query, renderer, and
  explicit query-failure paths; it remains historical evidence rather than an active automated gate.
- No root grant, T2/T3 action, service/timer change, persistent inventory/docs rewrite, or production
  mutation occurred.

## Pending Work and Blockers

- Fresh external review of the republished PR #255 is required; the earlier ACCEPT marker is stale.
- Automated regression protection is intentionally unavailable until the post-SKY-025 redesign.
- `bin/ops entities` truthfully refused stale/missing collection receipts, and `bin/ops hygiene`
  retained its existing current-authority budget failure (220,996 estimated tokens vs 200,000).
- Unchanged baseline temporal-hygiene matches and runbook-catalog drift remain outside this phase.

## Next Entry Point

After publication, start a fresh review of PR #255; do not close out from the stale ACCEPT marker.
