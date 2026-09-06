---
id: SKY-025
title: Make operational outcomes verifiable and prune misleading guidance
status: draft
horizon: short
created: 2026-09-06
updated: 2026-09-06
phases: 8
current_phase: 0
tier_touched: [T1, T2, T2+, T3]
related:
  - docs/system-design.md
  - docs/design/actuators.md
  - docs/design/disaster-recovery.md
  - docs/backup-strategy.md
  - docs/conventions/docs.md
  - scripts/deploy-gate.sh
  - scripts/tofu-apply.sh
  - scripts/backup-restic.sh
  - scripts/provision-restic.sh
  - runbooks/restore-service.md
  - runbooks/update-guests.md
  - planning/ideas/SKY-012-runbooks-as-executable-capabilities.md
  - "[[SKY-025-progress]]"
---

# SKY-025 · Make operational outcomes verifiable and prune misleading guidance

> Repair false-success and recovery gaps first; keep procedures compact, current, and backed by meaningful failure tests.

## 1. Review findings

**Baseline:** `main` at `749f08ae0b43b9b94651dfaf1e12bb94738725ba`, reviewed 2026-09-06.
Review covered the constitution/conventions, operational scripts, runbooks, CI tests, and relevant
Tofu/Nix declarations. This is source review plus local stub experiments, not a production health
attestation. All 19 existing `tests/*-test.sh` scripts returned 0; SQLite-dependent entity checks
were explicitly skipped because sqlite3 is unavailable. Nix/OpenTofu binaries are unavailable here,
so no flake/provider evaluation or live plan was performed. Existing green tests do not cover the
boundary failures reproduced below. No production commands, credentials, deployments, restores,
or merges were performed.

**Assessment:** the architecture makes sense: one constitution, declared infrastructure, scoped saved
plans, GitOps services, and human-merged authored changes. Runbooks are much easier to navigate.
The weak point is outcome verification: several scripts accept missing evidence or hide failure,
while some recovery procedures are too abbreviated or contradict their executors. More orchestration
or another documentation framework would not fix those defects.

### High priority — fix before trusting automated verdicts

| ID | Finding and evidence | Required correction |
|---|---|---|
| F1 | `scripts/deploy-gate.sh:48–56` accepts an empty container result as healthy. Because the probe is called in an `if`, its SSH failure is not stopped by `set -e`; an empty failed result also passes. **Reproduced:** Arcane stub reports running; SSH returns either empty success or exit 255; the real gate returns 0 and prints healthy in both cases. `tests/compose-rollback-test.sh` injects an entire probe, so it never exercises this defect. | Explicitly check transport/parse status, require the expected nonempty container set, validate every container, and bound individual probe calls. Test the real default probe with only external commands stubbed. |
| F2 | `scripts/gitops-deploy.sh` ignores redeploy failure (`|| true`), treats the status polling timeout as a report, and makes the health gate opt-in. `runbooks/deploy-service.md` invokes the ungated default and describes it as health-checking. The environment comes from the local checkout while Arcane independently pulls a branch, so source revisions can differ. `--no-deploy` still creates/enables an auto-sync or calls `/sync`. | Make normal deployment return success only for a verified revision and healthy expected service set. Propagate API/restart failures. Define and prove `--no-deploy` semantics, reconcile the exact approved source before environment materialization, and preserve prior environment on write failure. Keep supervised branch verification explicit. |
| F3 | `scripts/tofu-apply.sh:130–177` allows creates and updates together within one node scope. On apply failure it rolls back existing guests, then force-pushes the **whole** pre-apply state although created guests are expressly left for operator recovery. **Reproduced:** a core update+create fixture reaches `state push -force` after failed apply. This can erase state tracking for a successful/partial create. | Prefer refusing mixed create/update plans before any mutation. Never restore whole state unless every changed resource has a verified inverse. Preserve protected recovery evidence and lock/serial information; test actual state-push arguments, mixed actions, and failed recovery. |
| F4 | `scripts/provision-restic.sh:98` ends repository detection/initialization with `|| true`; its timer command can also hide enable failure behind later output. **Reproduced:** both `restic cat config` and `restic init` fail, but the exact initialization expression exits 0. `scripts/backup-restic.sh` silently skips missing selected paths; Docker list failure in process substitution and suppressed inspect failure can omit protected volumes while backing up appdata successfully. | Distinguish absent repository from unreadable/unauthenticated repository. Abort setup on initialization/timer failure. Fail an established backup when required paths or protected-volume discovery are unavailable; verify selection completeness before retention/prune. |

### Medium priority — make recovery and maintenance executable as written

| ID | Finding and evidence | Required correction |
|---|---|---|
| F5 | `runbooks/restore-service.md` restores directly onto `/` and checks out only `.env.sops`, then invokes a deploy script that pulls/syncs the current branch. It supplies no staging/clean-target procedure, ownership checks, or consistent configuration revision. `backup-restic.sh` takes hot filesystem copies of database volumes; there is no implemented dump/quiesce hook despite the runbook recommending one. | Define recovery by service, data snapshot, and complete compatible configuration revision. Restore into staging first; preserve the pre-restore target and verify ownership/application consistency. Specify a tested dump/quiesce strategy for protected databases. Coordinate paused sync, reviewed configuration changes, environment materialization, and resume. |
| F6 | `runbooks/update-guests.md` applies `apt full-upgrade` to every eligible guest although `hosts/` contains NixOS systems. It filters by pool exclusion rather than the full declared managed scope, and says continue after failure without distinguishing failed rollback. `runbooks/dr/DR-core-node.md` labels hypervisor/core recovery T2+ although node root and Unraid recovery are T3 in the constitution. Guest restore is reduced to 'with the PBS token ... restore', without the destination Proxmox/storage authority. | Select host OS and declared ownership first; give Debian and NixOS their correct reviewed update paths. Stop on failed rollback. Correct per-step recovery tiers, destination authority, and storage/network prerequisites; link shared policy. |
| F7 | `scripts/backup-pbs-gdrive.sh` runs `rclone sync` against a path without verifying the expected datastore/mount identity or coordinating backup/GC activity; its unit only orders after network readiness. An unexpectedly empty source directory can propagate deletion to the mirror. A size-only check against that same source does not prove a recoverable PBS archive. The docs acknowledge full core-loss recovery is unverified. | Verify source identity/readiness before sync, add a deletion guard, coordinate a stable source, and distinguish transfer completeness from restore integrity. Prove recovery into a separate target before strengthening any DR claim. Preserve existing backups throughout. |
| F8 | Several collectors (`collect-proxmox.sh`, `collect-dns.sh`, `collect-docker.sh`) return 0 when credentials/context are absent; `collect-all.sh` then prints OK and old inventory can remain. Proxmox's final JSON writes directly to the destination. | Use explicit success/skipped/unavailable/stale results, timestamps, and atomic validated replacement. A required failed collection must not appear fresh or healthy; optional unconfigured sources should be clearly skipped. Test consumer behavior as well as collector exits. |
| F9 | `scripts/update-clis.sh` globally installs npm CLIs and asks two LLMs for model IDs. `flake.nix` and `nix/home/aliammar.nix` declare the actual CLIs from Nix; `ops.env` is also Home Manager-owned. The weekly unit in `nix/modules/timers.nix` still runs this competing updater. | Remove the npm/self-query update path and its timer, or reduce it to a read-only version report with one declared owner. Update actual CLI packages through the pinned Nix workflow; do not treat generated model-name guesses as an authoritative registry or edit Home Manager output. |

### Pruning and maintenance debt

| ID | Evidence | Prune/improve |
|---|---|---|
| F10 | `scripts/backup-pbs-gdrive.sh:23–41` and `scripts/systemd/skynet-pbs-gdrive.service` retain the old six-hour timeout, chunk-shard/46% incident, and A6 story. `docs/conventions/docs.md` narrates the old token frontmatter gate; `collect-pbs.sh` and `collect-opnsense.sh` describe old implementations. These phrases evade the current temporal regex. | Delete those narratives from live files, keeping only present constraints and operational rationale. Keep history in journal/git. Add a few demonstrated regression cases and require semantic review; do not build an expanding ban-list of ordinary words. |
| F11 | Deploy standards are repeated in `runbooks/deploy-service.md`, compose conventions, and script headers. Rollback headers still suggest automatic mutation where the executor now only reports or prepares a PR. `planning/TEMPLATE.md` and `docs/conventions/metadata.md` disagree on status/horizon vocabulary; SKY-023 says phase 10/10 but remains in-progress with an unchecked phase and stale execute prompt. | Link standards once; describe actual executor behavior and supported flags. Reconcile metadata with the parser. Reconcile SKY-023 close-out against evidence before archiving; do not pretend incomplete live evidence exists. |

**Keep:** scoped apply/delete/excluded-guest guards, human merge ownership, useful diagnosis and DR
runbooks, current provider import exceptions, catalog/context renderers, and historical evidence.
Do not delete a script merely because a literal-reference search calls it an orphan; check timers,
remote installation, manual and recovery callers first. Do not reintroduce token-frontmatter stamping.

## 2. Decisions and ownership

- **CHOSEN:** targeted correctness fixes with failure tests at external boundaries. Reject a new
  general capability/orchestration framework: the existing Bash/runbook structure is sufficient.
- **CHOSEN:** reject mixed guest create/update plans first. Resource-specific recovery can follow
  only if a real workflow requires it and failure evidence supports it.
- **CHOSEN:** Nix owns installed agent CLIs; remove competing imperative maintenance.
- **CHOSEN:** this directive owns the concrete defects above. SKY-016 retains broader ingress
  verification/scaffolding; SKY-012 retains optional capability extraction; SKY-018 retains its
  reconciliation roadmap; SKY-024 retains fleet migration. Cross-link completed fixes there rather
  than implementing them twice. Leave SKY-023 history intact and reconcile its close-out separately.

## 3. Plan

Eight phases, each approximately 1–2 hours; split any phase that exceeds that size. Implementation
PRs are separate from this planning PR. No autonomy promotion, new credentials, trust expansion,
or live operation is authorized by minting this directive.

Repo work is T1. Later deploy/snapshot actions are supervised T2, workload-root backup/restore work
is T2+, and hypervisor/Unraid recovery is T3. Phase 6 must include the constitution in its PR because
it corrects T3 recovery instructions; retain its existing authority and boundaries. Every live phase
needs a stated target, recovery path, and the normal approval/grant. Credential handling, destructive
actions, T3 operations, and failed rollback remain **hard checkpoints**. Repo rollback is a reviewed
`git revert`; data recovery always preserves a separate pre-change copy.

### Phase 1 — Deploy verdicts and source consistency `[ ]`

Fix F1/F2 in the existing deploy path. Make transport errors, absent/partial containers, unhealthy
containers, missing required healthchecks, failed redeploy, and timeout nonzero. Match expected
service/image/config revision; materialize environment atomically from the reviewed revision.
Correct default/`--gate`/`--no-deploy` behavior and runbook/header claims without adding a bypass.
**Exit:** boundary-stub tests exercise the real probe and deploy sequence; no false success in the
reported cases, no secret output, and no false no-deploy promise. Live check, if needed: scoped T2.

### Phase 2 — Saved-plan recovery state `[ ]`

Fix F3. Refuse mixed create/update before snapshot/apply; explicitly check validated action shapes,
IDs, state recovery eligibility, and command failures. Preserve a restrictive recovery artifact on
recovery failure. Define concurrency/locking so restoration cannot overwrite unrelated newer state.
**Exit:** update-only recovery remains covered; create-only preserves its operator-recovery behavior;
mixed actions cause no mutation; a failed snapshot rollback never force-restores state. Do not run
live failure injection on production guests.

### Phase 3 — Trustworthy backup outcomes `[ ]`

Fix F4. Validate repository readiness, required selection, timer activation, and Docker enumeration.
Do not regenerate a lost password for an existing repository or claim provisioned after failure.
**Exit:** auth/network/init/timer/path/list/inspect failure fixtures all produce honest failure;
healthy fixtures include every intended protected path. Deploy only under the required host grant.

### Phase 4 — Consistent service recovery `[ ]`

Fix F5 for one representative protected database/service, then document the reusable pattern.
Define backup consistency, staged restore, preserved destination, ownership, compatible source
revision, paused reconciliation, and application-level verification. Do not imply a hook exists
until implemented. Avoid a generic restore framework.
**Exit:** isolated fixture/disposable-target recovery proves the chosen pattern and a failed restore
preserves the prior target. Live restore or destructive cleanup is a separate explicit checkpoint.

### Phase 5 — Safe PBS mirror source `[ ]`

Fix F7 in the source preflight and unit/procedure. Check datastore identity/mount, stable source,
and deletion guard before sync. Document mirror limitations once in backup policy.
**Exit:** missing/wrong/empty-source and concurrent-maintenance simulations never reach destructive
sync; valid-source copy and post-copy checks are distinguished from PBS restore verification.
Remote installation requires its grant; no production mirror deletion as a test.

### Phase 6 — Fleet and disaster runbook correctness `[ ]`

Fix F6. Route updates by OS and managed declaration, including unpooled core guests where allowed;
keep excluded guests excluded. Specify rollback-failure stop behavior. Correct core DR tiers and
PBS restore destination permissions; align with git-first system reconstruction and payload restore.
**Exit:** a cold walkthrough identifies exact host/tool/authority for each step, and no NixOS guest
is sent through apt. Include `docs/system-design.md` in the PR with existing boundaries unchanged.
Full core-loss live drill remains an explicit T3 checkpoint, never claimed from a prose walkthrough.

### Phase 7 — Honest collection and one CLI owner `[ ]`

Fix F8/F9. Publish explicit unavailable/stale/optional-skip evidence; validate and atomically replace
collector outputs. Remove the competing CLI updater and timer after checking callers; use the
existing Nix package-update process. Test required failure and optional absence separately.
**Exit:** consumers cannot label stale inputs fresh/OK; no npm update or model-self-query scheduler
remains, and Home Manager configuration has one writer.

### Phase 8 — Prune and reconcile `[ ]`

Fix F10/F11. Remove the named narratives and stale rollback promises, link duplicate standards,
reconcile metadata and completed directive placement, and cross-link ownership with SKY-012/016/018/024.
Use focused hygiene fixtures plus a semantic pass; preserve actionable limitations and real import
compatibility. Keep a compact PR deletion rationale for any removed executable and its former callers.
**Exit:** runbooks are executable as written, all findings have code/test evidence or an explicit
blocked dependency, catalogs are regenerated, relevant local/CI checks pass, and production claims
are limited to actual recorded exercises. No new formatting-budget machinery.

## 4. ▶ Execute prompt

```text
Read planning/ideas/SKY-025-make-operational-outcomes-verifiable-and-prune-misleading-guidance.md.
Use bin/plan start SKY-025, then execute Phase 1 only from its new planning/projects path.
Follow AGENTS.md. Recheck the cited defect on current main before changing it. Use tests that stub
external commands rather than replacing the behavior under test. Do not merge authored PRs or run
production failure injection. Stop at the listed grant/T3/destructive checkpoints. Finish with the
phase close-out below.
```

## 5. Phase close-out

- Open one reviewable PR with the defect, resulting behavior, test evidence, and remaining limitations.
- Journal raw evidence; refresh `SKY-025-progress` memory and its pointer when available.
- Set the phase checkbox, `current_phase`, and `updated` consistently; regenerate `bin/plan list`.
- On final completion set `status: done` and archive with `bin/plan archive SKY-025`.

**Continue prompt:**

```text
Continue SKY-025 at the next incomplete phase. Resolve its current path with bin/plan show SKY-025.
Read that phase, its findings, and [[SKY-025-progress]]. Recheck current main, follow AGENTS.md,
respect the listed checkpoints, and close out with a PR and evidence. Do not self-merge.
```

## 6. Status log

- 2026-09-06 — Minted from source review at `749f08a`; local boundary stubs reproduced false-positive
  deployment health, unsafe whole-state restoration for mixed guest actions, and masked restic init
  failure. Planning only; implementation and live recovery evidence remain pending.
