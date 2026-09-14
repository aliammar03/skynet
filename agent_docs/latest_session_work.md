# Latest Session Work

> Derived closure handoff. The active directive, current Git/PR state, and accepted evidence win any
> conflict; Main updates this at implementation-ready, paused/blocked, and accepted same-PR closeout.

## Detailed Current State

SKY-025 P11 Arcane deployment/environment/sync and rollback preparation is implementation-ready on
`phase/sky-025-p11-deploy` and pending fresh external review. Accepted progress remains **10/24** and
architecture checkpoint G3 remains complete.

The packaged deployment owner selects and reports one exact local branch head, reconciles unique
Arcane identities and ambiguous source writes, streams the effective environment without a plaintext
local file, atomically replaces the exact remote project `.env`, and requires complete runtime health.
Its optional gate invokes the separate report-only P10 verifier. Packaged rollback remains report-only
unless explicitly asked to prepare an isolated local review branch; it never pushes or merges.

## Session Changes

- Added packaged `skynet deploy service` and `skynet rollback service` owners with safe human/JSON
  outcomes and exact source/completed-step/verification/recovery evidence.
- Replaced shell evaluation, unbounded requests, local plaintext env staging, truncating remote writes,
  ambiguous first-match identity, and masked redeploy/restart failures with literal parsing, bounded
  reconciliation, stdin-only secret transit, atomic replacement, unique identity, and failed-closed
  runtime checks.
- Kept P10 verification separate and report-only; `--gate` supplies the selected local branch-head
  revision only after runtime reconciliation.
- Reduced the two legacy GitOps scripts to thin packaged-command forwarders and added the required Nix
  runtime closure for Git, SSH, and sops.
- Updated current design, runbooks, Compose/Nix guidance, and stable agent memory for the packaged
  owner and explicit human-reviewed recovery boundary.
- Preserved all pre-existing generated/inventory/drift worktree entries outside P11 ownership.

## Verification

- The independent Tester passed disposable Arcane HTTP/redirect/redaction, sync create/repoint/pull,
  deploy/no-deploy/gate, cloudflared target, env stdin/atomicity, process-tree timeout, malformed and
  ambiguous evidence, rollback report/prepare/conflict/cleanup, and compatibility-forwarder cases
  after five focused defects were repaired.
- Ruff, strict mypy, Python compile, shell syntax, offline Nix package build, secret scan, hard
  invariants, and diff checks passed under the test/CI embargo.
- The approved live T2 smoke targeted only `librespeed` on `vm-docker-dmz`. Both source and Nix-package
  entry paths failed closed at Arcane source pull because the registered GitHub repository credential
  was rejected; no `.env` replacement, redeploy, restart, rollback branch, root grant, or T3 action
  occurred.

## Pending Work and Blockers

- The P11 branch must be published as one open PR and reviewed in a fresh session before acceptance.
- Successful live deployment evidence is blocked by Arcane's rejected GitHub repository credential;
  changing that credential is outside this phase's authorized scope.
- Automated regression protection remains intentionally unavailable until the post-SKY-025 redesign.

## Next Entry Point

Open/reuse the SKY-025 P11 PR, then read `planning/prompts/review.md` and review that open PR in a
fresh session.
