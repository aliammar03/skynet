# Latest Session Work

> Derived closure handoff. The active directive, current Git/PR state, and accepted evidence win any
> conflict; Main updates this at implementation-ready, paused/blocked, and accepted same-PR closeout.

## Detailed Current State

SKY-025 P9 is externally accepted at progress **9/24**, completing architecture checkpoint G3. The
newest applicable ACCEPT marker was validated against open PR #256, its reviewed head, and the
unchanged reviewed base. Bounded closeout is staged on that same PR; it is not yet merged.

Every PR is human-merged during the embargo, including generated-only nightly PRs. The nightly
auto-merge executor is fail-closed, while the local secret scan and hard-invariant checker remain.

The P9 package now owns generated factual views, digest, context map, runbook catalog, and read-time
recall. Repository tests, their fixtures, GitHub workflows, and package/pre-commit test execution
remain embargoed; a post-transition review owns the replacement verification architecture.

## Session Changes

- Added packaged render commands for factual docs, digest, context map, and runbook catalog while
  retaining the old shell command names as forwarding compatibility shims.
- Routed current nightly rendering through the package and removed the factual shell implementation
  from the Nix fileset.
- Preserved all nine factual page contracts and the P8 SQLite query path, including the collection
  freshness refusal before any page replacement.
- Made factual publication a complete-tree transaction with backup rollback, preservation of unrelated
  generated pages, and validated node-derived page basenames.
- Added packaged read-time recall with preserved case-insensitive GNU grep ERE semantics, total-match
  reporting, a 20-result display cap, and explicit malformed-expression failure while keeping journal
  creation and writing with their later P21 owner.
- Updated present-tense docs, the P9 directive packet, the migration map, and generator-owned memory
  views for the new command ownership.
- Validated the newest external ACCEPT marker and advanced only bounded phase/planning state to 9/24;
  accepted implementation, runtime/configuration, doctrine, runbooks, behavioral docs, and stable
  memory remain unchanged after review.

## Verification

- Ruff, strict mypy, the Nix package build, shell syntax, secret scan, hard invariants, and diff checks
  passed under the test/CI embargo.
- The installed package rendered digest/context/catalog views, refused stale committed factual
  evidence, and rendered all nine pages from disposable receipt-consistent evidence.
- Normalized old/new factual output matched across all nine pages. Malformed JSON, unsafe node names,
  and an injected second-step publication failure retained the complete prior tree; digest and context
  repeated renders were byte-stable.
- Source and installed recall matched on `[[:space:]]`, `[[:digit:]]+`, ordinary alternation, no-match,
  ranking, a truthful 23-total/20-displayed cap, generated-directory exclusion, and read-only corpus
  hashes. Malformed ERE exited 2, and the compatibility forwarder matched packaged output.
- No root grant, credential access, live collection, T2/T3 action, service/timer change, or production
  mutation occurred.

## Pending Work and Blockers

- PR #256 remains open and requires Ali's one human merge.
- Automated regression protection is intentionally unavailable until the post-SKY-025 redesign.
- Committed collection evidence is stale, so the installed factual renderer truthfully refuses it;
  the successful factual smoke used isolated receipt-consistent evidence.

## Next Entry Point

Human-merge PR #256 once; after it lands, begin SKY-025 P10 from current `main`.
