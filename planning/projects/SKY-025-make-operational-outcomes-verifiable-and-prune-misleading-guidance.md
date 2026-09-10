---
id: SKY-025
title: Rebuild the Skynet engine in Python
status: in-progress
horizon: long
created: 2026-09-06
updated: 2026-09-09
phases: 24
current_phase: 6
tier_touched: [T1, T2, T2+, T3]
related:
  - docs/system-design.md
  - AGENTS.md
  - docs/conventions/construction.md
  - planning/README.md
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

## 3. Main model recommendations

Construction — Light/Medium/Heavy routes, worker roles, task capsules, ownership, batching,
verification, and repair — follows [`../../docs/conventions/construction.md`](../../docs/conventions/construction.md).
This directive adds only per-phase **Main model recommendations**, not a second orchestration system.

**Main model:** use the model/effort in the phase table as a starting recommendation for the Main
session; **merged-result review and next-phase planning** run in a fresh session with the
operator-selected model and effort. These are workload-based starting recommendations, not benchmark
equivalences. A phase review may change the next recommendation from observed results; record the
reason in that phase's packet.

Terra High is the default Main. Sol Low handles the defined rendering/documentation passes. Astra
Medium owns foundational design and consequential recovery/policy work. If a Terra/Sol phase exposes
unresolved architecture, privilege, or recovery decisions, hand that decision to Astra Medium rather
than spending repeated worker retries guessing. No automatic model router. Verify actual identifiers
in the installed harness; never silently substitute — if unavailable, mark routing blocked and ask
Ali to select an available identifier or update the harness.

Workers gain no production authority, never touch secrets or production, and never commit/push/merge;
keep non-overlapping ownership and human merge. Main owns decomposition, integration decisions, and
PRs; in Heavy, independent verification is the Tester's, not Main's. Load this directive, the current
phase, and relevant files only — no full-repo dumps or transcript handoffs.

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
Main details remaining slices within that phase's scope; no intermediate reviewer
releases them. Existing human merge and live/grant boundaries still apply. The table is a route map,
not permission to execute unspecified work. Section 5 holds the sole current executable packet.

For every phase: implement → relevant checks → PR → Ali merges → review the actual merged result.
A fresh reviewer, using the selected model and effort, reports **accept**, **fix**, or **blocked**
and never modifies the implementation. A fixable defect returns one paste-ready fix prompt to the
original implementation session, which lands a bounded fix PR; a fresh reviewer then reviews the
complete phase again, repeating until accept. Only after acceptance
flesh out the next phase with exact files, interfaces, worker
capsules, commands/checks, grants if any, and exit criteria. Do not roll into dependent implementation
just because a worker or CI says done. Ali can use the reusable review prompt in §8 in a fresh session.
Architecture checkpoints **G1–G6** additionally reconsider the remaining roadmap and prune unnecessary work.

| Phase | Recommended Main | Bounded outcome / main surface | Depends on; exit evidence |
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

## 5. Phase 7a — Omada read collection (~1–2h)

**Release gate:** execute after Ali merges the P6 combined review/repair ACCEPT PR recorded
in §9. Its verified repairs and phase acceptance take effect at that merge; no separate P6
repair review is required. **Lead:** Terra High (`gpt-5.6-terra`, high), retaining the phase-table
recommendation. The launcher dry-run resolves that exact model/effort.

**Goal:** replace the existing Omada shell collector with validated Python observations and
receipt-bound freshness. Split P7 into **P7a Omada**, **P7b certs/routes**, and **P7c recon**:
three independent parser/transport boundaries do not fit one implementation packet. Only P7a
is detailed here; Main details each remaining same-phase slice after the preceding
merge. One independent review covers all P7 slices before P8.

**Exact surfaces:** new `src/skynet/omada.py`, `src/skynet/{cli,collection}.py`,
`tests/test_{omada,cli,collection}.py`, synthetic `tests/fixtures/omada/`,
`scripts/collect-network-gear.sh`, `nix/packages/skynet.nix`, `flake.nix`,
`.githooks/pre-commit`, `.github/workflows/checks.yml`. Inspect `scripts/build-db.sh`,
`scripts/render-docs.sh`, `bin/ops`, `scripts/{collect-all,nightly}.sh`; change consumers
only where preserving their output contract requires it. Update `nix/README.md`,
`docs/design/observability.md`, `runbooks/nightly.md`, this directive/map and raw journal;
regenerate roadmap/digest/context through their tools. Shared transport extraction needs an
actual second caller; do not add a generic client/session framework.

**Interfaces and decisions:**

1. Add `skynet collect omada --output <file> [--credentials-file <file>] [--json]`.
   Preserve `inventory/network-gear.json`: collected time, controller host/version/omadacId,
   site id/name objects, and entity-keyed device observations. Preserve device identity/name,
   type/model/MAC/IP, site, firmware/upgrade status, connected/status, uptime/clients, PoE and
   switch-port fields consumed by the SQLite cache and renderer. Keep the existing entity slug
   grammar, including straight/curly apostrophe handling; reject ambiguous duplicate identities.
2. Parse literal `OMADA_HOST/PORT/SNI/USER/PASS/CACERT` assignments from the configured default
   `/opt/skynet-ops/secrets/omada.env`, without eval/sudo. Preserve quoted password characters
   as data; never include passwords, session cookies, CSRF tokens or external error messages
   in reports. Retain verified pinned-CA HTTPS, hostname/SNI handling and bounded timeouts.
   Do not use production credentials during construction.
3. Permit only the existing info GET, login POST, and authenticated sites/devices/switch-port
   GETs. Login is session establishment for the Viewer account, not permission for controller
   mutation. Keep session cookies in memory and validate controller identity, HTTP/API outcomes,
   pagination and every required list. Missing/null/error/truncated responses fail; explicit
   valid empty lists are observations. A missing switch-port read cannot silently become
   `ports:null` success; null ports for non-switch devices remain valid. Preserve previous bytes
   until every required read and validation completes, then replace atomically.
4. Run Omada once under the shared collection receipt/lock, with an unavailable marker before
   reads and success bound to snapshot hash/time. Remove only network-gear from `REMAINING`.
   Add its marker to default status/query/entity/render and nightly freshness requirements.
   Controller host provenance must work with `collect-status` (preserve nested controller data;
   add top-level host if needed). Failed reads permit later scoped readers, refuse overall
   freshness and retain previous data. Cover initial/final marker failure and recovery.
5. Retain `collect-network-gear.sh` as a forwarding shim for demonstrated callers; preserve
   `OMADA_SECRET_FILE` forwarding. P22 owns removal. Extend source/installed Nix checks and
   hook triggers to the module, fixtures and shim. Isolate all API/login/subprocess boundaries
   in tests, including subprocess-launched default collection; installed tests must import
   the package, not the source checkout.

**Optional worker assignments:** an Investigator (read-only) maps Omada device/port fields to
`build-db.sh`/`render-docs.sh`; a Default Executor owns only `tests/test_omada.py` and synthetic
fixtures after Main settles the response contract, on non-overlapping ownership. No production,
credentials, commits or pushes delegated; workers never spawn workers. Main owns implementation/integration.

**Checks and exit criteria:**

- `nix develop --no-write-lock-file -c pytest -q`: real CLI plus fake transport covers Viewer
  endpoint allowlist, cookie/CSRF lifecycle, TLS refusal, redacted failures, site pagination,
  complete switch-port collection, valid empty/non-switch shapes, malformed/null/error and
  partial-site failure, retained bytes, consumer contract, default freshness refusal/recovery.
  All previously accepted DNS/OPNsense/PBS/Docker/Proxmox and process-cleanup regressions pass.
- `nix develop --no-write-lock-file -c ruff check src tests/test_*.py` and
  `nix develop --no-write-lock-file -c mypy src/skynet`: clean.
- `nix build --no-write-lock-file --no-link .#checks.x86_64-linux.skynet` and
  `nix flake check --no-write-lock-file --no-build`: source/installed checks and evaluation pass.
- Offline doctor succeeds; disposable missing-evidence status exits 3; full staged hook and
  `git diff --cached --check` pass. The five paused documentation suites remain manual/unrun,
  with maintained replacements restored by P24.

**Live/grant boundaries and exclusions:** isolated construction, synthetic credentials and
disposable outputs. No Omada live login/read, device adoption/reboot/configuration, controller
write, root/grant, credential/pin change, activation or timer/service change is released here.
The operator-authorized P6 DNS/OPNsense/mirror tests do not authorize P7 endpoints. No cert,
route or recon implementation in P7a; no entity engine rewrite, new Omada capability or remote
Python installation. Workstation/state/payload recovery prerequisites remain. Rollback is
git revert; no production installation occurs in this packet.

**Close-out:** mark P7a slice-complete / P7 in progress, keeping accepted progress 6/24. After
human merge, detail P7b for certificate probes and authored Caddy route parsing with explicit
vantage/source provenance; then P7c for bounded local/unprivileged-SSH recon. No independent
slice acceptance or P8 release until all numbered-P7 work is merged and reviewed together.

## 5b. Phase 7b — certificate and authored-route observations (~1–2h)

**Release gate:** P7a is merged as [#235](https://github.com/aliammar03/skynet/pull/235) at
`b173e74142f6e57635a6b4f2a2e64b48800f2974`. **Lead:** Terra High (`gpt-5.6-terra`, high).

**Goal and surfaces:** replace `scripts/collect-certs.sh` and `scripts/collect-routes.sh` with
`src/skynet/{certs,routes}.py`, their `skynet collect certs|routes` CLI commands, synthetic tests
and fixtures, forwarding shims, receipt-bound default collection/status integration, Nix source
inputs and hook triggers. Update only consumers/doctrine needed to describe the implemented source
and vantage; retain `scripts/entity.sh` as P8's existing entity-derivation caller.

**Contracts:** certificates are unauthenticated TLS observations from the ops-VLAN vantage. Probe
the existing declared endpoint list with an explicitly unverified handshake solely to read the
leaf; do not call that trust. Record every unreachable endpoint as `reachable:false`, retain the
existing issuer/subject/SAN/not-after/days-left schema for a valid leaf, and fail atomically for a
malformed leaf or local publication failure. Routes are a static parse of the committed
`compose/caddy-apps/Caddyfile`: record that source/provenance, the apps front door, backend and
auth chain; use the existing entity script only to map collected guest IPs. Missing/invalid source
or entity derivation fails, no live reachability is implied, and neither collector reads secrets.
Both default observations receive initial/final receipt markers and status freshness; failure
retains bytes, refuses freshness and permits later readers. Preserve old shell entry points as
forwarders; P22 owns removal.

**Checks:** fake TLS/subprocess boundaries cover endpoint/vantage/source provenance, malformed and
unreachable cases, atomic retention, Caddy block/auth/backend parsing, source/installed CLI,
marker failure/recovery and consumer fields. Run the P7a check set (pytest, Ruff, mypy, package,
flake, doctor, disposable status, staged hook and diff check). The five paused documentation suites
remain manual. Ali additionally authorized a T1 live pass only from this isolated checkout: Omada
Viewer read, declared certificate probes, static route parse, and any P7c recon only after that
slice is independently released. No inventory rewrite, root/grant, credential/pin change,
activation, service/timer change, entity rewrite or recon implementation is authorized here.
Rollback is `git revert`.

**Optional worker:** a Default Executor may own only certificate/route tests and fixtures;
it must not access endpoints, credentials or production. Main owns integration and validation.
**Close-out:** P7b slice-complete / P7 in progress, accepted progress still 6/24; after human
merge detail P7c only.

## 5c. Phase 7c — bounded local and unprivileged-SSH reconnaissance (~1–2h)

**Release gate:** P7b is merged as [#236](https://github.com/aliammar03/skynet/pull/236) at
`e45b8132f3fe1e9637a2a8846de1258cb234dac8`. **Lead:** Terra High (`gpt-5.6-terra`, high).

**Goal and surfaces:** replace `scripts/recon.sh` with `src/skynet/recon.py`, `skynet recon
[target] [--json]`, a forwarding shim, synthetic tests/fixtures and Nix/hook inputs. Update only
the recon runbook and P7 evidence. The result is one bounded T1 snapshot, not a health assertion,
daemon, scheduler, entity rewrite, or remote command framework.

**Contracts:** local uses a fixed probe through `bash -s`. A remote target is a bare hostname or IP
only and is always invoked as `svc-ops@<target>` with an argument-array SSH command, BatchMode and
a bounded connect timeout; explicit users/options, root and grant use are rejected. The fixed probe
contains read-only host, pressure, disk/inode, failed-unit, socket, unprivileged Docker, journal,
configuration and package observations. Each probe is bounded; partial sections are preserved.
It returns either a structured JSON snapshot or Markdown from the same marker stream. Transport,
timeout, malformed/empty marker stream and rejected target are unavailable (exit 3), never a
successful snapshot. No credentials, inventory output, remote write, service/timer change or root
action exists in this packet.

**Checks:** fake subprocess tests cover local and remote argument construction, forced `svc-ops`,
target rejection, timeout/unavailable, malformed markers, partial sections, JSON/Markdown and shim
forwarding; run pytest, Ruff, mypy, package, flake, doctor, staged hook and diff check. The five
paused documentation suites remain manual. Ali's earlier phase-wide live authorization permits one
local and one `docker-dmz` unprivileged read from this isolated checkout; neither result updates
production inventory. Rollback is `git revert`.

**Optional worker:** a Default Executor owns only recon tests/fixtures; no endpoint, SSH,
credential or production access. **Close-out:** P7c slice-complete / P7 review pending, accepted
progress still 6/24. After all P7 PRs are merged, start a fresh review task: `Read
planning/prompts/review.md and review SKY-025 implementation PR <P7c URL>, plus #235 and #236.`


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
file (`current_phase` = accepted phases, date/status), map and roadmap; journal raw evidence. The
directive is the sole progress record—no extra tracker or repeated copy of the plan.
Implementation-complete/review-pending is not accepted/done.

## 8. Execute / review / continue prompts

Use the [phase handoff workflow](../prompts/README.md): two reusable prompts with standard GitHub
PR bodies. Select the execution model from the current packet; use a fresh task with the selected model for
merged-result review. An ACCEPT review/planning PR must be human-merged before its next packet runs;
a FIX verdict returns a paste-ready fix prompt to the original implementation session, which lands a
bounded fix PR reviewed afresh.

**Start or continue in the packet's execution model:**
```text
Read planning/prompts/execute.md and execute the next authorized SKY-025 packet.
```

**After Ali merges implementation, in a fresh review task with the selected model:**
```text
Read planning/prompts/review.md and review SKY-025 implementation PR <URL>.
```

## 9. Status

- 2026-09-10 — **P7 corrective packet implementation complete / review pending.** From merged
  remote-main `ded7289ca3938c3adeeaf21d3dad3bb90dcd5a80`, the bounded route/recon review fixes make
  a missing or unreadable authored Caddyfile unavailable and retain prior route evidence, reject
  malformed or unclosed vhost blocks rather than publishing a partial/empty observation, and add
  `target: recon` plus `outcome: success` to successful recon JSON snapshots. Regression tests use
  a genuinely absent source path and a truncated block. Full pytest (258), Ruff, mypy, Nix package
  and flake checks pass; no live collector, inventory rewrite, credential/pin, root/grant,
  service/timer, activation or remote write occurred. The five paused documentation suites remain
  manual. **P7 remains review pending and accepted progress remains 6/24.** After this fix is
  human-merged, a fresh reviewer must review #235, #236, #237 and this fix together before P8.

- 2026-09-09 — **P7c slice complete — bounded Python reconnaissance.** From remote-main base
  `e45b8132f3fe1e9637a2a8846de1258cb234dac8`, `skynet recon [target] [--json]` replaces the shell
  implementation with a fixed read-only marker probe. Local is explicit; remote targets are bare
  hostname/IP inputs forced to `svc-ops@<target>` through argument-array SSH with BatchMode and a
  connect timeout. Invalid target, transport/timeout, malformed or truncated marker streams return
  unavailable; command-level partial output remains visible inside complete snapshots. Synthetic
  source/installed checks pass (249 tests, Ruff, mypy and package checks). The authorized isolated
  T1 pass succeeded locally and at `docker-dmz`, each with all nine snapshot sections. No inventory,
  credential, grant/root, remote write, timer/service or activation state changed. **All P7 slices
  are now implementation-complete; P7 is review pending and accepted progress remains 6/24.** After
  this PR is human-merged, a fresh reviewer must review #235, #236 and this PR together before P8.

- 2026-09-09 — **P7b slice complete — certificate and static-route observations.** From
  remote-main base `b173e74142f6e57635a6b4f2a2e64b48800f2974`, `skynet collect certs` observes the
  fixed seven-endpoint TLS allowlist from the explicit ops-VLAN vantage using an unauthenticated
  leaf handshake, preserving the existing certificate schema and recording unreachable endpoints.
  `skynet collect routes` statically parses the committed apps Caddyfile and maps backends through
  compose addresses plus the existing entity script. Both collectors publish atomically, use
  receipt-bound default markers and freshness status, and retain their shell callers only as
  forwarders. Synthetic source and installed checks pass (239 tests, Ruff, mypy, package and flake
  checks). Ali-authorized isolated T1 reads succeeded: Omada 1 site/3 devices, certificates 7/7
  reachable, static routes 9. No production inventory, credentials, pins, timer/service, host,
  grant or root state changed. **P7 remains in progress and accepted progress remains 6/24**:
  P7c recon is released only after this PR is human-merged, then a fresh reviewer covers all P7.

- 2026-09-09 — **P7a slice complete — Omada Python collection.** From remote-main base
  `23223d035a4e5cd8a4138ca28eb6368413f082a9`, P7a adds the validated Viewer-only
  `skynet collect omada` command, preserves the existing network-gear consumer schema, and
  adds top-level controller-host provenance for default status. The default collection runs it
  once under the shared receipt, writes `collection-network-gear.json` before/after the read, and
  rejects stale, failed or mismatched Omada evidence in `collect-status`; the legacy shell script
  is a forwarding shim retaining `OMADA_SECRET_FILE`. Synthetic endpoint/session/TLS/redaction,
  malformed/partial/empty/duplicate/retained-bytes and receipt-marker recovery cases are covered.
  Source and installed checks passed (229 tests each), with Ruff, mypy, Nix package checks and
  flake evaluation clean. No production Omada login/read, inventory rewrite, timer/service or
  credential/pin change, activation, root grant or recovery test occurred. **P7 remains in
  progress and accepted progress remains 6/24**; after this PR is human-merged, detail P7b
  (certificate probes and static Caddy routes), then P7c recon, before one P7 review.

- 2026-09-09 — **P6c corrective slice — offline firewall inventory path removed.** Authorized by
  GitHub issue #230 as a bounded cleanup after the P6 ACCEPT (#229), from base
  `4bc4715ded192dcade30174ed6a857b74acf54b5`. P6b-ii's offline `config.xml` inventory parser was a
  second producer for the firewall-inventory shape and a source of ambiguity about live-vs-stale
  provenance; P6c retires it. Deleted `src/skynet/firewall.py`, `scripts/collect-firewall.sh`, the
  `skynet collect firewall` CLI wiring, `tests/test_firewall.py`, `tests/fixtures/firewall/`, and the
  parser-only Nix source-filter / installed-check / pre-commit-hook references. The one
  `test_collection.py` case that used the parser to write stale bytes now does a direct out-of-band
  overwrite of `firewall.json`, keeping its receipt-hash-mismatch freshness coverage. Docs/design/ADR
  references presenting offline `config.xml` parsing as an inventory source (nix/README, observability,
  ADR 0006 consequence, SKY-020) were updated. **Disposition:** the live OPNsense API
  (`src/skynet/opnsense.py`) is now the sole firewall inventory producer; freshness/receipt semantics
  unchanged; the `config.xml` git backup is retained only as DR material (restored as configuration,
  never parsed into inventory). No replacement offline collector added; live OPNsense API behavior and
  firewall write policy unchanged; P17 recovery not redesigned. Accepted progress remains **6/24** —
  P6c is a corrective slice, not a new numbered phase, and needs no P6 acceptance reopening beyond
  verifying it does not regress the live collector. See the P6c disposition in
  [the map](../sky-025-map.md).

- 2026-09-09 — **P6 ACCEPT with reviewer repairs**, effective when Ali merges this combined
  review PR. Reviewed [#226](https://github.com/aliammar03/skynet/pull/226)
  (`b7e6f6e8e1dd69f8bbe0f54d91738f9bced4a1b8`),
  [#227](https://github.com/aliammar03/skynet/pull/227)
  (`ea50741c8a25cac9b72a460c3ef08395403dea41`), and
  [#228](https://github.com/aliammar03/skynet/pull/228)
  (`9858daf0b4405b14aa93f45f50d71349ea29b1b6`), all verified merged through GitHub.
  Packet baseline `db09021802f590d79f2ab9f7c2c56064f29c0a4a`; reviewed main
  `9858daf0b4405b14aa93f45f50d71349ea29b1b6`; only those three commits intervene.
  Reviewer: GPT-6 session, exact variant/effort unavailable; two Luna Medium scouts and two
  Luna High builders handled bounded inspection/repairs. The reviewer inspected all changes
  and retained live checks and acceptance.

  | P6 exit | Verdict and independent evidence |
  |---|---|
  | Scoped reads, TLS, no write creep | ACCEPT — actual packaged DNS and OPNsense collectors succeeded over verified TLS using unchanged credentials; endpoint/method and TLS-refusal tests pass. No configuration, credential, service or root writes. |
  | Response validation and preserved consumers | ACCEPT after repairs — root DNS requests use `.` while inventory keeps its identity; A/AAAA/CNAME fields validated. OPNsense accepts unused `OPN_USER`, derives certificate SNI first, rejects missing/malformed containers and incomplete search/rule sets, and preserves optional interface fields. |
  | Failure, paired freshness and recovery | ACCEPT — initial/final DNS and both OPNsense marker failures refuse prior success and recover; partial pair publication returns failure; offline mirror replacement invalidates an existing live receipt. ICMP execution errors remain unavailable, not no-reply. |
  | Offline parser and provenance | ACCEPT — synthetic malformed XML, legacy paths, redaction and byte-retention tests pass; local mirror parse returned 41 aliases/29 rules/5 reservations without pulling or establishing live freshness. Source path is retained; mirror revision/hash is not recorded. |
  | Source/installed checks and callers | ACCEPT — 225 pytest tests passed; Ruff and mypy clean; Nix source/installed package check and flake evaluation passed; offline doctor succeeds and disposable missing-evidence status exits 3. Full staged hook and diff checks are recorded in the review journal/PR. |

  Packaged live results at 15:45 UTC: DNS 4 zones/13,355 records; OPNsense 40 aliases,
  28 rules, 41 ARP entries, 17 interfaces. Outputs stayed in `/tmp/skynet-p6-live.0M8zWC`;
  existing main inventory edits were preserved. No end-to-end production nightly, activation,
  write or recovery drill was attempted. The five paused documentation suites remain unrun.
  Repairs are included in this review branch; their commit identity is recorded in the PR.
  [Raw evidence](../../journal/2026/2026-09-09-session-sky-025-p6-combined-review-and-live-reads.md).
  Accepted progress becomes **6/24** at human merge. §5 releases only **P7a Omada, Terra High**;
  P7b certs/routes and P7c recon are same-phase continuations. No G checkpoint is due and no
  phase order changed. After merge: `Read planning/prompts/execute.md and execute SKY-025 P7a.`

- 2026-09-09 — **P6b-i slice complete / P6 in progress.** From origin/main base
  `b7e6f6e8e1dd69f8bbe0f54d91738f9bced4a1b8` (includes P6a #226), P6b-i adds the live OPNsense
  collector `src/skynet/opnsense.py`, replacing `collect-opnsense.sh`. P6 was split further:
  P6b-i is the **live** collector (this PR); **P6b-ii is the offline config.xml mirror parser**
  (`collect-firewall.sh` → `src/skynet/firewall.py`), matching the two shell scripts. One
  `skynet collect opnsense --firewall-output <f> --state-output <f>` run produces both paired
  snapshots: the user-view `inventory/firewall/firewall.json` (aliases with built-ins dropped and
  type/content resolved, rules intersecting `filter/get` UUIDs+sequence with `searchRule` fields,
  `dnsmasq` reservations) and live `inventory/opnsense.json` (firmware, ARP, interfaces, declared-
  host presence with explicit ARP/ICMP vantage). TLS reuses the PBS SNI-pinned transport
  (cert-derived SNI, pinned-cert CA trust); Basic auth key/secret stay in the header with fixed
  redacted diagnostics. Only the enumerated GETs and read-only search POSTs are called; a search
  page whose reported `total` exceeds its rows fails as incomplete. Both snapshots are fully
  validated before either is written, so a read/validation failure leaves both files untouched;
  `collect all` drops opnsense from the shell `REMAINING`, publishes both under one receipt with
  two markers (`collection-firewall.json`, `collection-opnsense.json`), and default status/query/
  entity/render + nightly require both. `collect-opnsense.sh` → forwarding shim (P22 owns removal);
  `collect-firewall.sh` is unchanged, owned by P6b-ii. New source/tests/fixtures joined the Nix
  source filter, installed check and staged-hook glob. Checks: `pytest -q tests` 186 passed,
  Ruff/mypy clean, `nix build .#checks…skynet` and `nix flake check --no-build` pass, offline
  doctor success, disposable missing-evidence status exits 3 (now requiring both OPNsense markers).
  Construction used synthetic credentials/transports and disposable outputs only; no live
  OPNsense read, config write, credential change, root, grant or production write occurred. Source
  rollback is `git revert`; live endpoint parity, the ops→NET_SKYNET ICMP-vantage rule, and
  workstation/state/payload recovery remain unverified. Accepted progress remains **5/24**. After
  human merge, detail only P6b-ii; obtain one fresh review of the complete numbered P6 (P6a +
  P6b-i + P6b-ii) before P7.
  [Raw evidence](../../journal/2026/2026-09-09-session-sky-025-p6b-opnsense-live-python-collection.md).

- 2026-09-09 — **P6b-ii slice complete / P6 in progress (P6 now fully sliced).** From origin/main
  base `b7e6f6e8e1dd69f8bbe0f54d91738f9bced4a1b8` (P6a; P6b-i #227 not yet merged), P6b-ii adds the
  offline OPNsense mirror parser `src/skynet/firewall.py`, replacing `collect-firewall.sh`. It parses
  the git-mirrored `config.xml` into the firewall.json aliases/rules/reservations shape for DR
  rebuild: no network or git operation (the operator refreshes the mirror first — no implicit pull),
  every sensitive-looking child tag dropped whether or not populated, and **no receipt-bound marker
  and no `host` field**, so an offline parse can never satisfy the default freshness contract
  (`collect-status` still reports it unavailable). A missing mirror is unavailable (3); malformed XML
  or an unexpected root fails (1); both retain prior bytes. CLI `skynet collect firewall
  --output <f> [--config <path>] [--json]`; `collect-firewall.sh` → forwarding shim; it is NOT wired
  into `collect all`. New source/tests/fixtures joined the Nix source filter, installed check and
  staged-hook glob. Checks: `pytest -q tests` 173 passed (this branch lacks P6b-i's opnsense tests),
  Ruff/mypy clean, `nix build .#checks…skynet` and `nix flake check --no-build` pass, offline doctor
  success, a real offline parse of the fixture returns counts {2,1,1} with no `host`.
  **Base/merge note:** the repo squash-merges, so P6b-ii is based on main (not the P6b-i branch) to
  avoid stranding; #228 shares three files with #227 (`cli.py`, the Nix source filter, the
  pre-commit glob) and needs a trivial additive rebase onto main after #227 merges. Merge order:
  P6b-i (#227) then P6b-ii (#228). Construction used a synthetic config.xml and disposable outputs
  only; no live/mirror read, git operation, or production write occurred. Source rollback is
  `git revert`. Accepted progress remains **5/24**. After all three P6 slices merge (P6a #226,
  P6b-i #227, P6b-ii #228), obtain one fresh review of the complete numbered P6 before P7.
  [Raw evidence](../../journal/2026/2026-09-09-session-sky-025-p6b-ii-opnsense-offline-mirror-parser.md).

- 2026-09-09 — **P6a slice complete / P6 in progress.** From isolated remote-main base
  `db09021802f590d79f2ab9f7c2c56064f29c0a4a` (#225), P6a replaces the Technitium shell collector
  with `skynet collect dns --output <file> [--credentials-file <file>] [--json]` in
  `src/skynet/dns.py`. Literal `TECH_HOST/TECH_TOKEN/TECH_CACERT` parsing (no eval/sudo/live read),
  CA-file hostname-verified HTTPS on port 53443, a bounded timeout, and a token carried only in the
  request query with fixed redacted diagnostics. Only `zones/list` and `zones/records/get` are
  allowed; a non-`ok` API status, null/missing zone or record list, duplicate zone identity,
  malformed required record field, timeout or trust failure is unavailable/failed and retains prior
  bytes, while a validated empty record list is a real observation. The snapshot preserves
  collection time, host, every zone object, and per-zone `{zone, records}` with record
  `name/type/rData` (all types) for SQLite and the service renderer. `collect all` drops DNS from
  the shell `REMAINING`, runs it once under the shared receipt, publishes a receipt/hash/time
  `collection-dns.json` marker, and default status/query/entity/render plus the nightly cutoff now
  require it; DNS failure permits later scoped readers but refuses default freshness. The shell
  entry is a forwarding shim (P22 owns removal). New source/tests/fixtures are added to the Nix
  source filter, installed check, and staged hook glob. Checks: `pytest -q tests` 166 passed,
  Ruff/mypy clean, `nix build .#checks…skynet` and `nix flake check --no-build` pass, offline
  doctor success, disposable missing-evidence status exits 3, full staged hook exits 0. Construction
  used synthetic credentials/transports and disposable outputs only; no live DNS/OPNsense read,
  credential/pin change, zone modification, timer/service, root, grant or production write occurred.
  Source rollback is `git revert`; endpoint parity and workstation/state/payload recovery remain
  unverified. The committed snapshot's root `""` Secondary zone returns null records, which the
  stricter contract would fail — an unverified live boundary noted for P6b/live transition, not
  resolved here. Accepted progress remains **5/24**. After human merge, detail only P6b (OPNsense
  live/offline reads); request one fresh review of the complete P6 after both slices merge.
  [Raw evidence](../../journal/2026/2026-09-09-session-sky-025-p6a-dns-python-collection.md).

- 2026-09-09 — **P5 ACCEPT with reviewer repairs, effective at this PR's human merge.**
  Reviewed [#223](https://github.com/aliammar03/skynet/pull/223), merge
  `c0e0f53007dee3d49779c4f7fca065fbac13dbd2`, and
  [#224](https://github.com/aliammar03/skynet/pull/224), merge/main reviewed
  `e09a8fc220d610cf6c5d60ac5471cdf0d67bcbe3`, against packet baseline
  `faf961ab3accb9466385da32efa9bb6185c77f3b`. No intervening main changes.
  Ali authorized reviewer repairs, live PBS/Docker reads and Luna workers, then requested
  model-agnostic review. The invoking review used Astra Medium; that is evidence, not a
  requirement. The combined PR contains inspected reviewer repairs and their regressions.

  | Full P5 exit | Verdict / evidence including repairs |
  |---|---|
  | Complete PBS observations and retained bytes | ACCEPT — numeric usage validation; explicit root namespace collected once; malformed/null/timeout retention tests; live 1 datastore, 152 snapshots, 18 groups. |
  | Backup verification signals | ACCEPT — failed, absent and unknown latest states cannot render green; real renderer tests cover warning and successful latest-group counts. Live latest states: 6 ok, 12 absent. |
  | CA/pin/SNI compatibility and refusal | ACCEPT — real synthetic CA and fingerprint handshakes/GETs, pin/name/CA refusal and SAN/CN fallback; configured live TLS succeeds. |
  | Docker field validation and bounded processes | ACCEPT — strict required fields with nullable optional Platform preserved; timeout, early-parent-exit and SIGINT/SIGTERM tests reap descendants; cleanup failure quarantines default receipt and reports recovery-required. Live 18 containers/31 images. |
  | Default freshness and consumers | ACCEPT — duplicate Docker reader removed; exactly-once regression, read/marker failure refusal and recovery, shared receipt/hash/time validation and existing consumer/cleanup regressions pass. |
  | Test isolation, installed package and enforced checks | ACCEPT — spawned runners substitute Docker; installed-mode imports preserved; full pytest, Ruff, mypy, Nix source/installed package check, flake evaluation, doctor/unavailable status and staged hook pass. Five paused documentation suites remain unrun, with P24 restoration retained. |

  Initial counterexamples and test-isolation limitations remain in the
  [review journal](../../journal/2026/2026-09-09-session-sky-025-p5-combined-independent-review.md).
  [Repair and live-read evidence](../../journal/2026/2026-09-09-session-sky-025-p5-reviewer-repairs-and-live-reads.md)
  records subsequent authorization and validation. No production mutation, activation, grant,
  credential/pin change or payload/state operation occurred. Live observations do not establish
  restore readiness; workstation/state/payload recovery remains unverified.
  Accepted progress becomes **5/24** at human merge. Release only §5 P6a DNS with Terra High;
  P6b remains a same-phase execution continuation. No G checkpoint or roadmap reorder is due.
  Reviewer repairs that have passed full affected exits need no additional review session.

- 2026-09-09 — **P5b slice complete / P5 review pending.** From isolated remote-main base
  `c0e0f53007dee3d49779c4f7fca065fbac13dbd2`, P5b replaces Docker shell parsing with an explicit
  read-only Python CLI, validated container/image JSON lines, atomic retention and a receipt-bound
  Docker marker required by default consumers. The retained shell entry forwards to the package.
  Synthetic command/output tests cover a valid host, malformed output and retained bytes. No Docker
  context, production host, credential, service, timer, root, grant or write action occurred.
  P5 remains unaccepted at 4/24; after human merge, request one fresh Astra Medium review for both
  P5a PBS and P5b Docker PRs before P6.

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
