---
id: SKY-025
title: Rebuild the Skynet engine in Python
status: in-progress
horizon: long
created: 2026-09-06
updated: 2026-09-09
phases: 24
current_phase: 4
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

**Temporary documentation-gate pause (Ali, 2026-09-08):** during this directive,
`obsidian-hygiene-test.sh`, `documentation-drift-test.sh`, `temporal-hygiene-test.sh`,
`repo-surface-test.sh`, and `hygiene-test.sh` are manual, not automatic pre-commit/CI blockers.
Their scripts remain available; skipped automatic checks are not reported as passing.
Behavioral tests, Python lint/type/package checks, secret scanning, privilege/pool invariants,
construction limits, rollback/provisioning and nightly merge-safety tests remain enforced.
P21–22 adapt or retire obsolete documentation checks; P24 must restore maintained documentation,
style and context-budget checks in hook and CI before marking the directive complete/archived.
Retirement of an obsolete assertion needs an explicit recorded disposition, not a silent waiver.

**Each numbered phase is 1–2 hours of implementation**, excluding waiting for merge. Split an oversized
phase into lettered implementation slices before work. Slices may have separate PRs, but independent
review and acceptance apply to the complete numbered phase, never to individual slices.
The execution lead details remaining slices within that phase's scope; no intermediate reviewer
releases them. Existing human merge and live/grant boundaries still apply. The table is a route map,
not permission to execute unspecified work. Section 5 holds the sole current executable packet.

For every phase: implement → relevant checks → PR → Ali merges → review the actual merged result.
A fresh Astra Medium reviewer reports **accept**, **fix before continuing**, or **blocked**. Fixes get a bounded PR and
another review. Only after acceptance flesh out the next phase with exact files, interfaces, worker
packets, commands/checks, grants if any, and exit criteria. Do not roll into dependent implementation
just because a worker or CI says done. Ali can use the reusable review prompt in §8 in a fresh session.
Architecture checkpoints **G1–G6** additionally reconsider the remaining roadmap and prune unnecessary work.

| Phase | Execution lead | Bounded outcome / main surface | Depends on; exit evidence |
|---|---|---|---|
| 1 | Astra Medium | Repo disposition, minimal Python doctrine, phase-specific lead/Luna routing, overlap decisions | Current main; complete surface map + checked agent config. **G1** |
| 2 | Terra High | Installable Python CLI, Nix package/dev environment, test/lint/type-check CI | 1; packaged help + one command work in clean environment |
| 3 | Astra Medium | P3a core collector in isolation; P3b default-caller integration and freshness | 2; complete vertical slice/default path handles success, timeout, malformed and absent data. **G2** after both slices |
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
| 24 | Astra Medium | Cold-start/recovery rehearsal, final fixes and archive | 23; final acceptance below; restore maintained documentation/style/context gates; honest residual limitations |

Phases 12, 17, and 18 are especially likely to need lettered slices after inspection. Shared clients
may move earlier when a real consumer needs them. Preserve dependency order, not arbitrary numbering.
Do not add a new live OPNsense writer or finish unrelated fleet migrations under this overhaul.

## 5. Phase 5a — PBS inventory (~1–2h)

**Release gate:** execute after Ali merges this P4 ACCEPT planning PR. Accepted progress is
4/24; §9 records the complete review of #220 and #221 at
`29b3af942968953a470c9f6d7a06a5c29ca3f8ec`. P4 packets are preserved in git.
**Lead:** Terra High (`gpt-5.6-terra`, high), retaining the phase-table recommendation.

**Goal:** replace PBS shell collection and its default freshness integration with validated,
atomic Python observations. P5 is split into **P5a PBS** and **P5b Docker** because PBS TLS
pinning and Docker subprocess handling have distinct failure boundaries. The execution lead
details P5b after P5a within the continuation below; review all P5 slices together before P6.

**Exact surfaces:** new `src/skynet/pbs.py`, `src/skynet/{cli,collection,proxmox}.py`
(the Proxmox module only for a shared helper with real callers), `tests/test_{pbs,cli,collection}.py`,
`tests/fixtures/pbs/`, `scripts/collect-pbs.sh`, `tests/collect-pbs-test.sh`,
`nix/packages/skynet.nix`, `flake.nix`, `.github/workflows/checks.yml`,
`.githooks/pre-commit`; `bin/ops`, `scripts/{collect-all,render-docs,nightly}.sh`
only where the evidence/caller contract requires it; `nix/README.md`,
`docs/design/observability.md`, `runbooks/nightly.md`, this directive/map and a raw journal.
Regenerate roadmap/digest/context with their generators.

**Interfaces and decisions:**

1. Add `skynet collect pbs --output <file> [--credentials-file <file>] [--json]`.
   Preserve `inventory/pbs.json`'s host/collected/datastores, status usage and per-group
   identity/count/latest-time/verification fields consumed by the backup renderer.
   Translate the existing namespace/group projection; do not infer verified from a missing
   verification value or confuse zero snapshots with unavailable data.
2. Parse literal PBS assignments without eval/sudo, using the configured default
   `/opt/skynet-ops/secrets/pbs.env`. Preserve `PBS_HOST/TOKEN/PORT/CACERT/FINGERPRINT/SNI`
   compatibility and the existing optional defaults from the shell source. Preserve the
   PBS colon token separator and accepted equals-separator normalization. Redact external
   exceptions and never print the secret. Do not read live files to design the parser.
3. Preserve CA-file and fingerprint trust modes, hostname/SNI verification with the separate
   connection address, the existing pin fallback and verified GET-only/no-redirect behavior.
   A bootstrap certificate is usable only after its configured fingerprint matches; never
   silently trust an observed certificate. TLS mismatch, missing CA, timeout and malformed
   data fail nonzero. Use ordinary functions, explicit deadlines and argument arrays where
   an existing tool is required. No new HTTP framework, insecure mode or dependency update.
4. Require complete validated datastore status and snapshot responses before atomic replacement.
   Empty successful snapshot lists are valid no-backup observations; a missing/null/failed
   endpoint is unavailable, not zero. A failed refresh retains previous bytes. Preserve each
   group's latest verification state and make failed/unverified/unknown distinguishable.
   Fix the touched renderer's null-to-zero fallbacks where they would claim healthy backup
   evidence; no renderer redesign or backup/restore operation.
5. Remove PBS from `REMAINING`; run it exactly once under the existing collection lock and
   durable attempt receipt. Add a PBS marker bound to snapshot hash/time and the same 36-hour/
   nightly cutoff. Default status/query/entity/render require PBS as well as all four accepted
   Proxmox markers. Failed PBS reads permit remaining readers but refuse fresh overall evidence.
   Preserve marker-publication, reader cleanup and receipt regressions. Retain the PBS shell
   entry only as a thin forwarding shim for its documented callers, owned by P22 for removal.
6. Port useful shell assertions to Python and retire the replaced shell test from hook/CI in
   the same slice. Include new modules, fixtures, tests and retained shim in source/installed
   package checks and staged-path/CI triggers. Keep unrelated safety checks enforced.

**Optional Luna High assignment:** after the lead settles the PBS data/TLS interface, delegate
only `tests/test_pbs.py` and synthetic PBS fixtures: group projection, malformed/unavailable
responses, TLS refusal and retained bytes. No production, module edits, secrets, commits or helpers.
The lead owns integration/freshness tests and reviews the complete result.

**Checks/exits:** all must pass before closing P5a:
- `nix develop --no-write-lock-file -c pytest -q`: actual CLI/fake HTTPS covers both trust
  modes and SNI, missing credentials, malformed/null/timeout/partial datastore failure,
  empty valid groups, verification states, atomic retention and recovery; default PBS
  failure refuses ordinary consumers and preserves factual pages.
- `nix develop --no-write-lock-file -c ruff check src tests/test_*.py` and
  `nix develop --no-write-lock-file -c mypy src/skynet`: clean.
- `nix build --no-write-lock-file --no-link .#checks.x86_64-linux.skynet` and
  `nix flake check --no-write-lock-file --no-build`: source/installed checks pass.
- Offline `bin/skynet doctor --json` succeeds; `collect-status` on a disposable repo
  without evidence exits 3. Full staged hook and `git diff --cached --check` pass.
  Keep the five paused documentation suites explicitly unrun and their P24 restoration.

**Boundaries:** isolated construction, synthetic credentials/transports and disposable outputs.
No live PBS/Docker reads are released by this packet; the P4 live-read authorization was scoped
to that review. No root/grant, activation, timer/service, trust/pin/credential change, backup,
restore, prune or payload/state write. Source rollback is git revert. Independent workstation,
state/payload recovery and untested endpoint parity remain prerequisites for live transitions.

**Close-out and P5b continuation:** P5a is slice-complete / P5 in progress, not independently
accepted. Open `SKY-025 P5: collect PBS inventory in Python`; do not merge.
After human merge, the execution lead details only Docker inventory: `src/skynet/docker.py`,
CLI/default marker integration, `tests/test_docker.py` and fixtures, `collect-docker.sh`,
package/hook/CI and affected docs. Preserve host label/context and container/image fields used
by SQLite; use bounded read-only Docker argument arrays, validate JSON lines, distinguish
missing context/failed commands from a valid empty host, retain bytes on partial failure,
and require Docker freshness in default consumers. No Docker mutation or Arcane work.
Run the same package/failure/consumer checks; review both P5 PRs together before P6.

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
| F9 npm updater competes with Nix | One package/config owner; remove updater/timer and model-self-query | 20–22 |
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
intended services/backups are restored; maintained documentation/style/context checks are again
automatic in hook and CI; a cold operator can diagnose and recover from git + survival kit.
An unperformed destructive/full-core drill stays explicitly unverified, not silently waived as passed.

**Close each phase:** PR with result/checks/limitations → Ali merge → independent review → update this
file (`current_phase` = accepted phases, date/status), map and roadmap; journal raw evidence. Keep
`SKY-025-progress` as a compact pointer when memory is available, never required to resume. No extra
tracker or repeated copies of the plan. Implementation-complete/review-pending is not accepted/done.

## 8. Execute / review / continue prompts

Use the [phase handoff workflow](../prompts/README.md): two reusable prompts with standard GitHub
PR bodies. Select the execution model from the current packet; use a new Astra Medium task for
merged-result review. The review/planning PR must be human-merged before its next or fix packet runs.

**Start or continue in the packet's execution model:**
```text
Read planning/prompts/execute.md and execute the next authorized SKY-025 packet.
```

**After Ali merges implementation, in a fresh Astra Medium task:**
```text
Read planning/prompts/review.md and review SKY-025 implementation PR <URL>.
```

## 9. Status

- 2026-09-09 — **P5a slice complete / P5 in progress.** From isolated remote-main base
  `faf961ab3accb9466385da32efa9bb6185c77f3b`, P5a replaces the PBS shell parser/client with
  `skynet collect pbs`. The Python command accepts only literal configured assignments, normalizes
  the PBS token separator, preserves CA or configured-fingerprint trust and separate SNI, performs
  verified GETs, validates every datastore/status/namespace/snapshot response, then atomically
  projects the existing datastore/group/count/latest-verification snapshot. Empty validated groups
  are a zero-backup observation; null, partial, malformed, timed-out or trust-failed data fails and
  retains old bytes. `collect all` obtains PBS once under the existing receipt, writes its own
  hash/time marker, and default status/query/entity/render/nightly consumers require all five
  migrated observations. Failed PBS permits later scoped readers but refuses default freshness.
  The shell entry now forwards to the package; its obsolete shell test left hook/CI with Python
  behavioral coverage. The touched renderer emits incomplete PBS evidence rather than coercing
  nulls to zero. No live PBS/Docker call, credential/pin change, backup/restore/prune, host/profile,
  timer/service, root, grant or production write occurred; rollback is `git revert` and endpoint
  parity plus workstation/state/payload recovery remain unverified. The raw journal records exact
  checks. Accepted progress remains **4/24**. After this PR is human-merged, detail only P5b Docker
  within the released continuation; do not request an independent review until both P5 slices merge.

- 2026-09-09 — **P4 ACCEPT.** Reviewed all P4 slices: [#220](https://github.com/aliammar03/skynet/pull/220),
  merge `67e1471987eb14f2f209db0d6ee4bed57386bd1f`, and
  [#221](https://github.com/aliammar03/skynet/pull/221), merge/main reviewed
  `29b3af942968953a470c9f6d7a06a5c29ca3f8ec`. Packet baseline is
  `d2bbedc649e2b4226a2f1b1721a35febbb6148cd`; no intervening commits beyond those slices.
  Session metadata, installed catalog and launcher dry-run confirm fresh Astra Medium.

  | Full P4 exit | Verdict / independent evidence |
  |---|---|
  | Both node shapes, field compatibility and protected pools | ACCEPT — maintained synthetic projections pass; authorized live reads return core 8 guests/1 pool and network 6 guests/1 pool; 2020/5001/635/837 remain unpooled. |
  | Operate-token selection, permissions validation, retained bytes | ACCEPT — GET-only shared transport inspected; CLI tests plus 32 review probes cover both targets, malformed/null permissions, missing operate token without fallback, timeout/redaction, marker refusal and recovery. |
  | Default routing/freshness and caller integration | ACCEPT — all four hash/time markers require one receipt; both legacy implementations removed; default consumer, initial/late marker, timeout/descendant and recovery regressions pass. |
  | Packaging and enforced safety checks | ACCEPT — 105 pytest cases, Ruff, mypy, source/installed Nix package check, flake evaluation, offline doctor/unavailable status and full staged hook pass. Five paused documentation suites remain unrun. |
  | TLS/API compatibility and authority | ACCEPT — Ali explicitly requested live reads during review; all four packaged CLI reads succeeded using configured credentials and disposable outputs, with verified TLS. ACL policy projections have zero forbidden hits and no unauthorized root allocation. No production write/activation occurred. |

  Findings requiring repair: none. P4a's earlier accidental T1 test reads are recorded in its
  incident journal; its blanket no-live-read status sentence below is incorrect. The repaired
  merged tests use parser inspection and synthetic overrides. This review's four live reads
  were explicitly authorized. Workstation/state/payload recovery and other API parity remain
  unverified; successful observations do not establish service health or restore readiness.
  Accepted progress is **4/24**. Release only §5 P5a with Terra High; PBS/Docker become two
  implementation slices within P5 because their transport/failure boundaries differ. No G
  checkpoint is due and no phase reorder is needed.
  [Raw commands and review evidence](../../journal/2026/2026-09-09-session-sky-025-p4-combined-independent-review.md).

- 2026-09-08 — **P4a slice complete / P4 in progress.** From isolated
  remote-main base `d2bbedc649e2b4226a2f1b1721a35febbb6148cd`, P4a adds the explicit network
  Proxmox collector with its target default credential path, existing literal parser and read-only
  TLS transport. `collect all` runs core and network once with one durable receipt, separate
  hash/time markers, and paired status enforcement for default query/entity/render/nightly callers.
  A failed network refresh or late marker preserves its snapshot yet makes default consumers
  unavailable; remaining scoped readers continue. The retained Proxmox shell entry is a thin
  packaged-command forwarder; ACL shell readers remain unchanged. Synthetic fixtures cover the
  network node shape, protected guests 5001/635/837, empty pools, distinct read/operate tokens,
  failed refresh retention and later recovery. No live credentials, endpoints, activation, timers,
  services, root, pool or ACL action occurred. Source rollback is `git revert`; workstation/state/
  payload recovery and live API parity remain unverified. Local Nix/package/hook checks are recorded
  in the raw journal, including the corrected fake-only default-path tests after an accidental
  T1 observation during validation. Accepted progress remains **3/24**; P4a is complete and P4
  remains in progress pending its human merge, P4b, and one full P4 review.

  **P4b continuation after this PR is human-merged:** inspect only the two retained ACL readers,
  then migrate their operate-token snapshots and paired default freshness markers without changing
  observation credentials, ACL permissions, pool invariants, or any live boundary. Run the scoped
  offline checks, update the same map/journal, and open the second P4 PR; do not request an
  independent review until both P4 slices are merged.

- 2026-09-08 — **P3 ACCEPT / G2 closed with the credential repair in this PR.** Reviewed
  [#215](https://github.com/aliammar03/skynet/pull/215), merge
  `05b6326c46506b1c936fbaae724a083d8a218954`;
  [#216](https://github.com/aliammar03/skynet/pull/216), merge
  `8e6c8502ba7c9ce8e9d39fe9bd6d5fd5a45a36df`; and
  [#218](https://github.com/aliammar03/skynet/pull/218), merge/main reviewed
  `1a08ebc6845f7e75ef29f2a4c3930ca07b9b1d2a`, against P3 base
  `17db700c22cb17ad219655674eada344c215029a`. #214 and #217 supply intervening
  planning changes. The merged base still rejected the shared operate-token assignment;
  Ali authorized its simple repair and P4 release without another review round. Acceptance
  includes this tested repair; it is not a claim that the unrepaired main passed.

  | Full P3 exit | Evidence / disposition |
  |---|---|
  | CLI/data/TLS/atomic retention | ACCEPT — 99 behavioral cases pass; actual CLI with fake HTTPS covers malformed/absent/timeout/redirect/CA failures and retained bytes/times. |
  | Default caller and freshness failure handling | ACCEPT — R1 regression refuses ordinary status/query/entity/render after initial-marker failure, makes no reads, preserves pages and recovers after a complete refresh. |
  | Sequential readers, overlap and bounded cleanup | ACCEPT — real timeout, SIGINT/SIGTERM and early-leader-exit tests reap group descendants before continuation/lock release; failed cleanup quarantines the receipt. Scope is existing foreground readers, not arbitrary daemonizing programs. |
  | Existing credential/caller compatibility | ACCEPT with repair — shared read/operate assignments accepted, only read token used, operate never substitutes for missing read token; duplicate/expression/unknown refusal and redaction retained. |
  | Packaging and repository integration | ACCEPT — source/installed Nix check, Ruff, mypy, flake evaluation, offline doctor/unavailable status and full hook pass; existing consumer field projections and safety suites retained. |
  | Authority and live boundaries | ACCEPT for isolated construction — no production credentials, API, activation, timer, host or protected-data changes. Live TLS/API parity and independent workstation/state/payload recovery remain unverified. |

  **G2 decisions:** retain synchronous ordinary functions and the receipt/hash/time contract.
  Accept 3/24 and release only §5 P4a with Terra High after human merge. Confirm the network/ACL
  slice boundary; move shared credential compatibility into P3 (fixed here), so P4 reuses it.
  No broader framework or roadmap reorder is needed. Preserve the five paused documentation
  suites and P24 restoration requirement. [Raw evidence](../../journal/2026/2026-09-08-session-sky-025-p3-combined-re-review.md).

- 2026-09-08 — **P3 R1/R2 fixes implemented / full P3-G2 re-review pending.** Isolated
  branch `fix/sky-025-p3` starts at `89a1dee3f497df7c8609c8639298f4d3db66d505` (merged
  repair packet #217). A durable local attempt receipt invalidates prior success even when
  initial marker replacement fails. Status tests writable receipt durability and preserves
  existing snapshot hash/time, 36-hour and nightly-cutoff rules. Reader process groups are
  killed/reaped under the collection lock on timeout, interruption and early leader exit;
  unconfirmed cleanup stops/quarantines further collection.
  Lead self-review and regressions cover ordinary default-consumer refusal, later recovery,
  actual descendants/signals, lock lifetime and redaction. Full pytest: 94 passed; installed
  package: 86 passed; Ruff, mypy, flake evaluation, offline launcher and staged hook pass.
  [Raw repair evidence](../../journal/2026/2026-09-08-session-sky-025-p3-freshness-and-process-fixes.md)
  records failed checks/corrections and the worker checkout repair. Ali also requested the next
  phase packet; §5 contains a **draft** P4a/P4b split, pending the fresh merged-result review of
  #215, #216 and this fix. No independent acceptance or P4 implementation is claimed; accepted
  progress stays **2/24**. Live/recovery prerequisites remain unmet and outside this packet.

- 2026-09-08 — **P3 FIX / G2 remains open.** One combined review covers
  [#215](https://github.com/aliammar03/skynet/pull/215), merged at
  `05b6326c46506b1c936fbaae724a083d8a218954`, and
  [#216](https://github.com/aliammar03/skynet/pull/216), merged at
  `8e6c8502ba7c9ce8e9d39fe9bd6d5fd5a45a36df`. Final main reviewed is the latter SHA.
  Packet starting revision `17db700c22cb17ad219655674eada344c215029a`;
  intervening #214 (`f21442c44d34baf71e01ca8938ea1305c82242f6`) supplies the accepted
  P2 review and P3 packet, with no implementation. No post-#216 changes at review.
  Fresh session metadata, installed catalog and review dry-run confirm Astra Medium.

  | Full P3 exit | Verdict and independent evidence |
  |---|---|
  | Packaged core CLI, human/JSON outcomes | ACCEPT — 87 behavioral cases pass; installed package check builds; offline launcher doctor returns runtime JSON, absent status exits 3. |
  | Core validation, TLS/redaction, retained snapshot on endpoint/publication failure | ACCEPT — actual CLI/fake HTTPS tests cover success, timeout, malformed/null/absent data, CA/redirect refusal, late failure and atomic retention. |
  | Consumer field compatibility, Nix/CI/hook coverage | ACCEPT — node/resource/pool/job/task projections inspected; pytest, Ruff, mypy, package and flake checks pass; historical invariant/entity coverage retained. |
  | Default caller integration and failed/stale evidence refusal | FIX R1 — initial marker replacement failure after a successful default run leaves ordinary status at exit 0. Nightly's since cutoff protects only its own pass; ordinary query/entity/render gates still accept the prior marker. |
  | Bounded remaining-reader execution and overlap protection | FIX R2 — real shell/child probe times out and returns failure, then its surviving child writes inventory after collection returned and released its lock. |
  | No live credential, authority, host or operational-data changes | ACCEPT — combined source diff and isolated checks show no activation or production collection; no real API/TLS parity or recovery rehearsal claimed. |

  **Findings:** R1 (P2) at `src/skynet/collection.py:59`, consumed by
  `bin/ops:48`, `bin/ops:54` and `scripts/render-docs.sh:9`; R2 (P2) at
  `src/skynet/collection.py:74`. Concrete probe setup/results and independent commands are in the
  [review journal](../../journal/2026/2026-09-08-session-sky-025-p3-independent-review.md).
  Both PRs' GitHub checks are green; that does not discharge these missing failure cases.

  **G2 decisions:** keep the small synchronous package and explicit observation/freshness contract.
  Repair those contracts before extending collection; release only §5's Astra Medium fix packet.
  Accepted progress remains **2/24**, P4 is unreleased, and G2 acceptance awaits full-phase
  re-review. No roadmap reorder is justified before these repairs. P4–7 retain their collector
  ownership; do not add a generic process/workflow framework. Live API parity and independent
  workstation/state/payload recovery remain unverified prerequisites for the first live transition,
  not results implied by construction tests. Preserve Ali's temporary documentation-gate pause
  and P24 restoration requirement.

- 2026-09-08 — **P3a + P3b implementation complete / full P3-G2 review pending.** P3b starts
  from `05b6326c46506b1c936fbaae724a083d8a218954` (merged #215) in an isolated worktree.
  Default collection uses the Nix package; matching hash/time/result evidence guards default
  core consumers and prevents stale-cache rendering. Synthetic default-path tests, installed
  package checks and offline launcher checks pass. Accepted progress remains 2/24; review
  covers #215 plus the P3b implementation PR together, and does not release P4 automatically.
  Ali's same-phase review correction and temporary documentation-gate pause are included.
  Production API parity and the map's live/recovery prerequisites remain unverified; no
  production credentials, collection, activation or service/timer changes were performed.
  [Raw P3b evidence](../../journal/2026/2026-09-08-session-sky-025-p3b-default-collection-and-freshness.md).

- 2026-09-07 — **P3a implementation complete / P3 in progress.** Isolated branch
  `phase/sky-025-p3a`, base `f21442c44d34baf71e01ca8938ea1305c82242f6`, implements the
  explicit-output core collector, literal credential parser, verified GET-only transport,
  endpoint/field validation and atomic publication. Synthetic CLI tests cover transport/data
  failures and retained evidence; Nix carries the collector suite through source and installed
  package checks. Consumer projections and unchanged live boundaries are recorded in the map.
  No lab call, production credential read, activation or default-caller change occurred.
  Ali explicitly authorized raising the current-authority context budget to 200,000;
  `scripts/hygiene.sh` carries that default and the full pre-commit gate passes. The 6,500
  always-loaded limit is unchanged. Python/package checks pass. Accepted progress remains
  2/24; P3b implementation remains, followed by one full P3/G2 review. Ali clarified that
  independent review is for full numbered phases, not their implementation slices.
  Raw commands, build/test corrections
  and limits are in the [P3a journal](../../journal/2026/2026-09-07-session-sky-025-p3a-isolated-core-collector.md)
  and [budget approval episode](../../journal/2026/2026-09-07-session-sky-025-p3a-context-budget-approval.md).

- 2026-09-07 — **P2 ACCEPT.** Reviewed [implementation PR #213](https://github.com/aliammar03/skynet/pull/213),
  merged into main at `17db700c22cb17ad219655674eada344c215029a`; final main reviewed is that SHA.
  Packet baseline `3373fc887296cb6b32064d867f814c75266fedc5`; intervening #212
  (`cdac8f98a3ea6f4326034b428be67df283e7ac3f`) supplies the P2 packet and review-evidence
  doctrine, with no package implementation. No supplied fix PRs or post-implementation commits.
  Fresh session metadata confirms `gpt-6-astra`, medium; installed catalog and review dry-run agree.

  | P2 exit | Verdict and independent evidence |
  |---|---|
  | Packaged help/doctor outside checkout | ACCEPT — Nix package/check outputs build; help/version/human and JSON doctor run in a temporary cwd with PYTHONPATH unset, version 0.1.0/Python 3.13.15; invalid command exits 2. |
  | CLI/JSON/exit behavior | ACCEPT — 10 behavioral tests pass across module/console runners; human and JSON agree, missing/invalid arguments fail. |
  | Nix ownership and enforced checks | ACCEPT — pytest, Ruff, mypy, packaged checks and flake evaluation pass; source filter contains only pyproject, four modules and CLI tests. Hook checks and CI triggers inspected; deploy-rs outputs retained. |
  | Accurate documentation | ACCEPT — nix/README documents implemented build/dev/check commands and runtime-only scope; layout points to package ownership. |
  | No live/authority/data changes | ACCEPT — complete phase diff contains construction, planning and generated context only; no host activation, credential, timer, service or collector changes. |

  Findings: none requiring P2 repair. Nix host-closure CI was pending when inspected; full host
  build/activation is not claimed. Flake evaluation passed with system-rename, app-meta and custom
  deploy-output warnings. No live calls or recovery drill were required/performed.
  [Raw independent evidence](../../journal/2026/2026-09-07-session-sky-025-p2-independent-review.md).
  Accepted numbered progress is 2/24. Release only §5 P3a with Astra Medium. P3b and G2 remain
  pending; the split bounds foundational code separately from default-caller/live prerequisites.
  No other roadmap reordering or autonomy change; P2 is not an architecture checkpoint.

- 2026-09-07 — **P2 implementation complete / review pending.** From isolated branch
  `phase/sky-025-p2` at base `cdac8f98a3ea6f4326034b428be67df283e7ac3f`, added the source-filtered
  Nix `skynet` package, its `python -m skynet` and console entry points, runtime-only `doctor`,
  behavioral tests, Nix development/check outputs, CI, and staged-hook enforcement. The package
  passes outside-checkout help/version/doctor smoke with `PYTHONPATH` unset; behavioral tests,
  Ruff, mypy, packaged checks, and `nix flake check --no-build` pass. Nix was not activated and no
  host, credential, timer, service, collector, or production data was touched. `current_phase: 1`
  remains correct until a fresh Astra Medium reviewer accepts the merged implementation. Raw command
  evidence and the corrected package-check test split are in the
  [P2 journal](../../journal/2026/2026-09-07-session-sky-025-p2-package-local-cli.md).

- 2026-09-07 — **P1 ACCEPT / G1.** Reviewed [implementation PR #211](https://github.com/aliammar03/skynet/pull/211),
  merged into main at `3373fc887296cb6b32064d867f814c75266fedc5`; final main reviewed is the same SHA.
  Complete phase diff starts at `670f06cfa75ca95a9eac7fdb1d3eb3544272ff1a`; no intervening commits
  or supplied fix PRs. Fresh review session metadata: `gpt-6-astra`, medium.

  | P1 exit | Verdict and independent evidence |
  |---|---|
  | All tracked families have a disposition | ACCEPT — baseline 398 paths match grouped counts; source/caller review covers hooks, Nix, templates, service assets, rescue and ownership notes. |
  | External installs/callers and unknowns visible | ACCEPT — map names remote and recovery blockers; local systemd metadata confirms both timers consume the main checkout. No remote absence inferred. |
  | Recommended model/effort combinations resolve | ACCEPT — installed Codex 0.153.4 catalog supports all five combinations; agent tests 82/82, including native parity and invalid combinations. Dry-runs do not claim all models were remotely executed. |
  | No privilege widening | ACCEPT — constitution/trust diff inspected; invariants pass, construction tests 8/8, worker cap/sandboxes and production gates retained. |
  | No future capability claimed live | ACCEPT — doctrine explicitly distinguishes new Python convention from installed Bash; documentation/temporal/surface/hygiene checks pass. |
  | P2 remains unimplemented; unknown state recorded | ACCEPT — no package, runtime, host or schedule implementation changed in #211; map blocks later live work on named evidence. |

  Findings: none requiring P1 repair. Roadmap, digest and context map regenerate identically at the
  reviewed SHA. No Nix/Tofu apply, remote backup/Arcane verification, recovery drill, or live
  Terra/Sol/Luna High invocation was performed or required for this repository-only phase.
  [Raw review evidence](../../journal/2026/2026-09-07-session-sky-025-p1-independent-review.md).

  **G1 decisions:** accept the compact package/output boundaries and adjacent ownership map. Keep
  dependency order and provisional 24 phases; no evidence yet justifies collapsing later failure/
  recovery work. Bound P2 to package/dev/CI and one runtime-only command. Move F9 updater removal
  wholly to P20–22 so its script, timer and configuration owner change together. P3 settles external
  data contracts. Only §5 is actionable after this planning PR's human merge; Terra High is retained.

- 2026-09-06 — Original correctness directive merged in #207; no implementation phases completed.
- 2026-09-06 — Reworked by Ali's instruction into a Python engine/repository overhaul, 24 provisional
  phases with rolling elaboration, Astra Medium/Luna construction, and accepted service downtime.

- 2026-09-06 — Assigned execution leads per phase: Terra High by default, Sol Low for defined prose/
  rendering passes, Astra Medium for foundations and consequential logic; fresh Astra Medium reviews
  every merged phase and defines the next packet. Luna workers remain scoped.
