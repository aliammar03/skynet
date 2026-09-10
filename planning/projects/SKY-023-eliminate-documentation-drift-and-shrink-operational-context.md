---
id: SKY-023
title: Eliminate documentation drift and shrink operational context
status: in-progress
horizon: short
created: 2026-09-04
updated: 2026-09-06
phases: 10
current_phase: 10
tier_touched: [T1, T2]
related:
  - AGENTS.md
  - CLAUDE.md
  - README.md
  - .codex/
  - .claude/
  - .githooks/
  - .github/
  - ca/
  - docs/
  - runbooks/
  - scripts/
  - bin/
  - tofu/
  - nix/
  - hosts/
  - compose/
  - flake.nix
  - tests/temporal-hygiene-test.sh
  - tests/documentation-drift-test.sh
  - scripts/hygiene.sh
---

# SKY-023 · Eliminate documentation drift and shrink operational context

> **2026-09-07 ownership:** This directive keeps its open P10 classifier/residue and LXC identity close-out. SKY-025 removes conflicting guidance it touches and owns engine-related pruning, preserving the hygiene gates; it does not accept P10 or PR #203.
> See the [SKY-025 disposition map](../sky-025-map.md#adjacent-directive-ownership). This note does not complete any phase.

> Keep Skynet's live repository surface current, lean, and boring. History lives in history-bearing
> surfaces; current files describe only the system that exists now and the instructions needed to
> operate it safely.

## 1. Current decision

SKY-023 Phases 1–9 are complete. They reconciled contradictory operational truth, shrank the design
and runbook corpus, removed dead migration machinery, added temporal/documentation drift gates, and
introduced `bin/ops hygiene`.

A post-completion cold review found one remaining design flaw in that hygiene system: **current
authority is defined by a hand-maintained positive list of known directories.** New live surfaces can
therefore escape the guard entirely. The current misses prove the failure class:

- `.codex/agents/*.toml` and `.codex/config.toml` still carry completed directive provenance and
  research-story comments;
- `.githooks/pre-commit` still narrates the directives/phases that introduced tests;
- `ca/README.md` still names deleted `envsync` behavior;
- `CLAUDE.md` restates merge policy instead of remaining a pure import shim;
- `flake.nix` retains directive/provenance residue;
- the production NixOS LXC bootstrap artifact still uses the proof-era `lxc-proof` identity.

The permanent rule is now inverted:

> **All tracked textual repository content is current authority unless it is explicitly classified as
> planning, history/evidence, generated output, encrypted payload, binary/vendor data, or test fixture.**

An unknown tracked text file is a classification failure, not an implicit exemption.

## 2. Completed foundation

- **P1–P4:** truth reconciliation, authority ownership, task-shaped runbooks, deterministic drift gates.
- **P5–P6:** temporal/provenance purge across prose, code, config, OpenTofu, Nix, and runtime labels.
- **P7:** dead compatibility audit; deleted `envsync`, retained only proven current DR/break-glass paths.
- **P8:** temporal-hygiene pre-commit/CI gate.
- **P9:** `bin/ops hygiene`, context-budget reporting, cold-agent review, and re-archive.

Detailed phase history remains in git and the SKY-023 journal episodes. Do not copy it back into live
operational files.

## 3. Phase 10 — close the classifier gap + retire `lxc-proof`  `[ ]`

### A. Make repository classification complete by construction  `[T1]`

1. Create **one shared repository-surface classifier** used by temporal hygiene, documentation drift,
   and `bin/ops hygiene`. Do not maintain three path lists.
2. Enumerate tracked files from git, then classify each textual file into exactly one class:
   - **current** — live operational/config/agent/tooling content; default for tracked text;
   - **planning** — `planning/`;
   - **history/evidence** — `journal/`, `docs/history/`, ADR history/evidence where appropriate;
   - **generated** — renderer-owned `docs/generated/` and other explicitly generated outputs;
   - **fixture/test-data** — narrow paths whose purpose is deliberately invalid/example content;
   - **opaque** — encrypted/binary/vendor payloads that prose lint cannot safely interpret.
3. **Fail CI for an unclassified tracked file or multiply-classified file.** Adding a new top-level
   operational directory must automatically enter `current` without editing the classifier.
4. Make the shared classifier drive:
   - numeric directive-provenance checks;
   - historical-narrative checks;
   - current-authority link/script validation where applicable;
   - `bin/ops hygiene` current-authority/context-budget totals.
5. Replace the permanent `b6dea99` comparison default in `scripts/hygiene.sh`. Accept an explicit
   comparison ref when requested; otherwise report current totals and stable configured thresholds,
   not allegiance to a historical reopening commit.
6. Add regression fixtures proving:
   - a new unknown top-level text file is treated as current and linted automatically;
   - `.codex/`, `.githooks/`, `ca/`, `CLAUDE.md`, and root config files are covered;
   - planning/history/generated/fixture content remains intentionally exempt from temporal prose rules;
   - an unclassified/ambiguous classification fails closed.

### B. Purge the residue the old classifier missed  `[T1]`

1. `.codex/agents/*.toml` and `.codex/config.toml`: remove numeric SKY provenance, benchmark/rework
   backstory, and phase references. Keep only the current role, model/effort/sandbox, limits, and link
   to the canonical construction contract.
2. `.githooks/pre-commit`: describe what each gate verifies **now**; remove the directive/phase origin
   story from comments.
3. `ca/README.md`: remove deleted `envsync` from the standing `svc-ops` key description and verify the
   remaining access examples are current.
4. `CLAUDE.md`: reduce to a true engine shim. It imports `AGENTS.md` and names the authoritative design;
   it does not restate merge, trust, or safety policy.
5. Sweep `.claude/`, `.github/`, root configs, `ca/`, and other newly covered current files for the same
   residue. Remove `ATH-000`/similar provenance from `flake.nix` while preserving current Athena
   ownership and break-glass instructions.

### C. Replace the proof-era NixOS LXC identity  `[T1 + T2]`

The canonical generic bootstrap identity becomes **`lxc-base`**. This is a coordinated artifact
migration, not a search-and-replace.

1. Rename the generic Nix host/configuration surface:
   - `hosts/lxc-proof/` → `hosts/lxc-base/`;
   - `nixosConfigurations.lxc-proof` → `nixosConfigurations.lxc-base`;
   - `lxc-proof-tarball` → `lxc-base-tarball`;
   - generic configuration hostname/marker text becomes production-neutral;
   - remove the generic `deploy.nodes.lxc-proof` target unless a real long-lived `lxc-base` guest is
     intentionally required. A build template does not need a fake production deploy identity.
2. Build the replacement artifact from the canonical flake target and name it
   **`nixos-lxc-base-26.05.tar.xz`** (or the renderer/build's equivalent deterministic filename).
3. Before changing Tofu, upload the new template to the required Proxmox storage through the approved
   T2 path and verify the exact storage ID is readable by the Proxmox API/provider.
4. Change every **new-create** OpenTofu bootstrap reference from
   `local:vztmpl/nixos-lxc-proof-26.05.tar.xz` to the new `lxc-base` artifact.
5. Preserve imported-guest lifecycle semantics. A live imported CT whose source template is unreadable
   and ignored must not be recreated merely to rename its historical bootstrap artifact.
6. Run a saved plan and prove existing CTs are **no-op**. If the plan proposes replacement/destroy of an
   existing guest, stop and fix the declaration before any apply.
7. Prove the new path with the least-destructive valid test available: provider/config validation plus
   an approved disposable create when needed to demonstrate the template actually boots and accepts the
   Nix day-two path. Destroy the disposable guest through the normal reviewed cleanup path.
8. Only after the new template is referenced, verified, and no current declaration needs the old file,
   remove `nixos-lxc-proof-26.05.tar.xz` from Proxmox storage. Do not delete historical journal/planning
   references to the old artifact.
9. Update current runbooks/docs/tests to say `lxc-base`; historical evidence remains untouched.

### D. Close-out

Run the full pre-commit/CI suite, `nix flake check --no-write-lock-file`, the strengthened hygiene
report, OpenTofu format/validate/saved-plan checks, and a cold-agent review from README/AGENTS/context map.
Record the live template upload/removal and any disposable-create evidence in a journal entry.

**Exit criteria:**

- every tracked textual file has exactly one classifier outcome and unknown operational surfaces fail
  closed;
- current authority contains no numeric directive provenance or high-signal project archaeology outside
  explicitly historical/planning/evidence classes;
- `.codex`, `.githooks`, `ca`, `CLAUDE.md`, root configs, and future new operational directories are
  covered automatically;
- `CLAUDE.md` contains no duplicated operating policy;
- `ca/README.md` contains no `envsync` claim;
- the canonical generic NixOS LXC build target and Proxmox template are named `lxc-base`, with no
  `lxc-proof` reference remaining in **current** operational authority;
- existing production CTs show no destructive/replacement drift from the template rename;
- the new template path is verified usable before the old artifact is removed;
- full local/CI/Nix/Tofu checks pass and no authority/trust boundary changes.

## 4. ▶ Execute prompt

```text
Read planning/projects/SKY-023-eliminate-documentation-drift-and-shrink-operational-context.md in full.
Execute Phase 10 only. Treat all tracked text as current authority unless the shared classifier explicitly
places it in planning/history/generated/fixture/opaque classes. Purge the residue exposed by the old
positive-list model. Then migrate the generic NixOS LXC bootstrap identity from lxc-proof to lxc-base as
a coordinated build/upload/tofu/verify/retire operation. Do not recreate existing CTs merely to rename a
bootstrap template. Use reviewed saved plans, stop on destructive drift, preserve history-bearing files,
and follow AGENTS.md for every T2 action. Land authored changes through a human-merged PR and re-archive
SKY-023 only after every Phase 10 exit criterion passes.
```

## 5. Close-out

- One bounded Phase 10 implementation PR, or split repo-only and live-template checkpoints only if the
  T2 upload boundary makes one reviewable PR unsafe.
- Journal the evidence, not the current docs.
- On completion: set Phase 10 `[x]`, keep `phases: 10`, `current_phase: 10`, mark `status: done`, run the
  roadmap renderer, and return SKY-023 to `planning/archive/`.
