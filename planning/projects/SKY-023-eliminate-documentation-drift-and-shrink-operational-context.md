---
id: SKY-023
title: Eliminate documentation drift and shrink operational context
status: in-progress
horizon: short
created: 2026-09-04
updated: 2026-09-06
phases: 9
current_phase: 5
tier_touched: [T1]
related:
  - AGENTS.md
  - README.md
  - docs/system-design.md
  - docs/design/
  - docs/conventions/
  - runbooks/
  - scripts/
  - bin/
  - tofu/
  - nix/
  - hosts/
  - compose/
  - tests/documentation-drift-test.sh
  - templates/runbook.md
  - templates/script.sh
  - "[[SKY-023-progress]]"
---

# SKY-023 · Eliminate documentation drift and shrink operational context

> Keep Skynet's operational surface current, lean, and boring: current truth and executable guidance
> in live files; history in history-bearing files; obsolete compatibility machinery deleted when it
> no longer serves a current recovery or migration need.

## 1. Problem

Phases 1–4 removed major contradictions and context bloat, but the follow-up repository pass after
completion found a deeper recurring failure class: **temporal crud** survives in live operational
artifacts even when the underlying behavior is correct.

Examples include completed directive/phase provenance in OpenTofu and Nix comments, scripts explaining
what they replaced, runbooks carrying dated proof stories, current docs describing old hosts or retired
paths, and migration helpers remaining in normal maintenance flows after the migration is effectively
finished. The existing drift test catches selected stale identifiers, but not the class itself.

This matters for three reasons:

1. **Cold-agent accuracy:** historical narration looks like current instruction and can resurrect dead
   assumptions.
2. **Context cost:** every "we used to..." paragraph consumes tokens without helping current operation.
3. **Entropy:** if old compatibility paths and old stories remain indefinitely, future agents imitate
   them and the repo slowly becomes an archaeological site instead of an operating system for the lab.

## 2. Decisions

- **Current-state surfaces are timeless interfaces.** `AGENTS.md`, `README.md`, current design and
  conventions, `runbooks/`, `scripts/`, `bin/`, `tofu/`, `nix/`, `hosts/`, and `compose/` describe
  what exists, how to operate it, why a present constraint exists, how to verify it, and how to roll
  it back. They do not narrate project chronology.
- **History has explicit homes.** Raw events belong in `journal/`; frozen project history in
  `docs/history/` and `planning/archive/`; durable architectural rationale in ADRs. Git history remains
  the final provenance record.
- **Compatibility fact != provenance.** "Provider does not round-trip `vm_id`, so ignore it" is useful.
  "SKY-018 P11 proved this" is not. Preserve present constraints; delete the birth story.
- **Specific directive IDs do not belong in live operational artifacts.** Generic `SKY-###` planning
  syntax is fine. Completed/active numeric directive references belong in planning/history/evidence,
  not runtime/config/runbook prose.
- **Delete dead machinery, do not cosmetically rename it.** A path kept solely because an old system
  once needed it must either prove a current recovery/migration use or leave the normal operational
  surface.
- **No broad blind deletion.** Every candidate is classified as current constraint, current procedure,
  future work, historical provenance, or dead machinery before removal.
- **No authority change.** This directive changes repository hygiene and dead code paths only. Any
  trust-tier, credential, firewall, backup, recovery, or infrastructure boundary change stops and
  becomes its own human-approved decision.

## 3. Scope and boundaries

**Current-authority surfaces for this maintenance pass:**

- `AGENTS.md`, `README.md`
- `docs/` except `docs/history/`, `docs/decisions/`, and machine-generated `docs/generated/`
- `runbooks/`
- `scripts/`, `bin/`
- `tofu/`
- `nix/`, `hosts/`, `flake.nix`
- `compose/` including service READMEs/config comments
- repository-facing templates and lint tests

**History-bearing surfaces intentionally excluded from temporal cleanup:**

- `journal/`
- `planning/scratchpad/`
- `planning/archive/`
- `docs/history/`
- ADR `History` sections and evidence references
- generated digest/state pages whose job is to summarize time-varying state

**Non-goals:** rewriting history to look clean, live infrastructure mutation, autonomy promotion,
permission changes, secret rotation, destructive guest/service changes, or removing a compatibility
path without proving it has no current caller/recovery purpose.

**Rollback:** `git revert` each phase PR. **Human actions:** review/merge only; no grants or live
credentials should be required.

## 4. Completed foundation

### Phase 1 — reconcile truth before pruning  `[x]` complete 2026-09-05

Resolved unsafe operational contradictions against runtime/test evidence: saved-plan OpenTofu,
Arcane env materialization, trust boundaries, restore status, grant behavior, and drift semantics.

### Phase 2 — restore the documentation ownership model  `[x]` complete 2026-09-05

Shrank the constitution/design corpus and re-established constitution vs spoke vs runbook vs journal
ownership. Historical evidence was moved out of current design prose.

### Phase 3 — prune operational context and consolidate maintenance paths  `[x]` complete 2026-09-06

Repaired the nightly merge gate, split oversized publishing runbooks, standardized runbook shape,
fixed digest resolution, consolidated the nightly sequence, and removed editor artifacts.

### Phase 4 — make known drift classes fail CI  `[x]` complete 2026-09-06

Added deterministic documentation drift, nightly, merge-gate, and artifact hygiene regressions to CI
and pre-commit. Close-out evidence:
`journal/2026/2026-09-06-session-sky-023-phase-3-and-4-close-out.md`.

## 5. Reopened maintenance plan

### Phase 5 — temporal-hygiene purge: prose and operational docs  (~1–2h)  `[ ]`

Build a temporary **crud matrix** with columns: path, offending text, class, present-day dependency,
action, destination/owner. Do not commit the matrix as current design; summarize it in the phase PR
and journal close-out.

Sweep `AGENTS.md`, `README.md`, current `docs/`, `runbooks/`, and `compose/*/README.md` for:

- numeric completed/active directive provenance (`SKY-023`, `SKY-021 P3`, etc.);
- old host/CT/VM stories, previous topology, dated migration narrative, "used to", "previously",
  "retired", "replaced", "introduced", "piloted", "witnessed", or dated proof anecdotes;
- implementation-status prose that should simply state current capability or current absence;
- repeated philosophy that belongs in a convention/ADR rather than a task procedure;
- runbook sections whose only purpose is explaining an already-finished migration.

Known candidates from the reopening audit include:

- `docs/conventions/naming.md` historical VMID/addressing posture and old `lxc-adguard-core` examples;
- `docs/architecture.md` directive-linked implementation status and legacy-env data flow;
- `docs/design/secrets.md` directive-labelled per-CT identity design and legacy-import narration;
- `docs/backup-strategy.md`, `runbooks/restore-service.md`, and DR runbooks carrying dated proof stories;
- `compose/cloudflared/README.md` credential reconstruction and retired-CT story;
- `runbooks/nightly.md` and `runbooks/deploy-service.md` treating old migration behavior as ordinary
  steady-state operation.

For each removal, preserve the **current operational consequence**. Example: replace a dated recovery
story with "targeted Drive→PBS archive recovery is verified; full core-loss recovery is not yet
verified" if that distinction still affects decisions.

**Exit:**

- no numeric `SKY-NNN` provenance remains in the scoped prose surfaces unless the file is itself a
  planning/history/evidence surface;
- runbooks contain procedures, preconditions, verification, rollback, and current gotchas only;
- no old guest/topology anecdote is required to understand a current rule;
- all removed load-bearing facts still have one current authoritative home.

### Phase 6 — temporal-hygiene purge: code, config, OpenTofu, Nix  (~1–2h)  `[ ]`

Sweep live code/config comments and user-visible runtime strings across `scripts/`, `bin/`, `tofu/`,
`nix/`, `hosts/`, `flake.nix`, `.sops.yaml`, and compose/config files.

Prioritize known contamination:

- `tofu/pool-cts.tf`: phase labels, "the SKY-021 lesson", migration candidates, and "adguard-core was
  a standalone resource" narration while preserving required `moved` blocks/provider state semantics;
- `tofu/lxc-pbs.tf`, `tofu/cloudflare-dns.tf`, `tofu/versions.tf`, `tofu/dns-aliammar-net.tf`, and
  template declarations: remove directive/provenance comments while preserving provider limitations,
  derivation rules, saved-plan safety, and import constraints;
- `flake.nix`, `nix/modules/*`, and `hosts/*`: remove proof/pilot/phase language; describe only each
  module/host's current role;
- `.sops.yaml`: comments explain recipient/path semantics only, never which directive introduced them;
- `scripts/build-db.sh`, `audit-entities.sh`, `pve-snapshot.sh`, `collect-firewall.sh`, `cf-dns-route.sh`,
  `render-docs.sh`, and `bin/ops`: strip directive/phase provenance and historical replacement stories;
- `bin/grant-root`: remove "NO LONGER"/rehearsal/status history; state current per-host certificate
  behavior directly;
- user-visible generated labels/descriptions such as snapshot descriptions must be timeless and must
  not embed a directive/phase ID.

Do not remove comments that explain a non-obvious current safety property, provider bug, parse rule,
state-address requirement, or compatibility behavior.

**Exit:**

- numeric `SKY-NNN` provenance is absent from live code/config comments and runtime descriptions;
- every remaining comment answers "what does this do now?", "why is this current constraint needed?",
  or "what breaks if changed?";
- OpenTofu state moves/import ignores and other load-bearing compatibility mechanics remain intact;
- syntax/unit/invariant tests pass unchanged or stronger.

### Phase 7 — remove dead migration and compatibility machinery  (~1–2h)  `[ ]`

Now inspect the **behavior**, not just the prose. For every migration/compatibility path discovered in
Phases 5–6, trace callers and prove whether it still has a current job.

Use repository references, tests, current configuration, and documented DR requirements to classify
it as one of:

1. **steady-state capability** → keep and rename/document as steady state;
2. **break-glass/DR capability** → keep, move out of the normal path, and make the trigger explicit;
3. **one-time migration utility still intentionally available** → isolate under a clearly named
   migration surface and remove it from nightly/everyday runbooks;
4. **dead path** → delete code, docs, tests, caller branches, and stale config together.

Explicit candidates to adjudicate:

- `scripts/envsync.sh` and the nightly "legacy env import" stage;
- the legacy non-GitOps cutover section in `runbooks/deploy-service.md`;
- `scripts/collect-firewall.sh` as an offline/DR parser versus obsolete nightly collector;
- `scripts/cf-dns-route.sh` now that Cloudflare tunnel CNAME creation is declarative;
- `lxc-proof`/proof-template naming and resources if production provisioning still depends on what was
  originally a throwaway proof artifact;
- obsolete single-cert, retired-host, old credential-name, old wildcard-DNS, or compatibility branches
  surfaced by the sweep.

A deletion requires evidence of **no current caller + no documented recovery dependency**. If uncertain,
keep the capability but remove it from normal execution and file an explicit follow-up rather than
silently deleting it.

**Exit:**

- normal nightly/deploy/provision flows contain no completed-migration stage;
- every retained compatibility helper has a current trigger and owner;
- every dead helper is removed with its callers/tests/docs in the same PR;
- no live infrastructure is changed by this phase.

### Phase 8 — make temporal crud fail locally and in CI  (~1–2h)  `[ ]`

Turn the policy into deterministic guardrails.

1. Extend `tests/documentation-drift-test.sh` or add a focused temporal-hygiene test covering the
   current-authority surface set above.
2. Add a **hard gate** against specific numeric directive references (`SKY-[0-9]{3}`) in current
   operational surfaces. Permit generic `SKY-###` syntax where planning mechanics are documented.
3. Add a **small, explicit narrative-pattern gate** for high-signal archaeology phrases such as
   `used to`, `previously`, `formerly`, `retired`, `replaced`, `introduced by`, `validated during`,
   and directive phase notation. Avoid banning words like `legacy`, `imported`, `compatibility`, or
   `deprecated` globally because they can describe present behavior.
4. If a legitimate current sentence collides with a heuristic, prefer rewriting it as a current-state
   constraint. Use a tiny reviewed allowlist only when rewriting would make the artifact less clear.
5. Update `docs/conventions/docs.md` and `docs/conventions/scripts.md` with the current-state-only rule:
   history/provenance goes to journal/history/ADR; live artifacts contain only present behavior and
   load-bearing current rationale.
6. Update `templates/runbook.md` and `templates/script.sh` with an author-only reminder that history,
   completed directive IDs, migration chronology, and "what this replaced" narration do not belong in
   the finished artifact.
7. Wire the gate to both pre-commit and CI. Add positive and negative fixture tests so future agents
   cannot satisfy the rule by merely changing wording around a stale directive reference.

**Exit:**

- adding `# SKY-021 P3 — ...` to a live script/tofu file fails before merge;
- adding "this replaced the old CT..." to a runbook/current doc fails or has to be rewritten;
- legitimate current provider/import/compatibility comments still pass;
- history-bearing directories remain free to record history without lint noise.

### Phase 9 — make hygiene a repeatable maintenance capability and re-archive  (~1–2h)  `[ ]`

Create one deterministic, T1, no-network-by-default maintenance entry point, preferably
`bin/ops hygiene` backed by a small script, that composes existing checks rather than inventing another
parallel policy engine.

It should report at least:

- temporal-hygiene violations;
- broken/missing current-authority links and script references;
- stale completed-directive paths/identities already covered by drift tests;
- obvious orphan migration helpers or unreferenced operator scripts as **review candidates**, not
  automatic deletions;
- runbook catalog divergence and task-shape failures;
- size/token deltas for always-loaded/current-authority surfaces so context bloat is visible.

Keep destructive cleanup human-reviewed. The hygiene command may propose candidate removals; it must
never delete files, rewrite docs, or modify live systems by itself.

Then perform a cold-agent verification:

1. start from `README.md`/`AGENTS.md`/context map only;
2. locate deploy, provision, restore, publish, backup, and DR procedures without reading historical
   files;
3. search current-authority surfaces for numeric directive provenance and high-signal archaeology;
4. run full CI/pre-commit/invariant/syntax checks;
5. record before/after word/token counts and a short list of intentionally retained compatibility
   exceptions with their current reason.

Archive SKY-023 again only when the repo passes both the deterministic gates and the cold-agent review.
Future recurrence should be handled by the same hygiene command/gates; reopen SKY-023 only when a new
maintenance failure class requires changing the policy or toolchain itself.

**Exit:**

- `bin/ops hygiene` gives one concise maintenance report and is safe to run repeatedly;
- current operational surfaces read as if the system sprang into existence in its current form;
- all tests are green and no trust/authority boundary changed;
- SKY-023 returns to `planning/archive/` with Phase 9 complete and a journal close-out.

## 6. ▶ Execute prompt

```
Read planning/projects/SKY-023-eliminate-documentation-drift-and-shrink-operational-context.md in full.
Read the relevant convention and current-authority files for the phase. Verify repository reality before
editing. Execute Phase <N> only. Preserve current operational constraints while deleting provenance and
dead machinery. Never rewrite journal/history to make the sweep pass. Never hand-edit generated docs.
Never merge your own authored PR. Validate every phase exit criterion, update SKY-023 progress, run the
roadmap renderer, and close out with the exact next phase.
```

## 7. Phase close-out

- One reviewable PR per phase or bounded checkpoint; do not mix unrelated infrastructure work.
- Record what was deleted, what was retained and why, checks run, and any uncertain candidate deferred.
- Update `[[SKY-023-progress]]`, `current_phase`, and the phase checkbox only after exit criteria pass.
- Regenerate the planning roadmap through its owner (`bin/plan list`).
- Continue with:
  `Continue SKY-023 at Phase <N+1>; read [[SKY-023-progress]], verify reality, and execute only that phase.`

## 8. Status log

- 2026-09-04 to 2026-09-06 — original four-phase documentation-drift cleanup completed and archived.
  Detailed evidence remains in the SKY-023 journal entries and git history.
- 2026-09-06 — reopened by explicit human instruction after a post-completion pass found temporal
  provenance and dead-migration residue across current docs, runbooks, scripts, OpenTofu, Nix, and
  config comments. Phases 5–9 add systematic purge, dead-path adjudication, deterministic enforcement,
  and a repeatable maintenance capability. No live infrastructure or authority boundary is changed by
  this planning update.
