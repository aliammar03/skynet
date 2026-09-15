# Latest Session Work

> Derived closure handoff. The active directive, current Git/PR state, and accepted evidence win any
> conflict; Main updates this at implementation-ready, paused/blocked, and accepted same-PR closeout.

## Detailed Current State

SKY-025 P11 Arcane deployment/environment/sync and rollback preparation has its latest review's FIX
findings repaired on PR **#259** and is pending fresh external review. Accepted progress remains **10/24** and
architecture checkpoint G3 remains complete.

The packaged deployment owner selects and reports one exact local branch head, requires a unique
existing Arcane sync whose scheduled activation was already disabled and drained, streams the effective
environment without a plaintext local file, atomically replaces the exact remote project `.env` before
manual source activation, reconciles ambiguous source writes, and requires complete runtime health.
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
- Repaired the review-found source/environment race: `autoSync=false` is now a standing precondition,
  missing-sync bootstrap fails closed, manual sync happens only after the selected environment is
  installed, and `--no-deploy` never repoints or activates source.
- Repaired source-sync admission handling: ambiguous POST/response and non-terminal deadline outcomes
  stop after one POST with inspect-before-retry guidance; bounded retry requires positively newer
  terminal failure evidence. Later failures after `source-synced` report that activation occurred.

## Verification

- The independent Tester passed disposable Arcane HTTP/redirect/redaction, sync create/repoint/pull,
  deploy/no-deploy/gate, cloudflared target, env stdin/atomicity, process-tree timeout, malformed and
  ambiguous evidence, rollback report/prepare/conflict/cleanup, and compatibility-forwarder cases
  after five focused defects were repaired.
- Ruff, strict mypy, Python compile, shell syntax, offline Nix package build, secret scan, hard
  invariants, and diff checks passed under the test/CI embargo.
- A disposable Arcane-equivalent OLD/OLD to NEW/NEW harness passed six normal/no-deploy/refusal/
  failed/ambiguous deploy cases and the affected exact-revision, env atomicity/redaction,
  timeout/process-tree, runtime-health, gate, cloudflared, rollback, forwarder, and package-closure
  checks. NEW source was observed only with NEW environment.
- Focused disposable probes passed admitted-but-unobserved ambiguity, non-terminal timeout,
  terminal-only retry, empty completion-marker refusal, and truthful post-sync identity failure.
- The registered Arcane GitHub credential was updated from the authenticated local GitHub CLI without
  printing or persisting its value; Arcane's repository connection test passed. The approved live T2
  `librespeed` run then synced exact `main` revision `f8072b3`, atomically replaced its 10-key
  environment as `1000:1000` mode `0600`, consumed the redeploy operation stream, reconciled one
  healthy container, and passed the P10 route gate with HTTP 200 and verified TLS. No root grant or T3
  action occurred.

## Pending Work and Blockers

- The one-time T2 migration of legacy `autoSync=true` records must be performed and drained while old
  source/environment still agree before a coupled service revision is exposed.
- P11 PR #259 must be reviewed in a fresh session before acceptance.
- Automated regression protection remains intentionally unavailable until the post-SKY-025 redesign.

## Next Entry Point

Read `planning/prompts/review.md` and review SKY-025 PR #259 in a fresh session.
