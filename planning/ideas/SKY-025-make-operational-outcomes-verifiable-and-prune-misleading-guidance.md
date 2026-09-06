---
id: SKY-025
title: Rebuild the Skynet engine in Python
status: draft
horizon: long
created: 2026-09-06
updated: 2026-09-06
phases: 24
current_phase: 0
tier_touched: [T1, T2, T2+, T3]
related:
  - docs/system-design.md
  - AGENTS.md
  - docs/conventions/construction.md
  - planning/README.md
  - "[[SKY-025-progress]]"
---

# SKY-025 · Rebuild the Skynet engine in Python

> One small Python operations application; fewer moving parts, trustworthy outcomes, easy automation.

## 1. Mandate and boundaries

Rework the whole repository around a Python engine: commands, collectors, verification, execution,
backups, recovery, planning utilities, tests, agent configuration, doctrine, runbooks, templates,
packaging, and schedules. Every live surface is reviewed; not every file needs rewriting.

Ali accepts Skynet/service downtime throughout. Replace components directly; temporary breakage is
acceptable and must be recorded. No rolling deployment, dual production engines, compatibility
framework, or availability-preserving migration. Retain a shell shim only for a demonstrated external
caller or rescue requirement, with an owner and removal condition.

Downtime does not authorize loss of payload, backup deletion, secret exposure, or wider privileges.
Keep data/keys/state recoverable, preserve a human recovery path outside the ops VM, and retain existing
T2/T2+/T3 boundaries and human merges. This PR plans the overhaul; it does not stop services.
Routine scoped downtime needs no repeated permission once a phase's live plan is authorized.

**Keep the right languages/tools:** Python for procedural logic; Nix for hosts/packages/timers;
OpenTofu for resource declarations; Compose/Caddy for services/routes; SQL for useful queries;
Markdown for decisions and procedures. Keep Git, SSH, sops, restic, rclone, PBS, and deploy-rs as tools.
Do not translate declarative configuration into imperative Python or rebuild those tools.

**YAGNI:** one package, one CLI, ordinary functions/modules, synchronous execution first. Add bounded
concurrency only for measured independent I/O. No daemon, web UI, app server, scheduler, queue, plugin
system, generic workflow/rollback framework, distributed locks, new database, or new agent framework.
Reuse systemd and native subagents. JSON evidence/files and an existing SQLite cache suffice.
Shared helpers need real callers. Dependencies need a concrete job; stdlib first, not stdlib at all costs.

## 2. Target shape and engineering rules

`src/skynet/` holds a thin CLI, clients, collectors, workflows, renderers, and small shared helpers;
`tests/` holds behavioral tests/fixtures; `pyproject.toml` defines the package. Exact boundaries and
CLI names are settled by the first working slice, not an elaborate upfront schema.

- Expose coherent `skynet collect|verify|deploy|backup|restore|tofu|nightly|doctor|plan` commands as needed.
  Help documents arguments; runbooks document decisions and recovery. Humans and agents use the same CLI.
- Define explicit success/failure/unavailable/skipped/recovery-required results, meaningful exit codes,
  and optional JSON. Unknown/empty/stale is never healthy. Keep output contracts small and tested.
- Validate external data; use argument arrays, explicit timeouts, checked results, and redacted errors.
  Retry reads selectively. A timed-out write may have succeeded: reconcile before retrying.
- A write records target, source/plan identity, completed steps, verification, and needed recovery.
  Use a local lock only where overlap can corrupt state. No blind restart of interrupted writes.
- Preserve scoped credentials, TLS verification, excluded guests, saved-plan checks, and grant boundaries.
  Python modules are not security boundaries. Existing auto-merge authority never expands by translation.
- Package the runtime/dependencies with Nix; use one reproducible development/production dependency
  story. No production pip/npm installation, model-ID guessing, or competing package owners.
- Test real decisions with fake external boundaries. Use recorded response fixtures, temporary files,
  and disposable targets; do not mock away the operation being verified. Type-check and lint in CI.
  Port useful old assertions; delete implementation-mirroring tests instead of recreating them.
- Update a component's callers, tests, runbooks, and doctrine with its replacement. Current docs state
  implemented behavior only; evidence/history belongs in journal/git, future work in this directive.

## 3. Phase-specific leads and Luna workers

**Execution lead:** use the model/effort in the phase table. **Merged-result review and next-phase
planning:** a fresh Astra Medium session for every phase, including phases implemented by Astra.
These are workload-based starting recommendations, not benchmark equivalences. Phase review may
change the next recommendation from observed results; record the reason in that phase's work packet.

Terra High is the default implementation lead. Sol Low handles the defined rendering/documentation
passes. Astra Medium owns foundational design and consequential recovery/policy work. If a Terra/Sol
phase exposes unresolved architecture, privilege, or recovery decisions, stop that decision and hand
it to Astra Medium; do not spend repeated worker retries guessing. No automatic model router.

**Workers: Luna**, native tooling, at most two active workers, one level deep. Luna Medium for
inspection; Luna High for scoped implementation. These phase roles replace the old fixed Terra/Sol
routing and the overhaul's Astra-only execution rule. Phase 1 aligns config, launcher and tests.
Verify actual identifiers in the installed harness; never silently substitute. If unavailable,
mark routing blocked and ask Ali to select an available identifier or update the harness.

The execution lead owns decomposition, integration, verification and PRs within the approved packet.
Astra owns cross-phase interfaces, unresolved recovery/policy decisions, independent acceptance and
next-phase definition. Delegate bounded work proactively when worthwhile; do tiny jobs locally.
Luna gets only: `Goal | allowed files | interface/inputs | acceptance checks | exclusions`.

Workers do not redesign, spawn helpers, commit/push/merge, handle secrets, or touch production.
Use non-overlapping files; separate worktrees only when concurrent edits need them. Return:
`changed files | checks/results | unresolved issues`. The execution lead inspects the diff and
reruns relevant checks; a worker's completion is not phase acceptance. No full-repo dumps or
transcript handoffs; load this directive, current phase, and relevant files only.

## 4. Rolling plan and review gates

**Each numbered phase is 1–2 hours of implementation**, excluding waiting for merge. Split an oversized
phase into lettered slices before work; each slice gets its own PR/review. The table is a route map,
not permission to execute unspecified work. Only Phase 1 is fleshed out now.

For every phase: implement → relevant checks → PR → Ali merges → review the actual merged result.
A fresh Astra Medium reviewer reports **accept**, **fix before continuing**, or **blocked**. Fixes get a bounded PR and
another review. Only after acceptance flesh out the next phase with exact files, interfaces, worker
packets, commands/checks, grants if any, and exit criteria. Do not roll into dependent implementation
just because a worker or CI says done. Ali can paste the review prompt below in a fresh session here.
Architecture checkpoints **G1–G6** additionally reconsider the remaining roadmap and prune unnecessary work.

| Phase | Execution lead | Bounded outcome / main surface | Depends on; exit evidence |
|---|---|---|---|
| 1 | Astra Medium | Repo disposition, minimal Python doctrine, phase-specific lead/Luna routing, overlap decisions | Current main; complete surface map + checked agent config. **G1** |
| 2 | Terra High | Installable Python CLI, Nix package/dev environment, test/lint/type-check CI | 1; packaged help + one command work in clean environment |
| 3 | Astra Medium | First vertical slice: Proxmox read collection → validated inventory → readable summary | 2; real default path handles success, timeout, malformed and absent data. **G2** |
| 4 | Terra High | Remaining core/network Proxmox and ACL collection; shared client only where useful | 3; both node shapes + existing invariants preserved |
| 5 | Terra High | PBS and Docker inventory | 4; backup/container signals and unavailable/stale cases verified |
| 6 | Terra High | DNS and OPNsense/firewall read collection | 5; scoped reads, TLS, response validation, no write creep |
| 7 | Terra High | Omada, certs, routes, recon | 6; live/static provenance and vantage explicit; fixtures cover parsers |
| 8 | Terra High | Entity derivation/audit, SQLite cache and queries | 7; identity exceptions preserved, stale inputs cannot look fresh |
| 9 | Sol Low | Docs/digest/context/catalog rendering; journal/recall helpers | 8; deterministic views and usable cold-start context. **G3** |
| 10 | Terra High | Python deployment health and reachability verification | 9; SSH failure, empty/partial sets and wrong revision fail |
| 11 | Terra High | Arcane deploy/env/sync sequence and reviewed rollback preparation | 10; exact source, atomic env, failures/flags truthful |
| 12 | Terra High | Publishing: Caddy routes, Authentik scoped operations, DNS coordination | 11; internal/public/auth paths verified from correct vantage |
| 13 | Astra Medium | Saved-plan parsing, scope/action/exclusion policy in Python | 12; mixed create/update refused, protected targets refused before writes |
| 14 | Astra Medium | Snapshot/apply/task completion, partial failure and recovery evidence | 13; failed rollback cannot erase state; interrupted writes stop safely. **G4** |
| 15 | Terra High | Restic setup, target selection, consistency method, local scheduling | 14; init/auth/timer/path/volume failure cannot report success |
| 16 | Terra High | PBS off-site transfer preflight and retention semantics | 15; wrong/missing/empty source never deletes backups; stable source proven |
| 17 | Astra Medium | Service restore and guest/core/network recovery procedures | 16; isolated data restore + correct config/ownership; T3 explicitly labelled. **G5** |
| 18 | Astra Medium | Provision/onboard VM/LXC, pins, age identity and workstation grant tooling | 17; API/deploy/bootstrap paths agree, keys stay human-held where required |
| 19 | Terra High | OS-aware guest updates and required host-local backup/rescue packaging | 18; NixOS/Debian paths distinct; rollback failure stops affected workflow |
| 20 | Astra Medium | Nightly collect/report/evidence/PR and exact-PR auto-merge gate | 19; one sequence, bounded engine attempts, no repeated writes, authority unchanged |
| 21 | Terra High | Planning/scaffolding, repository hygiene and invariant gates; CI unification | 20; metadata/links/tests agree; meaningful gates replace shell doctrine |
| 22 | Sol Low | Whole-repo prune: docs, agent shims/config, templates, Nix/Tofu/Compose callers, obsolete scripts | 21; disposition map has no unresolved live caller or duplicate implementation |
| 23 | Terra High | Install/restart the Python engine and intended services; staged operational acceptance | 22; packaged CLI, schedules, collection and one approved write work. **G6** |
| 24 | Astra Medium | Cold-start/recovery rehearsal, final fixes and archive | 23; final acceptance below; honest residual limitations |

Phases 12, 17, and 18 are especially likely to need lettered slices after inspection. Shared clients
may move earlier when a real consumer needs them. Preserve dependency order, not arbitrary numbering.
Do not add a new live OPNsense writer or finish unrelated fleet migrations under this overhaul.

## 5. Phase 1 — ready to execute (~1–2h)

**Goal:** make the rebuild's boundaries concrete and remove instructions that force Bash or wrong models.
**Scope:** T1 repo work only. No service shutdown, production credentials, or implementation rewrite.

1. Rebase work on current main; read the constitution, AGENTS, conventions, CLI/config, schedules,
   and active directives. Record baseline SHA. Confirm no overhaul phase has already landed.
2. Create one compact `planning/sky-025-map.md` disposition table, grouped by subsystem. Account for
   tracked executable/config/docs/test families and remote-installed scripts. Columns:
   `surface | migrate/retain/delete | replacement/owner | callers | phase | verified/blocked`.
   Enumerate files once with git; inspect timers, hooks, Nix activation, Docker/SSH callers, templates,
   workstation utilities, generated outputs, and rescue paths. Record known ignored/local runtime
   state and install locations by metadata only; do not read secrets. Unknown remote state is a blocker
   for its deployment phase. Literal-reference orphan search is advisory only.
3. Resolve duplicate ownership with SKY-005/006/012/015/016/017/018/020/023/024: this overhaul owns
   engine replacement and its existing correctness findings; preserve unrelated feature/migration
   work. Add short cross-links/dependency notes where needed; do not falsely complete those directives.
4. Align `AGENTS.md`, constitution/operator contract, relevant conventions, `.codex/`, `.claude/`,
   `bin/agent`, and routing tests to phase-specific execution leads + Astra review + Luna workers and language-neutral capability
   rules. Prefer changing existing config over adding another launcher. Strip benchmark/provenance
   narration. Keep trust/gates intact; describe Bash as current where it still runs, Python as the
   chosen new-code convention, and the transition only in planning.
5. Record proposed CLI/package boundaries and external output contracts in the map, at most a few
   paragraphs. Decide which generated formats must survive and which may be regenerated; no blanket
   backwards compatibility. Preserve journal and key/state recovery locations.
6. Land the map, contract/config changes, and Phase 1 evidence in one PR. After merge, stop for G1;
   the reviewer accepts/amends boundaries and then writes the executable Phase 2 work packet.

**Worker packets:** Luna A inventories executable/caller families read-only; Luna B checks doctrine,
config/test contradictions and directive overlap read-only. Astra integrates the map and owns any
policy/config edits. If editing is delegated, supply exact file ownership and accepted wording first.

**Checks:** model-routing dry-runs/tests, helper-cap/sandbox assertions, invariant/secret checks,
planning metadata/links, and diff review. Do not disable a safety check to make language changes pass;
update an obsolete shell-only expectation with an equivalent behavioral check.

**Exit:** all tracked families have a disposition; external installs/callers and unknowns are visible;
All recommended lead/worker model-effort combinations resolve as intended; no privilege widening; no future capability claimed live;
Phase 2 remains unimplemented. Unknown remote state is recorded, not guessed.

## 6. Carry forward the original review as acceptance cases

Source review baseline `749f08a`; merged original directive #207. The full original findings remain
in git. All 19 shell suites returned 0, with SQLite checks skipped; local stubs still reproduced F1,
F3, and masked initialization in F4. No live/Nix/Tofu verification was claimed.

| Finding | Must prove in replacement | Owner phases |
|---|---|---|
| F1 false healthy on SSH failure/empty containers | Transport, required set and health independently checked | 3, 10 |
| F2 ignored deploy errors / mixed revisions / misleading no-deploy | Consistent revision/env; failed API or timeout nonzero; flags match behavior | 11–12 |
| F3 whole-state restore after mixed guest create/update | Refuse mixed actions; retain partial resource tracking; verified recovery only | 13–14 |
| F4 hidden backup init/timer/target failures | Required selection complete; auth/init/timer failures stop honestly | 15 |
| F5 hot DB backup and inconsistent restore revision | Tested dump/quiesce method; staged restore preserves prior data/config | 15, 17 |
| F6 apt-only fleet / wrong DR authority | OS-aware actions; failed rollback stop; correct destination access/T3 | 17–19 |
| F7 empty-source destructive PBS mirror | Source identity/stability and deletion guard; copy integrity ≠ restore proof | 16–17 |
| F8 stale/missing collectors reported OK | Validated atomic outputs, explicit freshness/unavailability | 3–9 |
| F9 npm updater competes with Nix | One package/config owner; remove updater/timer and model-self-query | 2, 20–22 |
| F10 incident narratives evade hygiene | Remove named old-timeout/A6/token-budget stories; semantic review | 1, 21–22 |
| F11 repeated rules, stale rollback/metadata/phase claims | One authority per rule; truthful help/runbooks/frontmatter | 1, 21–24 |

## 7. Pause, recovery, and completion

Build in a checkout not consumed by live timers/reconcilers. Before editing or installing into their
active checkout, or beginning the first live phase, agree affected targets; capture protected data/state recovery points and
verify the workstation can rebuild/reach the system without the ops engine. Record the survival-kit
reference, access check, and concrete recovery command/test in the map without secret contents. Record and pause only
schedulers/reconcilers that could race the work; do not stop the active construction workstation or
remove its only access path. Services may remain off across phase reviews. Track what's stopped and
restore intended schedules at acceptance, not blindly every timer found on disk. Before G5 closes,
name the bounded acceptance targets in the map: required services, backup jobs, representative approved
write and isolated restore target. Phase 23 verifies that set; it does not expand into new lab projects.

Code rollback uses git/Nix releases; interrupted infrastructure/data writes require recorded recovery,
not a blind git revert. No requirement to keep the old engine operational or maintain parallel engines.
Live root/T3/destructive actions still need their existing scoped grant/checkpoint.

**Done means:** the disposition map is closed; Python owns useful procedural logic; retained shell
has a concrete rescue/bootstrap reason; one CLI/package/config owner; tests exercise real failure
boundaries; relevant Nix/Tofu/Compose checks pass in a capable environment; docs match installed commands;
all F1–F11 cases have evidence or explicitly accepted limitations; no duplicate engines or dead schedules;
intended services/backups are restored; a cold operator can diagnose and recover from git + survival kit.
An unperformed destructive/full-core drill stays explicitly unverified, not silently waived as passed.

**Close each phase:** PR with result/checks/limitations → Ali merge → independent review → update this
file (`current_phase` = accepted phases, date/status), map and roadmap; journal raw evidence. Keep
`SKY-025-progress` as a compact pointer when memory is available, never required to resume. No extra
tracker or repeated copies of the plan. Implementation-complete/review-pending is not accepted/done.

## 8. Execute / review / continue prompts

**Start:**
```text
Resolve SKY-025 with bin/plan show SKY-025. Read it and AGENTS.md; use bin/plan start SKY-025 if needed.
As Astra Medium, execute only the detailed Phase 1, using at most two scoped Luna workers.
Follow its checks and open its PR. Do not self-merge or start Phase 2. Report the review handoff.
```

**After Ali merges a phase:**
```text
As a fresh Astra Medium reviewer, review SKY-025 Phase <N> at merged commit <SHA> against its exit criteria and disposition map.
Inspect implementation and tests, not just the prior report. Return accept / fix / blocked with
concrete evidence. If fixes are needed, scope their PR and stop. If accepted, update progress and
flesh out only the next 1–2h phase with exact files/interfaces, Luna packets, checks and live boundaries.
At a G checkpoint, prune/reorder the remaining roadmap from results. Do not implement the next phase.
```

**Continue after the next packet is reviewed:**
```text
Continue SKY-025 at its next detailed, approved phase using its table's execution model/effort and
scoped Luna workers. Confirm the selected model matches the packet; do not silently substitute.
Load only the directive, map and relevant files. If the next phase is still outline-only, stop for
its review/expansion. Execute its bounded scope, verify, open a PR and hand back for merge/review.
```

## 9. Status

- 2026-09-06 — Original correctness directive merged in #207; no implementation phases completed.
- 2026-09-06 — Reworked by Ali's instruction into a Python engine/repository overhaul, 24 provisional
  phases with rolling elaboration, Astra Medium/Luna construction, and accepted service downtime.

- 2026-09-06 — Assigned execution leads per phase: Terra High by default, Sol Low for defined prose/
  rendering passes, Astra Medium for foundations and consequential logic; fresh Astra Medium reviews
  every merged phase and defines the next packet. Luna workers remain scoped.
