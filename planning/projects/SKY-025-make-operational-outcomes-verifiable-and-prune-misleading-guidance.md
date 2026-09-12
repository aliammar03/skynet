---
id: SKY-025
title: Rebuild the Skynet engine in Python
status: in-progress
horizon: long
created: 2026-09-06
updated: 2026-09-12
phases: 24
current_phase: 6
tier_touched: [T1, T2, T2+, T3]
related:
  - docs/system-design.md
  - AGENTS.md
  - docs/conventions/construction.md
  - planning/README.md
  - planning/sky-025-map.md
---

# SKY-025 · Rebuild the Skynet engine in Python

> One small Python operations application. Keep Skynet simple, reviewable, rebuildable, and easy to automate.

## 1. Current state

Accepted numbered progress is **P6 / 6 of 24**.

P7 implementation is complete and already merged in PRs **#235, #236, #237 and corrective #239**.
Those PRs landed under the former post-merge review workflow, so there is no open P7 PR to review.
P7 is therefore the only legacy migration case.

**Single current next action:** start one fresh P7 review using the one-time already-merged transition in
[`../prompts/review.md`](../prompts/review.md). The reviewer inspects the **already-integrated P7 result**
on current `main`, including #235, #236, #237, #239 and later P7-owned changes.

- **P7 ACCEPT** → do **not** create a standalone P7 closeout PR. Start the natural P8 PR; its opening
  bookkeeping records P7 accepted (`current_phase: 7`) before P8 implementation.
- **P7 FIX** → open one bounded corrective P7 PR. It then uses the normal open-PR review → same-PR
  closeout → one-merge lifecycle and never returns to legacy integrated-main mode.
- No implementation packet is executable until P7 receives a truthful ACCEPT.

P8 is prepared below so work can begin immediately after P7 ACCEPT, with the P7 progress transition
recorded at the start of the P8 PR instead of manufacturing a bookkeeping-only PR.

## 2. Mandate and boundaries

Rebuild Skynet's procedural operations engine around one installable Python package under `src/skynet/`
while keeping the tools that already fit their jobs:

- Python for procedural logic, validation, orchestration, collectors, checks, and bounded workflows;
- Nix for hosts, packages, services, and timers;
- OpenTofu for resource declarations;
- Compose/Caddy for services and routes;
- SQL where a query is genuinely clearer as SQL;
- Git, SSH, sops, restic, rclone, PBS, and deploy-rs as external tools.

Ali accepts Skynet/service downtime during this overhaul. Availability-preserving dual engines are not
a goal. Downtime never expands authority: payload/state recovery, secret custody, T2/T2+/T3 boundaries,
human merge, protected guests, saved-plan rules, and grant boundaries remain in force.

### Engineering rules

- Prefer ordinary Python functions/modules and synchronous execution. Add shared abstractions only for
  real repeated callers. YAGNI wins over framework-building.
- No app server, daemon, queue, workflow database, custom agent transport, plugin system, or second
  scheduler. systemd and native Codex subagents already exist.
- External data is validated. Missing, partial, stale, malformed, timed-out, or indeterminate required
  evidence never becomes healthy by default.
- Writes must record target, source/plan identity, completed steps, verification, and recovery state.
  A timed-out write is reconciled before any retry.
- Nix owns production Python packaging. No production pip/npm package ownership.
- Tests exercise behavioral boundaries with synthetic inputs, disposable paths, and fake external I/O.
- Current docs describe current behavior. Raw episodes and superseded process details belong in Git and
  `journal/`, not in this active directive.

The subsystem disposition and external/live blockers remain in
[`../sky-025-map.md`](../sky-025-map.md). That map is supporting scope, not a second progress tracker.

## 3. Construction and review lifecycle

Construction follows [`../../docs/conventions/construction.md`](../../docs/conventions/construction.md).
The active phase chooses Light/Medium/Heavy as appropriate; `.codex/agents/` defines worker models and
efforts. Workers gain no production authority and never merge.

### From P8 onward: one PR, one review loop, one merge per numbered phase

Each numbered phase owns **one open authored PR** targeting `main`.

If a phase needs internal slices:

1. create/update the same phase branch and open phase PR;
2. implement all bounded slices on that same PR; never merge slices independently;
3. when the complete numbered phase is implementation-ready, implementation/fix reports the PR and
   **stops**;
4. Ali starts a fresh reviewer for that open PR;
5. reviewer resolves current target/base + PR head, reviews the integration result, and rechecks both
   immediately before verdict;
6. FIX returns to the same PR; original implementation/fix session republishes and stops again;
7. ACCEPT records the exact last-verified pair and posts a machine-readable `skynet-acceptance:v1`
   marker to the PR conversation;
8. Ali tells the original session only `accepted`;
9. that original session fetches/validates the marker and performs bounded closeout on the **same PR**;
10. after CI and a final base + closeout-delta recheck, Ali human-merges that same PR **once**.

Ali never copies or compares commit hashes. The accepted closeout may change only:

- accepted phase/directive state and archive/planning state;
- `agent_docs/project_progress.md`, `project_diary.md`, `latest_session_work.md`;
- append-only journal closure evidence;
- generator-owned closure views changed solely by the state transition.

It may not change source/runtime/config/tests/invariants/AGENTS/doctrine/runbooks/behavioral docs/stable
agent memory or other substantive work. The sanctioned closeout commit moves PR head by design and does
not itself invalidate ACCEPT. Reviewed-base movement, unexplained head movement, or any substantive
post-ACCEPT delta makes ACCEPT stale and requires fresh review.

Private GitHub Free leaves a non-atomic race window between the final agent recheck and Ali clicking
Merge. Prompt merge minimizes but does not remove it. No paid GitHub feature, manual SHA handling, or
fake-atomic read/check helper is required.

There is **no closeout-only PR** after normal acceptance and no automatic second acceptance review for
a valid closeout-only delta.

### P7 migration exception

P7 predates this lifecycle. Its already-merged state gets exactly one integrated-main review. That
exception cannot be reused by P8+ or by a corrective P7 PR.

Because historical P7 has no open PR, P7 ACCEPT is carried into the next natural P8 PR as opening
bookkeeping. This avoids a pointless closeout-only PR. A legacy P7 FIX opens one corrective P7 PR and
immediately returns to the normal lifecycle above.

## 4. Roadmap

| Phase | Recommended Main | Outcome | Exit evidence |
|---|---|---|---|
| 1 | Medium | Repository disposition + Python doctrine | accepted |
| 2 | Heavy | Installable Python CLI + Nix package/dev/test/lint/type path | accepted |
| 3 | Medium | Proxmox core collection + default freshness | accepted; G2 |
| 4 | Heavy | Remaining Proxmox/network/ACL collection | accepted |
| 5 | Heavy | PBS + Docker inventory | accepted |
| 6 | Heavy | DNS + live OPNsense/firewall observations | accepted |
| 7 | Heavy | Omada + certs + routes + recon | implementation merged; one-time review pending |
| 8 | Heavy | Entity derivation/audit + rebuildable SQLite cache/query | prepared below; blocked only on P7 ACCEPT |
| 9 | Medium | Docs/digest/context/catalog rendering + journal/recall helpers | deterministic views; G3 |
| 10 | Heavy | Deployment health + reachability verification | failures/empty/partial/wrong revision fail |
| 11 | Heavy | Arcane deploy/env/sync + rollback preparation | exact source + truthful failures |
| 12 | Heavy | Publishing: Caddy/Auth/DNS coordination | correct vantages + auth paths |
| 13 | Medium | Saved-plan parsing + scope/action/exclusion policy | unsafe plans refused pre-write |
| 14 | Medium | Snapshot/apply/task completion + partial failure recovery | G4 |
| 15 | Heavy | Restic setup/selection/consistency/scheduling | failure cannot report success |
| 16 | Heavy | PBS off-site transfer preflight/retention | destructive empty-source cases refused |
| 17 | Medium | Service/guest/core/network restore | isolated restore + T3 labels; G5 |
| 18 | Medium | Provision/onboard + pins/age identity/workstation grants | custody and access paths agree |
| 19 | Heavy | OS-aware guest updates + host-local backup/rescue packaging | platform-specific rollback |
| 20 | Medium | Nightly collect/report/evidence/PR/exact-PR auto-merge gate | one sequence, authority unchanged |
| 21 | Heavy | Planning/scaffolding + hygiene/invariant gates + CI unification | meaningful deterministic gates |
| 22 | Medium | Whole-repo prune of obsolete scripts/shims/docs/callers | no duplicate implementation |
| 23 | Heavy | Install/restart Python engine + staged operational acceptance | G6 |
| 24 | Medium | Cold-start/recovery rehearsal + final fixes/archive | maintained docs/style/context gates restored |

Architecture checkpoints G1/G2 are already behind us. G3–G6 remain at phases 9/14/17/23.

## 5. Current gate and prepared P8 packet

### 5.1 P7 migration gate — current action

Start a fresh review chat with:

```text
Read planning/prompts/review.md and review SKY-025 P7 using the one-time already-merged transition.
```

Reviewer resolves current `main` itself, reviews the complete integrated P7 result, and rechecks current
`main` before verdict. Do not ask Ali for a SHA.

P7 ACCEPT alone releases P8. Because no P7 PR exists, the **P8 PR's opening bookkeeping** updates this
frontmatter to `current_phase: 7`, aligns Main-owned `agent_docs` + map/roadmap state, and then proceeds
with P8. No standalone P7 closeout PR is created.

### 5.2 Phase 8 — entity spine + rebuildable query cache

**Status:** prepared, **not executable until P7 ACCEPT**.

**Recommended Main:** Heavy. Use one P8 branch/PR for the whole numbered phase. Internal slices are
working units on that same PR, never separately merged.

**Goal:** replace the remaining shell entity/audit/cache procedures with small Python modules while
preserving the current entity grammar, audit semantics, rebuildable SQLite cache, query behavior, and
freshness gates. Do not create a new persistent database or another source of truth.

#### P8A · Entity derivation and audit

Migrate the behavior currently owned by:

- `scripts/entity.sh`
- `scripts/audit-entities.sh`
- `tests/entity-test.sh`
- entity-related callers in `src/skynet/routes.py`, `bin/ops`, current render/query paths, and tests.

Preferred implementation surface: `src/skynet/entities.py` plus CLI wiring/tests. Keep names small;
do not add an object graph or generic entity framework.

Required behavior:

- preserve the five entity classes: guest, service, node, vhost, network;
- preserve stable IDs and the current naming grammar;
- preserve canonical and legacy VMID↔IP handling, including the ambiguous `10xx` case;
- preserve template, declared-exception, matched, stale, and running-unmapped distinctions;
- a running guest/service that is neither mapped nor excepted remains an audit failure;
- OPNsense presence remains liveness annotation, not identity truth;
- vhost/network unresolved state remains truthful and does not silently become a match;
- consume repo/inventory data only; no network, secret, or mutation authority.

A thin compatibility entry may remain only for a demonstrated current caller and must forward to the
packaged Python command. Update known callers in this phase rather than preserving shell logic for
convenience.

#### P8B · Rebuildable SQLite cache and queries

Migrate the behavior currently owned by:

- `scripts/build-db.sh`
- `scripts/sql/host-map.sql`
- `scripts/sql/vhosts.sql`
- `bin/ops query`
- the database consumer in `scripts/render-docs.sh`
- affected collection/query regression tests.

Preferred implementation surface: one small Python cache/query module. SQLite remains a disposable
`.cache/inventory.db` projection of Git/inventory truth, rebuilt from scratch. It is never authority.

Required behavior:

- preserve the current tables/fields actually consumed by host-map/vhost/query callers;
- preserve entity-keyed joins and authored `lab.json` relationships;
- rebuild atomically enough that a failed rebuild cannot leave a newly claimed valid cache;
- ordinary query/render callers must still require current collection freshness before treating the
  cache as current evidence;
- keep the two maintained SQL query files if they remain the clearest query representation;
- ad-hoc query failure, missing SQLite capability, malformed source data, and rebuild failure must be
  explicit non-success outcomes;
- do not add migrations, a DB service, ORM, cache daemon, or schema version framework.

#### P8 verification

At minimum, before P8 is handed to fresh review:

- focused entity/cache/query behavioral tests cover normal, ambiguous, exception, stale,
  running-unmapped, malformed/missing-source, rebuild failure, freshness refusal, and recovery cases;
- existing entity/query/render consumer behavior is preserved;
- full `pytest -q`, Ruff, mypy, packaged Nix checks, hard invariants, construction gate, relevant shell
  gates, and `git diff --check` pass;
- source and installed-package paths both exercise the Python implementation rather than source-only
  fallbacks;
- no live endpoint, credential, root grant, service/timer, inventory rewrite, or production mutation is
  required for this phase.

**P8 closeout:** when all P8A/P8B work is complete on the same open P8 PR, implementation stops and Ali
starts one fresh P8 review. FIX updates that same PR. ACCEPT posts the acceptance marker; Ali says
`accepted` to the original session; that session stages P8 closeout (`current_phase: 8`, accepted
evidence, release P9/G3 planning) on the **same P8 PR**, verifies the post-ACCEPT delta is closeout-only,
and hands the same PR back for one human merge.

## 6. Carry-forward correctness cases

The original overhaul review identified these failure classes. Replacements must keep their safeguards
or provide a stronger equivalent:

| Case | Required property | Owner phases |
|---|---|---|
| F1 | SSH/container failure or empty required set cannot look healthy | 3, 10 |
| F2 | deploy/API/revision errors cannot be ignored | 11–12 |
| F3 | unsafe mixed infrastructure actions are refused and partial state stays recoverable | 13–14 |
| F4 | backup init/timer/target failure cannot report success | 15 |
| F5 | backup/restore consistency is explicit and tested | 15, 17 |
| F6 | fleet operations are OS-aware and stop on failed rollback | 17–19 |
| F7 | empty/wrong PBS source cannot drive destructive mirror behavior | 16–17 |
| F8 | stale/missing collectors cannot look current | 3–9 |
| F9 | package/config ownership remains singular | 20–22 |
| F10 | current docs stay current instead of carrying incident narration | 21–22 |
| F11 | one authority per rule; help/runbooks/frontmatter stay truthful | 21–24 |

## 7. Live/recovery boundaries

The overhaul can take services down, but cannot destroy the only recovery path. Before live installation
or destructive work, preserve the existing survival-kit, workstation access, protected payload/state,
credential custody, and scoped grant rules from the map and system design.

Git/Nix rollback is appropriate for source/config deployment. Interrupted infrastructure/data writes
require operation-specific recovery evidence, not blind `git revert`.

## 8. Handoffs

### Execute the next authorized SKY-025 packet

```text
Read planning/prompts/execute.md and execute the next authorized SKY-025 packet.
```

Until P7 is accepted, `execute.md` refuses P8 and points to the P7 migration review. After P7 ACCEPT,
that same invocation starts P8 and records P7 accepted/current_phase 7 as opening P8-PR bookkeeping.

### Review a normal open PR

Use for every P8+ phase PR and any corrective P7 PR:

```text
Read planning/prompts/review.md and review SKY-025 PR #<number>.
```

Reviewer resolves/rechecks base+head itself and posts the acceptance marker on ACCEPT. Ali then returns
to the original implementation/fix session and says only `accepted`; that session closes out the same
PR and hands it back for one human merge.

## 9. Progress authority

This file owns current numbered progress. The disposition map owns subsystem/caller/recovery scope.
`agent_docs/` owns compact derived session memory. Git and `journal/` preserve implementation/review
history.

Do not reinsert chronological phase diaries into this active directive. A phase status needs only:
accepted / implementation-ready / review-pending / blocked, its current exit evidence, and one next
entry point.
