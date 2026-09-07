---
summary: "SKY-025 subsystem dispositions, external callers, output contracts, and deployment blockers."
---

# SKY-025 · Repository disposition map

Owned by [the directive](projects/SKY-025-make-operational-outcomes-verifiable-and-prune-misleading-guidance.md).
Baseline: `670f06cfa75ca95a9eac7fdb1d3eb3544272ff1a` (remote main, 2026-09-07).
Phase 1 is accepted at G1; Phase 2 is accepted at `17db700c22cb17ad219655674eada344c215029a`. Its local package
is built only in the isolated checkout and is not installed or activated on any lab host. This map
describes planned replacements; it does not claim that Python is installed. The baseline's 398 tracked paths were enumerated with
`git ls-files`; the grouped families below cover them. `scripts/` names are relative to that directory.
**Verified** means source/caller inspection, not a successful production operation. **Blocked** names
a later phase's missing live evidence. No blanket shell compatibility or duplicate production engine.

Enumeration counts: root files 10; `.claude` 1, `.codex` 4, `.githooks` 1, `.github` 2,
`.obsidian` 5; `bin` 6, `ca` 3, `compose` 40, `docs` 42, `hosts` 5, `inventory` 14,
`journal` 77, `nix` 14, `planning` 47, `runbooks` 24, `scripts` 50, `secrets` 16,
`templates` 7, `tests` 19, `tofu` 11. These are baseline counts, not a manifest to maintain.

## Dispositions by subsystem

| Surface | migrate/retain/delete | Replacement/owner | Callers | Phase | verified/blocked |
|---|---|---|---|---|---|
| `bin/ops`; `collect-all.sh` | migrate | Thin `skynet` dispatch and explicit workflow results | Humans, runbooks, nightly | 2–9, 20 | Verified dispatch and Nix timer references |
| `collect-proxmox.sh`, `collect-proxmox-acl.sh` | migrate | Python read collectors; node-specific validation | collect-all, inventory gates/renderers | 3–4 | P3a builds isolated core collector; P3b owns default-caller/freshness integration; network/ACL remain P4. Live behavior untested |
| `collect-pbs.sh`, `collect-docker.sh` | migrate | Python PBS/Docker collectors | collect-all, backup/container views | 5 | Verified current callers; preserve unavailable states |
| `collect-dns.sh`, `collect-opnsense.sh`, `collect-firewall.sh` | migrate | Python DNS/live OPNsense collection and offline mirror parsing | collect-all, firewall/DNS views; ADR 0006 offline recovery | 6 | Verified live/offline distinction; no new OPNsense writer |
| `collect-network-gear.sh`, `collect-certs.sh`, `collect-routes.sh`, `recon.sh` | migrate | Python observations with provenance and vantage | collect-all, recon/diagnosis runbooks | 7 | Verified callers; static declarations cannot imply live discovery |
| `entity.sh`, `audit-entities.sh`, `build-db.sh` | migrate | Entity functions, audit, rebuildable SQLite cache | collectors/render-docs, bin/ops entities/query | 8 | Verified existing identity and join callers |
| `scripts/sql/*.sql` | retain | SQL query definitions | bin/ops query, SQLite cache | 8 | Verified host-map/vhosts queries; adapt schema with consumers |
| `render-docs.sh`, `render-digest.sh`, `render-context-map.sh`, `render-runbook-catalog.sh`; `bin/recall` | migrate | Python rendering/retrieval, existing Markdown sources | nightly, bin/ops, cold boot, catalog checks | 9 | Verified outputs; history remains append-only |
| `deploy-gate.sh`, `gitops-deploy.sh`, `gitops-rollback.sh` | migrate | Python verification/deploy/recovery evidence | deploy/restore runbooks, Arcane Git Sync procedures | 10–11 | Verified references; actual Arcane command/revision settings blocked before P11 |
| `cf-dns-route.sh`, `dns-revert.sh` | migrate | Scoped publishing/DNS workflows | publish runbooks, rollback tests | 12–14 | Verified declarative DNS/saved-plan relationship |
| `tofu-env.sh`, `tofu-apply.sh`, `pve-snapshot.sh` | migrate | Python saved-plan policy/execution and recovery | provisioning/publishing runbooks, operator contract | 13–14 | Verified scopes/exclusions; preserve refusal/recovery cases F3 |
| `backup-restic.sh`, `provision-restic.sh` | migrate | Python host-local backup and provisioning | root-granted provisioner; restic template unit | 15, 19 | Source verified; remote versions/OS and consistency methods blocked |
| `backup-pbs-gdrive.sh` | migrate | Python guarded PBS transfer | PBS host-local unit | 16 | Source verified; datastore identity/stability/retention blocked |
| `scripts/systemd/skynet-restic-backup@.*`, `skynet-pbs-gdrive.*` | retain | systemd remains scheduler; replace executable targets with packaged commands | Docker hosts/PBS host | 15–19 | Verified template paths; installed units and enabled instances blocked |
| `pin-cert.sh`, `ct-age-identity.sh`, `onboard-host.sh`, `skynet-ops-ssh-certs.sh` | migrate | Python access/onboarding validation; Nix trust config retained | manual onboarding, provisioning and certificate workflows | 18–19 | Verified source; human custody and grant boundary retained |
| `bootstrap-workstation.sh`, `bootstrap-proxmox.sh`; `bin/grant-root` | retain, review shell necessity | Human bootstrap/rescue outside ops runtime | workstation installs `~/bin/grant-root`; node bootstrap by human | 18, 22, 24 | External bootstrap caller verified in source; workstation install/access blocked. Retain only standalone recovery need; remove shell if independently packaged replacement passes rescue test |
| `nightly.sh`, `nightly-automerge.sh` | migrate | One Python nightly/report/PR sequence, same exact-PR merge gate | bin/ops nightly, ops timer | 20 | Source verified; no expansion of generated-only authority |
| `update-clis.sh` | delete | Nix package ownership, explicit configuration | weekly skynet-cli-update timer | 20–22 | Installed timer verified locally; removal must update Nix unit and local config ownership together; P2 only packages the new runtime |
| `scripts/systemd/ops.env.example` | retain/adapt | Explicit engine/operator settings only | Nix nightly unit, operator bootstrap | 20–22 | Source verified; don't preserve npm/model-self-query output |
| `check-invariants.sh`, `secret-scan.sh`, `repo-surface.sh`, `hygiene.sh` | migrate | Python deterministic gates with equivalent behavioral enforcement | hook, CI, nightly, bin/ops hygiene | 21 | Verified callers; no safety gate disabled during replacement |
| `bin/new`, `bin/plan`; `templates/**`, `planning/TEMPLATE.md` | migrate executables; retain/adapt templates | Python scaffolding/planning helpers | operators, directive/journal lifecycle | 9, 21 | Verified Bash script template is for shell needs, not mandatory new Python logic |
| `bin/agent`, `.codex/**` | retain/adapt | Existing explicit lead/review/worker launcher and native definitions | construction runbook, invoking sessions, routing tests | 1, 22 | Routing/config checked; shell removal reviewed at P22 after external callers inventoried |
| `.claude/settings.json`, `CLAUDE.md` | retain | Shared-contract import and operator permissions | Claude lead sessions | 1, 22 | Inspected: no model router or Bash-only capability rule; git-push permission does not authorize worker pushes |
| `tests/*.sh` (19 suites) | migrate useful assertions; delete obsolete mirrors | Behavioral tests/fixtures under tests | CI and pre-commit | 2–21 | Routing tests updated P1; each other suite travels with its replaced component |
| `.github/workflows/*`, `.githooks/pre-commit` | retain/adapt | Unified package/lint/type/test and invariant checks | GitHub, local Git hook | 2, 21 | Verified shell suites and Nix checks; no new workflow required |
| `flake.nix`, `flake.lock`, `hosts/**`, `nix/**` | retain/adapt | Nix packages, host definitions, timers, activation and rescue packaging | deploy-rs/Nix, Home Manager, Docker context/MOTD/login | 2, 18–23 | Source inspected; activation and live installs not run |
| `tofu/**` | retain | OpenTofu resources/providers/locks and encrypted state configuration | saved-plan executor, provision/publish runbooks | 13–14, 18 | Declarative ownership retained; local state never copied into this worktree |
| `compose/**` | retain | Compose/Caddy/tunnel/app configuration and encrypted env | Arcane, Docker, publish/deploy workflows | 11–12, 22–23 | Includes Jikan PHP/JS override assets and `.env.compose`: service code, not ops engine; payload not replaced |
| `inventory/**`, `docs/generated/**` | retain data contracts; regenerate views | Python collectors/renderers | gates, SQLite/SQL, Obsidian, cold boot | 3–9, 21–22 | Never hand-edit; format decisions below |
| `AGENTS.md`, `README.md`, `docs/system-design.md`, `docs/conventions*`, `docs/design/**`, other `docs/*.md`, `runbooks/**` | retain/adapt/prune stale guidance | One current authority per rule, commands match each replacement | human/agent operators, context/catalog/hygiene | 1, 9–24 | No future capability claimed installed; raw history excluded from cleanup |
| `docs/history/**`, `docs/decisions/**`, `journal/**`, `planning/**` except templates | retain | History, accepted decisions, working plans | recall/digest, review handoffs | 1, 9, 21, 24 | Journal append-only; adjacent directives keep unrelated work |
| `ca/**`, `secrets/**`, `.sops.yaml`, encrypted Compose payloads | retain | Existing public keys, encrypted material and custody | sops/Nix activation, SSH grants, recovery | all; 18, 24 | Filenames/source declarations only; no decrypted material read |
| `.obsidian/**` | retain | Vault settings | Obsidian and digest/doc consumers | 9, 22 | Preserve wiki-link/navigation usability; local plugin payloads not source |
| `.gitignore`, `invariants.json`, `lab.json`, `renovate.json` | retain/adapt | Ignore policy, hard laws, authored topology and update configuration | Git, invariant gates, entity/renderers, Renovate | 2, 8, 21–22 | Hard laws unchanged P1; updates require normal human merge |

No executable is retained merely to preserve the old command name. At its owning phase, update all
known callers together; a shell shim needs a demonstrated external caller or rescue requirement,
an owner, and a removal condition. Each migrate row's old implementation is deleted when that phase's
replacement/callers are accepted. A literal-reference search is advisory: indirect SSH, service-manager,
Arcane and human recovery callers require the checks below.

## Proposed package and output boundaries (G1 review)

Use one `src/skynet/` package and CLI. Add collector/client/workflow/renderer modules only when a
working slice needs them. P2 packages a minimal local command; P3 settles the first external-data
boundary through Proxmox collection and readable output. Keep ordinary functions, synchronous I/O,
stdlib-first dependencies, and Nix-owned runtime. No generic workflow/result class hierarchy or new
database. Proposed command families are those in the directive; these are not implemented commands.

Preserve inventory filenames and fields consumed by the existing invariant checker, SQL cache,
renderers, and tests until their consumers change in the same accepted slice. Collection must write
validated outputs atomically and expose source/freshness/unavailability; old files cannot masquerade as
fresh evidence. Preserve entity IDs, protected guest exceptions, authored `lab.json`, journal paths and
frontmatter, encrypted secret/state formats and recovery locations. Saved-plan source/artifact identity,
scope/action refusal and partial-write evidence are required contracts; byte-for-byte old logs are not.

Generated Markdown, roadmap/catalog formatting and `.cache/inventory.db` may be regenerated when their
consumer changes together: retain meaningful links and cold-boot filenames, not whitespace or cached
schemas by default. Optional CLI JSON must include an explicit outcome (success/failure/unavailable/
skipped/recovery-required); success exits zero and failed or indeterminate required work exits nonzero.
The first slice must settle exact keys/exit numbers and test them; a skip must state its reason and
cannot satisfy required verification. Human output and JSON must agree.

## External installs, local state, and recovery blockers

| Location/caller | Evidence and required action | Gate |
|---|---|---|
| Ops VM `/home/aliammar/skynet` | Installed nightly/update units report this WorkingDirectory. Both timers are scheduled; neither service was active at inspection. Build checkout is `/tmp/skynet-sky-025-p1`; no scheduler was paused. | Verified T1 metadata P1; agree live plan before editing/installing runtime |
| `/opt/skynet-ops/scripts/backup-restic.sh`, `backup-pbs-gdrive.sh`; remote `/etc/systemd/system/` | Tracked provisioner installs restic script; tracked unit ExecStart names both. Exact host-local versions, enabled instances, datastore paths and package availability not inspected. | Block P15/P16/P19 live replacement until scoped remote inventory |
| Arcane Git Sync and Docker mounts | Compose and deploy runbooks declare callers; actual sync commands, revisions, materialized env and mount paths not queried. | Block P11 live replacement until identified |
| Workstation `~/bin/grant-root`, `~/.skynet-ca/ops_ca` | Bootstrap installs helper; CA stays with Ali. Installed helper/version and independent access not inspected. Never fetch private key. | Block first live phase and P18/P24 recovery acceptance |
| Ops `/opt/skynet-ops/{certs,mirror}` and `/nix/persist/opt/skynet-ops` | Local cert/mirror directories exist by metadata. Nix persists `/opt/skynet-ops`, home, Docker data, systemd state, logs, SSH host identity. Mirror contents not read. | Preserve on replacement; verify recovery at first live phase |
| `/opt/skynet-ops/secrets/`, `/run/secrets`, per-CT age identity | Nix declarations own materialization and persistent age path; no secret contents inspected. Preserve existing recovery/custody rules. | No rotation or new credential handling authorized P1 |
| Main checkout `.cache/`, `.claude/settings.local.json`, `result`, `tofu/.terraform`, `tofu/*.tfstate*` | Ignored-file names show SQLite/nightly logs, local settings, build output, provider cache and state/backups. No contents read or copied. State is recovery-critical; caches/build outputs are rebuildable. | Capture/verify state recovery before live execution; never blanket-clean ignored files |
| `.agent/`, `.obsidian/workspace*.json`, `.obsidian/plugins/`, effective Compose `.env`/`project.env`, credential/SSH files | Declared ignored/runtime classes; existence not inferred. Home also holds engine auth/config, gh auth, ops.env and SSH material per Nix/runtime contracts. | Inventory metadata only before affected install; do not remove to simplify rebuild |

Survival-kit source: [runbooks/dr/survival-kit.md](../runbooks/dr/survival-kit.md), plus
[core](../runbooks/dr/DR-core-node.md) and [network](../runbooks/dr/DR-network-node.md) recovery.
**Not verified:** workstation access, protected payload/state recovery points, kit keys, a concrete
independent rebuild/access command and its execution. These must be named and demonstrated in the
first live packet; this T1 construction phase is not a recovery drill. No services were stopped.
Before G5, name required services/backup jobs, a representative approved write and isolated restore
target here; that bounded set is not selected or implicitly authorized by P1.

## Adjacent directive ownership

SKY-025 owns engine replacement and its F1–F11 correctness work. No adjacent phase is marked complete.

| Directive | Ownership/dependency decision |
|---|---|
| SKY-005 | P7 replaces existing recon implementation; diagnosis practice and deferred lab bench stay SKY-005. |
| SKY-006 | P9 owns current digest/recall/journal tooling replacement; optional semantic retrieval remains SKY-006. Preserve raw journal, no competing writer. |
| SKY-012 | Existing capability contracts carry into Python; additional executable-runbook features remain SKY-012. No generic workflow framework added. |
| SKY-015 | Keep SKY-018's existing supersession/close-out decision. P8–9 replace implemented entity/renderer surfaces; do not launch a duplicate renderer project. |
| SKY-016 | P10–12 own replacement and existing health/reachability defects. Additional deployment features remain SKY-016 and must consume the accepted Python verifier. |
| SKY-017 | Owns proving ground and evidence-earned promotions, budgets and circuit breakers. Python replacement grants no autonomy; consume accepted executors without building another. |
| SKY-018 | Retains eight-layer semantics and unbuilt reconciliation features. P8/P10–14/P20–21 own replacement of existing substrate/checker/executor code and its correctness cases; dependent features use accepted Python interfaces. |
| SKY-020 | Owns future OPNsense writer/provider and self-leash policy implementation. P6 replaces existing reads only; P13–14 replace existing saved-plan capabilities, not an unbuilt firewall actuator. |
| SKY-023 | Retains its open P10 classifier/residue and LXC identity close-out work. P1 removes conflicting guidance it touches; P21–22 own engine-related pruning and preserve its existing hygiene gates. No claim that P10 or PR #203 is accepted. |
| SKY-024 | Retains guest declaration/fleet migration and supervised adoption. P13–14/P18 replace executor/provisioning tooling while preserving merged-source, saved-plan, grant and exclusion boundaries. |

## Phase 1 evidence

Model identifiers/efforts were checked against installed Codex `0.153.4` model catalog metadata;
session metadata confirmed `gpt-6-astra`, medium. The exact five combinations are in the construction
convention. Luna Medium scouts performed bounded read-only audits; leads/workers were not silently
substituted. Dry-run routing is verified separately from model availability; no test claims live
execution for Terra High, Sol Low, or Luna High.

The [official configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference)
was consulted for explicit model/effort and agent configuration. Existing helper cap and sandbox
settings remain unchanged. Final check commands/results and raw inspection corrections are in the
[phase journal](../journal/2026/2026-09-07-session-sky-025-p1-repository-map-and-routing.md).
G1 accepted PR #211 at `3373fc887296cb6b32064d867f814c75266fedc5`; the directive records independent
exit evidence. P2's isolated package build, source-filter boundary, runtime-only doctor, and Nix-owned
checks are independently accepted; §5 of the directive releases only P3a, led by Astra Medium.
P3/G2 acceptance still requires P3b's default-caller integration and freshness handling.
It did not install or activate a runtime, replace an existing command, or clear an external live/recovery
blocker. External live/recovery blockers above remain in force.
