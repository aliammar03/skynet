---
date: 2026-09-09
time: 11:25:06
kind: session
title: SKY-025 P5 reviewer repairs and live reads
tier_touched: [T1]
grants: []
refs: [SKY-025, "PR #223", "PR #224"]
thread_status: open
---

# 2026-09-09 · session · SKY-025 P5 reviewer repairs and live reads

## What happened

After the initial review findings recorded in
[the preceding episode](2026-09-09-session-sky-025-p5-combined-independent-review.md),
Ali instructed the reviewer to implement simple fixes itself, perform live PBS/Docker reads,
use Luna workers, and update the review process so reviewers can repair and clear a phase.
This overrides the initial review-only scope and separate fix handoff. No review PR had been
published. I renamed the isolated branch to `fix/sky-025-p5-review`.

I assigned two Luna High workers non-overlapping Docker and PBS implementation/tests.
Neither received credentials, production authority, commits or helper delegation.
After a turn interruption, their partial edits remained but their sessions were no longer
active; I assigned two replacement Luna workers to inspect and finish the same bounded files.
The reviewer retained integration, live reads, package/doctrine updates and acceptance.

## Actions & outcomes

- Before fixes, `bin/skynet collect docker docker-dmz --output
  /tmp/skynet-p5-review-probes.FIhV6e/live-docker-before.json --json` succeeded:
  18 containers, 31 images, collected 2026-09-09T06:22:29+00:00.
- Before fixes, the equivalent `collect pbs --output .../live-pbs-before.json --json`
  failed with `missing or malformed identity/status field`.
  I used the existing verified PBS client for only datastore/status/namespace reads;
  did not print credentials. The returned namespace rows were
  `[{"ns":""},{"ns":"network"},{"ns":"core"}]`, while the parser rejected the
  valid explicit root namespace. Status used/total were integers.
  I sent this response shape to the PBS worker as a synthetic regression input.
- After the namespace repair, `PYTHONPATH=src python3 -m skynet collect pbs --output
  /tmp/skynet-p5-review-probes.FIhV6e/live-pbs-after.json --json` succeeded at
  2026-09-09T06:29:48+00:00: 1 datastore, 152 snapshots, 18 groups; 6 latest states
  `ok`, 12 null/unverified. These are observations, not proof of restore readiness.
- Updated review.md, its workflow README, construction convention and the active directive:
  a fresh reviewer repairs bounded defects with Luna, inspects the results, rechecks the
  affected complete-phase exits, and may accept in the combined repair/review PR. Acceptance
  and the next packet take effect on Ali's merge. Unresolved defects still receive FIX;
  the original implementing lead does not accept its own phase; no self-merge or new
  production authority is introduced.
- Added openssl/jq/gawk/bash as Nix test inputs so synthetic TLS and actual renderer checks
  run in source and installed environments. Runtime dependencies/credentials were not changed.
  Updated touched runtime docs to include Docker freshness and truthful backup verification.

## Graveyard — tried & abandoned

- The initial separate P5 FIX packet was replaced before publication after Ali authorized
  direct reviewer repairs. Its raw counterexamples remain in the preceding journal entry.
- Parallel packaged live invocations printed an ignored Nix evaluation-cache busy warning;
  both completed and returned the results recorded above. No endpoint retry was hidden.
- The first worker pair had unfinished edits after a turn interruption. Replacement workers
  continued the files; no completed artifact was discarded or restarted from scratch.

## Follow-ups / open threads

- Finish full source/installed validation, repeat packaged live observations, then publish the
  combined repair/acceptance PR and P6a DNS packet. No P6 implementation is part of this run.
- Workstation/state/payload recovery remains unverified. No backup/restore/prune, Docker
  mutation, activation, timer/service, root grant or credential/pin change was performed.

## Final integration and disposition

Ali further requested model-agnostic review. Removed the fixed review model/effort from
the launcher, current prompts/handoffs, AGENTS and construction convention. Review defaults
to harness configuration; AGENT_REVIEW_MODEL/EFFORT are optional overrides. Launcher tests:
84 passed; construction tests: 8 passed. Execution-phase recommendations and Luna roles remain.

Final packaged live reads at 2026-09-09T10:52:07+00:00 both succeeded: PBS 152 snapshots,
Docker 18 containers/31 images. An intermediate strict Docker parser rejected optional
Platform:null; required fields remain strict while optional nulls are preserved and tested.
No production inventory was overwritten: all outputs are in the disposable probe directory.

Final `nix develop --no-write-lock-file -c pytest -q`: 144 passed in 21.64s.
Nix source build includes passing Ruff/mypy. Separate installed-package check and full staged
hook were run before publication; five paused documentation suites remain unrun. Flake
evaluation passed with existing warnings. Earlier integration attempts caught a missing test
signal import and empty-tuple type inference; both were fixed. Bare pytest outside Nix lacked
the console command, so its 8 setup errors were not counted as acceptance evidence.

The final Luna test worker edited the main checkout's two test files despite the scoped path.
I inspected its exact diff, transferred the two useful Docker failure/recovery tests to the
isolated worktree, and removed only that worker's test edits from main using an inverse patch.
Main's prior generated/inventory changes remain intact. The final timeout test uses a parent
and grandchild, and the renderer success test counts latest backup groups, not all snapshots.

Disposition: P5 ACCEPT including the repairs in this PR, effective on Ali's human merge.
After merge, use Terra High: `Read planning/prompts/execute.md and execute SKY-025 P6a.`
The old fix handoff in the preceding episode is superseded; no extra P5 review is required.
