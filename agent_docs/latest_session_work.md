# Latest Session Work

> Derived closure handoff. The active directive, current Git/PR state, and accepted evidence win any
> conflict; Main updates this at implementation-ready, paused/blocked, and accepted same-PR closeout.

## Detailed Current State

SKY-025 P11 is implementation-ready on existing PR **#259** after repairing the fresh review's FIX
findings and is pending another completely fresh external review. Accepted progress remains **10/24**
and architecture checkpoint G3 remains complete. The old ACCEPT reviewed the superseded Arcane Git
Sync architecture and is stale after substantive head movement.

The packaged deployment owner resolves one exact local branch head, prepares its complete service
subtree and layered environment as an immutable protected generation, activates it directly through
the existing `svc-ops` Docker Compose path under a per-service lock, verifies Docker generation
identity, complete health, and DMZ/TLS routes, and only then promotes stable. Arcane is observation
and a migration guard; enabled auto-sync refuses activation before a Compose write. Runtime rollback
activates and verifies a retained generation and never changes authored Git.

## Session Changes

- Added `generation.py`, `activation.py`, and `deploy.py` as the small synchronous deployment owner;
  removed the Arcane repository/sync/redeploy implementation from `gitops.py`.
- Made preparation read Git objects from the exact selected branch head, reject unsafe trees, decrypt
  only in local memory, stream plaintext through bounded SSH stdin, validate Compose in remote staging,
  and atomically publish an immutable generation with a non-secret release manifest.
- Added protected filesystem state, atomic mutable metadata, operation records, remote `flock`, Docker
  label reconciliation, same-generation recovery, independent verification, stable promotion, and
  explicit retained-generation rollback.
- Adapted P10 verification from Arcane Git Sync identity to release-manifest and independently observed
  Docker generation identity while retaining its complete health and route/TLS safety contract.
- Reduced the legacy deploy and rollback shell names to thin package forwarders, updated the Nix
  closure, current design/runbooks/Compose guidance, directive/map, ADR, and agent memory.
- Preserved all pre-existing generated/inventory/drift worktree entries outside P11 ownership.
- Preserved committed runtime modes in published generations while keeping `.env` and metadata
  protected; retained reuse now rejects byte or mode drift.
- Required `rollback --apply` to reconstruct the selected historical commit and compare its complete
  subtree, effective environment, modes, and manifest before activation.
- Bound deployment route selection and Compose address mapping to the exact expected Git revision so
  dirty worktree edits cannot turn a required route into `skipped`.

## Verification

- Independent Testers passed the required disposable preparation, activation/reconciliation,
  verification/promotion, rollback, and integration cases after their findings were repaired. These
  include dirty-tree isolation, atomic failure, secret custody, idempotence, path safety, lock and
  dual-writer refusal, coherent OLD→NEW application, transport ambiguity, same-generation recovery,
  stale metadata, incomplete/unhealthy projects, failed-candidate retention, and no Git mutation.
- The live T2 `librespeed` canary used the existing `svc-ops` Docker capability and persistent protected
  home. Arcane auto-sync was disabled and drained, the old exact revision was verified, and direct
  activation used revision `f8072b390c10957a572eda4aa112da0583e46796`.
- The first live verification saw health still starting and correctly withheld promotion. A later
  same-generation reconciliation verified one healthy generation container and the route at HTTP 200
  with TLS result 0, then promoted stable. A subsequent deployment reused the generation without
  changing its container or release manifest; state ended `active=stable` with `previous=null` and
  the retained `.env` at mode `0600`.
- Focused source and installed-package smokes plus Ruff, strict mypy, Python compilation, shell syntax,
  offline Nix build, secret scan, hard invariants, and diff checks cover the embargoed gate surface.
- The latest independent repair evidence covers non-root `0644` config access, retained executable
  mode, exact `.env` mode, retained content/environment/mode tamper refusal, missing historical object,
  pre-activation rollback refusal, zero Git mutation, and dirty-worktree route isolation. The pinned
  cloudflared image was independently inspected with configured user `65532:65532`.

## Pending Work and Blockers

- P11 PR #259 requires a completely fresh review; the prior ACCEPT is unusable for this architecture.
- Other services retain a deliberate migration guard and refuse direct activation while Arcane
  auto-sync remains enabled. P11 did not mass-migrate them.
- Automated regression protection remains intentionally unavailable until the post-SKY-025 redesign.

## Next Entry Point

Read planning/prompts/review.md and review SKY-025 PR #259.
