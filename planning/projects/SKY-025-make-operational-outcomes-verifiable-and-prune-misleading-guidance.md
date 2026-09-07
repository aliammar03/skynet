---
id: SKY-025
title: Rebuild the Skynet engine in Python
status: in-progress
horizon: long
created: 2026-09-06
updated: 2026-09-07
phases: 24
current_phase: 2
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
| 24 | Astra Medium | Cold-start/recovery rehearsal, final fixes and archive | 23; final acceptance below; honest residual limitations |

Phases 12, 17, and 18 are especially likely to need lettered slices after inspection. Shared clients
may move earlier when a real consumer needs them. Preserve dependency order, not arbitrary numbering.
Do not add a new live OPNsense writer or finish unrelated fleet migrations under this overhaul.

## 5. Phase 3a — core Proxmox collector in isolation (~1–2h)

**Release gate:** execute after Ali merges this review/planning PR. P2 is accepted in §9.
Reviewed starting revision: `17db700c22cb17ad219655674eada344c215029a`; start from current
remote main containing this packet and inspect intervening changes.
**Lead:** Astra Medium (`gpt-6-astra`, medium), as recommended for P3's external-data contract.
**Goal:** a packaged core-node read collector that validates a complete snapshot, writes it atomically,
and reports collection outcomes truthfully, exercised through the actual command using fake boundaries.

**Slice decision:** separate P3a's collector/data contract from P3b's default-caller integration.
Replacing a live caller also needs package availability, freshness handling by existing consumers,
and the map's unresolved live/recovery evidence. Combining those decisions with the first client is
larger than one packet. The execution lead must detail P3b's packet before implementing it;
P3a does not require an independent review to continue within P3.
P3/G2 is not complete until the integrated default path is independently accepted.

**Exact surfaces:** `src/skynet/cli.py`; new `src/skynet/proxmox.py`,
`tests/test_proxmox.py`, and synthetic `tests/fixtures/proxmox/**`; existing
`tests/test_cli.py`, `nix/packages/skynet.nix`, `flake.nix`,
`.github/workflows/checks.yml`, `.githooks/pre-commit`, and `nix/README.md` as required
to include the new tests/fixtures and checks. Update this directive/map and append a raw journal;
regenerate roadmap/digest/context only with their tools. No dependency or lock refresh expected.

**Read contracts before implementation:** `scripts/collect-proxmox.sh`,
`scripts/collect-all.sh`, `bin/ops`, `scripts/check-invariants.sh`,
`scripts/build-db.sh`, `scripts/sql/host-map.sql`, `scripts/render-docs.sh`,
`docs/conventions/scripts.md`, and `docs/design/observability.md`. Inspect only relevant
inventory schema/field shapes; never fetch or copy live credential material into fixtures.

**Interfaces and work:**

1. Add `skynet collect proxmox core --output <file> [--json]`. Output is required in this
   construction slice so execution cannot silently choose the operational checkout. Help explains
   that the command collects observations, not service-health verification. Keep doctor unchanged.
   Network-node collection, ACLs and all-collector orchestration remain outside this slice.
2. Implement synchronous GET-only HTTPS reads for the existing core snapshot: nodes,
   cluster/resources, pool list and each pool's members, cluster/backup, and per-node recent vzdump
   tasks. Use stdlib HTTPS with verified CA/hostname and explicit bounded timeouts; reject redirects
   rather than forward the Authorization header to another destination. Encode path/query components.
   Keep the client and collector ordinary functions in one module until another caller needs a split.
3. Use the existing `PVE_HOST`, `PVE_TOKEN`, `PVE_CACERT` credential contract with a narrow
   non-executing assignment parser for the existing env-file format. Default source is
   `/opt/skynet-ops/secrets/proxmox-core.env`; permit an explicit `--credentials-file` for
   synthetic test files. Do not source/eval shell, invoke sudo, accept arbitrary shell expressions,
   print token values, dump response bodies in diagnostics, or disable TLS. Missing/unreadable
   credentials or CA fail nonzero with a redacted reason. No production secrets are read in P3a.
4. Preserve `node`, `collected`, `nodes`, `resources`, `pools`, `backup_jobs`,
   `backup_last` and their consumer-required field types. Validate the API envelope and entries,
   not just JSON syntax. Missing/null required data and empty nodes/resources cannot satisfy a
   successful core snapshot. Empty pool/job lists can be legitimate observations; never turn a
   failed read into an empty list. Preserve stable pool member identities and nullable backup fields.
   In this slice, any required endpoint failure prevents publication of a new snapshot.
5. Assemble and validate before writing a temporary sibling and atomically replacing the requested
   output. On timeout, malformed data, absent evidence or local write failure, preserve the prior file
   byte-for-byte and its collection time; remove temporary residue. Report that the requested refresh
   failed and any retained snapshot is previous evidence. P3b must address consumers that ignore
   freshness before routing the live default path here.
6. Human output gives target, outcome, destination and concise node/guest/pool counts on success;
   JSON is one stdout object with `outcome`, `target`, `output`, and success timestamp/counts
   or a redacted failure reason. Success exits 0, usage errors 2, unavailable remote/config evidence
   3, malformed data/local publication failure 1. Human and JSON must agree; no generic outcome
   class hierarchy, retries, locks, status database, or extra metadata files.
7. Extend Nix source filtering to precisely include the new module/tests/synthetic fixtures; carry
   all behavioral tests through source and packaged checks. Extend lint/hook/CI selection to the
   new Python tests. Document the implemented command, explicit output, and failure semantics;
   do not claim the nightly or installed host now uses Python.

**Optional scoped Luna assignment:** after Astra fixes interfaces, Luna High may own only
`tests/test_proxmox.py` and `tests/fixtures/proxmox/**`: exercise real parsing/collection/publication
through fake HTTP boundaries and temporary files. Test success, timeout, TLS refusal, HTTP failure,
malformed envelopes/entries, missing credentials, empty required data, and publication failure.
No production access, secrets, module/Nix edits, helper spawning, commits or pushes.
Astra owns CLI/client/integration, inspects fixtures, and reruns all checks.

**Checks and expected results:**

- `nix develop --no-write-lock-file -c pytest -q` → doctor regressions and collector tests pass.
  Tests drive the actual CLI entry function/default collector path, replacing only the external
  transport boundary; no fixture-only CLI mode or mocked collector. Include an outside-checkout
  packaged invocation with missing synthetic credentials → redacted JSON/nonzero/no output file.
- Prove endpoint failure after earlier successful reads leaves a pre-existing output unchanged;
  prove an output-replacement failure also preserves it. Assert no success timestamp on failed
  refresh, no token in either output stream, and no redirect/TLS-verification downgrade.
- `nix develop --no-write-lock-file -c ruff check src tests/test_*.py` and
  `nix develop --no-write-lock-file -c mypy src/skynet` → clean.
- `nix build --no-write-lock-file --no-link .#checks.x86_64-linux.skynet` and
  `nix flake check --no-write-lock-file --no-build` → package and existing output checks pass.
  `.githooks/pre-commit` with Python changes staged and `git diff --cached --check` → pass.
- Compare a successful synthetic snapshot with the existing consumers' projections and document
  preserved fields; inspect the diff to confirm no default caller, live inventory or host changed.

**Boundaries and exclusions:** T1 construction only in an isolated checkout, with synthetic
credentials/responses and temporary outputs. No lab API calls, credential inspection, activation,
profile installation, service/timer change, root grant, or production data writes. Existing shell
callers remain the sole live path during this isolated construction slice; no compatibility shim
or second production engine is introduced. No shell collector deletion until P3b/P4 account for
core/network callers. Source rollback is git revert; build/test artifacts are disposable.
The map's live/recovery blockers must be resolved before any later live transition.

**Exit criteria:** (1) packaged core CLI and readable/JSON collection summaries implement the stated
contract; (2) validation, timeouts, TLS/redaction and atomic failure behavior pass independent tests;
(3) snapshot field compatibility and Nix/CI/hook coverage are demonstrated; (4) no live caller,
credential, authority or operational data changed. Missing live evidence is explicitly outside this
slice, not proof of P3/G2 completion. Record P3a complete and continue P3 by detailing P3b's
integration/freshness packet, retaining its live/recovery boundaries. Do not increment accepted
numbered progress. Request fresh Astra Medium merged-result review only after all P3 slices finish.

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
intended services/backups are restored; a cold operator can diagnose and recover from git + survival kit.
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
