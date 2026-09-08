---
date: 2026-09-09
time: 00:30:44
kind: session
title: SKY-025 P4 combined independent review
tier_touched: [T1]
grants: []
refs: [SKY-025, "PR #220", "PR #221", server-proxmox-core, server-proxmox-network]
thread_status: open
---

# 2026-09-09 · session · SKY-025 P4 combined independent review

## What happened

Ali requested `planning/prompts/review.md` and a combined review of #220 and "this PR" before
P5. GitHub identified the latter as merged #221. Main was
`29b3af942968953a470c9f6d7a06a5c29ca3f8ec`; #220 merged at
`67e1471987eb14f2f209db0d6ee4bed57386bd1f`. The complete phase diff starts at
`d2bbedc649e2b4226a2f1b1721a35febbb6148cd`, with only those two commits afterward.
The ops checkout had existing generated/inventory edits. Created an isolated worktree at
`/tmp/skynet-sky-025-p4-review`, branch `plan/sky-025-p4-review`, without moving main or
copying local credentials/state. Session turn-context metadata says `gpt-6-astra`, medium;
installed model catalog and `bin/agent review 'SKY-025 P4 merged review' --dry-run` agree.

Inspected combined collector/CLI/default evidence changes, tests, shell forwarding entries,
invariant ACL projections, default query/entity/render/nightly callers and packaging. The P4a
incident records real reads caused by an earlier default-path test. The merged test now inspects
parser defaults, and subprocess tests supply both credential overrides. The old status sentence
claiming no live read is qualified by the new review entry; no incident history was rewritten.

## Actions & outcomes

- `nix develop --no-write-lock-file -c pytest -q` → 105 passed in 17.69s.
- `nix develop --no-write-lock-file -c ruff check src tests/test_*.py` → clean;
  `nix develop --no-write-lock-file -c mypy src/skynet` → six source files clean.
- `nix build --no-write-lock-file --no-link .#checks.x86_64-linux.skynet` → success,
  including the installed-package check derivation. `nix flake check --no-write-lock-file
  --no-build` → success with existing system-rename, app-meta and custom-deploy warnings.
- `bin/skynet doctor --json` → runtime success, Python 3.13.15, package 0.1.0.
  `bin/skynet collect-status --repo /tmp/skynet-sky-025-p4-review --json` → expected exit 3,
  absent receipt/markers. No default collection ran in either repository checkout.
- Wrote `.agent/test_p4_review.py` as disposable independent probes using existing synthetic
  credential/HTTPS fixtures. `nix develop --no-write-lock-file -c env
  PYTHONPATH=/tmp/skynet-sky-025-p4-review/src:/tmp/skynet-sky-025-p4-review/tests
  pytest -q .agent/test_p4_review.py` → 32 passed in 4.91s. Matrix: both ACL targets reject
  null, list, empty map, relative path, non-map grants, boolean/2/string privilege values and
  transport timeout while retaining bytes/redacting the token; missing operate assignment
  makes no request; actual CLI/fake-HTTPS ACL failures retain both files, refuse status, then recover;
  missing/hash/attempt/time mismatch on each new marker refuses status. These probes are not
  counted among the maintained suite and do not change production implementation.
- Ali then said "test the live read too". Announced four scoped T1 reads with configured
  credentials and disposable outputs. `mktemp -d /tmp/skynet-p4-live-read.XXXXXX` produced
  `/tmp/skynet-p4-live-read.W4brpC`. Ran the packaged commands below, all exit 0 at
  2026-09-08T19:30:13Z (2026-09-09 00:30:13 Asia/Karachi):
  `bin/skynet collect proxmox core --output /tmp/skynet-p4-live-read.W4brpC/core.json --json`;
  the equivalent network command; `collect proxmox-acl core` and `collect proxmox-acl network`
  with `core-acl.json` and `network-acl.json` destinations respectively. CLI reports core
  1 node/8 guests/1 pool, network 1 node/6 guests/1 pool, ACL path counts 18 and 2. Credentials
  were consumed by the existing collector only; no secret content was printed or committed.
- Inspected pool/protected-guest projections from those outputs: core ops-managed members
  qemu/10015, lxc/240, qemu/9000, qemu/9090; network ops-managed empty; 2020/5001/635/837
  unpooled. Applied the existing `operate_token_scope` forbidden/root-allocation jq predicates
  to both live ACL files: zero forbidden hits, no unauthorized root allocation. No ACL write.
- P4 ACCEPT, 4/24. Retained Terra High for P5. Reading PBS's fingerprint/SNI/group projection
  and Docker's context/subprocess/SQLite callers justified PBS and Docker slices within P5;
  §5 details only PBS now and defines the same-phase Docker continuation. No G checkpoint due.
  Regenerate roadmap/digest/context through existing tools, then run the full staged hook
  and diff check before publishing; final results are appended below.
- `bin/plan list`, `scripts/render-digest.sh`, `scripts/render-context-map.sh` completed.
  After staging the six review/planning/view files, `.githooks/pre-commit` and
  `git diff --cached --check` exited 0. Hard-law, entity, rollback/provisioning, PBS,
  construction/routing and nightly merge/sequence suites passed. The five paused suites
  stayed unrun. Python checks were run independently above, not inferred from this docs-only hook.
  Final GitHub main recheck still returned `29b3af942968953a470c9f6d7a06a5c29ca3f8ec`.

## Graveyard — tried & abandoned

- Initial probe invocation set PYTHONPATH before `nix develop`; the shell replaced it, causing
  `ModuleNotFoundError: test_proxmox` during collection. Set explicit absolute paths with `env`
  inside the Nix command instead; 32 cases then passed. No collector ran in the failed attempt.
- A combined documentation patch failed validation due to a malformed hunk; reapplied the map
  and fresh journal scaffold separately. No partial changes from the failed patch.
- No implementation defect reproduced. Did not turn live successful observation into a claim
  of service health, restoration readiness or default nightly activation.

## Follow-ups / open threads

- After Ali merges this P4 ACCEPT planning PR, run a fresh Terra High session:
  `Read planning/prompts/execute.md and execute SKY-025 P5a.`
- Workstation access, state/payload recovery, other endpoint parity and host activation remain
  unverified. Five paused documentation suites were not run or counted as passing; restore
  maintained replacements by P24. P4 live authorization does not authorize PBS/Docker execution.
