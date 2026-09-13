---
id: SKY-025
title: Rebuild the Skynet engine in Python
status: in-progress
horizon: long
created: 2026-09-06
updated: 2026-09-13
phases: 24
current_phase: 9
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

Accepted numbered progress is **P9 / 9 of 24**. Architecture checkpoint **G3** is complete.

**Current action:** P9 is accepted and merged. P10 is implementation-ready on PR **#257** and awaits
one fresh external review; accepted numbered progress remains P9 until that review and same-PR closeout.

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
- GitHub CI and automated repository tests are embargoed through SKY-025. Phases record focused
  manual/build/smoke evidence and verification debt without adding replacement test fragments; a
  post-transition repository review owns one coherent test architecture. Every PR, including
  generated-only nightly work, is human-merged during the embargo.
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
10. after retained safety controls and a final base + closeout-delta recheck, Ali human-merges that
    same PR **once**.

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
| 2 | Heavy | Installable Python CLI + Nix package/dev/lint/type path | accepted |
| 3 | Medium | Proxmox core collection + default freshness | accepted; G2 |
| 4 | Heavy | Remaining Proxmox/network/ACL collection | accepted |
| 5 | Heavy | PBS + Docker inventory | accepted |
| 6 | Heavy | DNS + live OPNsense/firewall observations | accepted |
| 7 | Heavy | Omada + certs + routes + recon | accepted |
| 8 | Heavy | Entity derivation/audit + rebuildable SQLite cache/query | accepted |
| 9 | Medium | Docs/digest/context/catalog rendering + journal/recall helpers | accepted; G3 |
| 10 | Heavy | Deployment health + reachability verification | implementation-ready on PR #257; fresh review pending |
| 11 | Heavy | Arcane deploy/env/sync + rollback preparation | exact source + truthful failures |
| 12 | Heavy | Publishing: Caddy/Auth/DNS coordination | correct vantages + auth paths |
| 13 | Medium | Saved-plan parsing + scope/action/exclusion policy | unsafe plans refused pre-write |
| 14 | Medium | Snapshot/apply/task completion + partial failure recovery | G4 |
| 15 | Heavy | Restic setup/selection/consistency/scheduling | failure cannot report success |
| 16 | Heavy | PBS off-site transfer preflight/retention | destructive empty-source cases refused |
| 17 | Medium | Service/guest/core/network restore | isolated restore + T3 labels; G5 |
| 18 | Medium | Provision/onboard + pins/age identity/workstation grants | custody and access paths agree |
| 19 | Heavy | OS-aware guest updates + host-local backup/rescue packaging | platform-specific rollback |
| 20 | Medium | Nightly collect/report/evidence + human-review PR path | one sequence; embargo unchanged |
| 21 | Heavy | Planning/scaffolding + retained hard-safety controls | verification debt remains explicit |
| 22 | Medium | Whole-repo prune of obsolete scripts/shims/docs/callers | no duplicate implementation |
| 23 | Heavy | Install/restart Python engine + staged operational acceptance | G6 |
| 24 | Medium | Cold-start/recovery rehearsal + final fixes/archive | post-transition test/CI redesign handed off |

Architecture checkpoints G1–G3 are already behind us. G4–G6 remain at phases 14/17/23.

## 5. Current P8 packet

### Phase 8 — entity spine + rebuildable query cache

**Status:** accepted and human-merged on PR **#255**.

**Recommended Main:** Heavy. Use one P8 branch/PR for the whole numbered phase. Internal slices are
working units on that same PR, never separately merged.

**Goal:** replace the remaining shell entity/audit/cache procedures with small Python modules while
preserving the current entity grammar, audit semantics, rebuildable SQLite cache, query behavior, and
freshness gates. Do not create a new persistent database or another source of truth.

#### P8A · Entity derivation and audit

Migrate the behavior currently owned by:

- `scripts/entity.sh`
- `scripts/audit-entities.sh`
- entity-related callers in `src/skynet/routes.py`, `bin/ops`, and current render/query paths.

Preferred implementation surface: `src/skynet/entities.py` plus CLI wiring. Keep names small;
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

At minimum, before P8 is handed to fresh review during the embargo:

- focused manual entity/cache/query smoke evidence covers normal operation and the review defect;
- existing entity/query/render consumer behavior is inspected for preservation;
- Ruff, mypy, package build, hard invariants, secret scan, and `git diff --check` pass;
- source and installed-package paths are both exercised without recreating a repository test suite;
- no live endpoint, credential, root grant, service/timer, inventory rewrite, or production mutation is
  required for this phase.

**P8 closeout:** when all P8A/P8B work is complete on the same open P8 PR, implementation stops and Ali
starts one fresh P8 review. FIX updates that same PR. ACCEPT posts the acceptance marker; Ali says
`accepted` to the original session; that session stages P8 closeout (`current_phase: 8`, accepted
evidence, release P9/G3 planning) on the **same P8 PR**, verifies the post-ACCEPT delta is closeout-only,
and hands the same PR back for one human merge.

## 5a. Current P9 packet

### Phase 9 — generated views + read-time recall

**Status:** accepted; bounded same-PR closeout staged on PR **#256** for one human merge.

**Recommended Main:** Medium. Use one P9 branch/PR for the whole numbered phase.

**Goal:** replace the remaining shell implementation of factual docs, digest, context-map, and runbook
catalog rendering plus read-time recall with small packaged Python paths. Preserve generated-view
ownership, collection freshness, raw append-only journal truth, deterministic retrieval semantics,
and explicit failures. Do not migrate the nightly journal writer or general `bin/new` scaffolding;
those remain P20/P21 work.

#### P9A · factual and catalog rendering

Migrate `scripts/render-docs.sh`, its nightly caller, and `scripts/render-runbook-catalog.sh` while
retaining the P8 SQLite host-map/vhost queries. Factual rendering must require receipt-bound current
collection evidence, preserve the existing Obsidian page set and entity-keyed relationships, and never
fall back to retained cache bytes. Malformed input, cache/query failure, or page-generation failure must
return non-success and leave prior generated pages unchanged; stale host pages are removed only after a
successful completed render. Catalog rows remain derived from leaf frontmatter in deterministic order.

#### P9B · digest, context map, and recall

Migrate `scripts/render-digest.sh`, `scripts/render-context-map.sh`, and `bin/recall`.

- Digest and context outputs remain content-stable and atomically published.
- The digest preserves ADR ordering, open-directive pointers, same-day journal ordering by explicit
  `time`, append-only `resolves` handling, explicit-open follow-ups, truthful unknown status, and the
  seven most recent raw episode pointers without mechanically summarizing episodes.
- The context map preserves its explicit loadable sets, frontmatter/heading fallback, pipe escaping,
  byte-derived token estimates, generated-view exclusion of itself, and topic-retrieval pointer for the
  journal rather than enumerating the episodic store.
- Recall excludes generated derivatives, OR-joins case-insensitive regular-expression terms, ranks by
  match count then load cost/path, caps displayed results without misreporting the total, writes nothing,
  and rejects malformed expressions explicitly.
- The raw journal, `scripts/nightly.sh` journal append, templates, `bin/new`, and semantic retrieval
  ambitions under SKY-006 remain outside this migration.

Thin shell compatibility entries may forward to the packaged command until P22, but may not retain
duplicate logic. Current callers and current operational docs use the packaged interface.

#### P9/G3 verification

- Focused manual source and installed-package smoke covers each renderer and recall.
- Normal, empty/no-match, malformed-regex, stale-evidence, malformed-input, and failed-render
  preservation paths are exercised without creating a replacement automated test suite.
- Digest, context map, and runbook catalog are regenerated by their owners; factual pages are
  regenerated only when current collection evidence is available.
- Ruff, strict mypy, package build, hard invariants, secret scan, shell syntax, and `git diff --check`
  pass; unavailable evidence is reported explicitly.
- No credential, root grant, live write, service/timer change, or T2/T3 mutation is required.

**G3 exit:** the packaged application is the single procedural owner for collection, entity/cache/query,
generated Markdown rendering, and read-time recall through P9. Bash retained in this surface is only a
forwarding compatibility entry or the explicitly later-owned nightly/journal orchestration.

## 5b. Current P10 packet

### Phase 10 — deployment health + reachability verification

**Status:** implementation-ready on PR **#257**; fresh external review pending.

**Recommended Main:** Heavy. Use one P10 branch/PR for the whole numbered phase.

**Goal:** make one packaged, report-only verifier prove that the requested Arcane GitOps revision is
live, the complete Compose project is running and healthy, and every declared service route is
reachable with valid TLS from the DMZ ingress vantage. Verification failure never invokes rollback or
changes authored/runtime configuration; P11 owns deployment and recovery orchestration.

Required behavior:

- require an explicit full expected Git revision and match it exactly in both the Git Sync and Arcane
  project observations;
- require one unambiguous successful Git Sync, the matching running project, positive equal
  service/running counts, and a non-empty Docker project observation with the same count;
- require every observed container to be running and healthy; a missing healthcheck is failure;
- validate the complete canonical route observation before selecting service routes, rejecting empty,
  partial, malformed, duplicate, or case-ambiguous route evidence;
- probe each selected route from the Docker `dmz` network through the apps front door with a
  digest-pinned curl image, valid public TLS, and an HTTP response below 500; authentication responses
  such as 302/401 are reachable outcomes;
- report routed and intentionally unrouted services distinctly, preserve safe human/JSON errors, and
  never expose credential values or remote response bodies;
- retain `scripts/deploy-gate.sh` only as a thin current-caller forwarder until P22; do not migrate
  `gitops-deploy.sh` source/retry/env/recovery behavior before P11.

P10 implementation evidence recorded before fresh review:

- the independent Tester passed disposable normal, empty, partial, malformed, wrong-revision,
  unhealthy, TLS/HTTP, identity, timeout, redaction, and compatibility-forwarder cases;
- source and Nix-installed paths passed routed and unrouted live smokes;
- all ten live Arcane projects matched merged P9 revision `c800d58`, all 18 project containers were
  present/running/healthy, eight service routes passed from the DMZ vantage with TLS result 0, and
  `caddy-apps`/`cloudflared` were truthfully skipped as unrouted projects;
- Ruff, strict mypy, Python compile, shell syntax, Nix package build, secret scan, hard invariants, and
  diff checks passed under the test/CI embargo.

**P10 closeout:** implementation stops on PR #257 and Ali starts one fresh P10 review. ACCEPT must be
recorded on that PR before the original session advances `current_phase: 10` and releases P11 through
bounded same-PR closeout.

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

After PR #256 is human-merged once, the next invocation executes P10. Later invocations execute only
the next packet released by this directive's numbered progress and review state.

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
