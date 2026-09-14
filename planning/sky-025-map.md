---
summary: "SKY-025 current subsystem dispositions, callers, replacement phases, and live/recovery blockers."
---

# SKY-025 · Repository disposition map

Owned by [the active directive](projects/SKY-025-make-operational-outcomes-verifiable-and-prune-misleading-guidance.md).

Current accepted progress is **P10 / 10 of 24** and architecture checkpoint G3 is complete. P11
implementation is ready on PR **#259** and pending fresh external review; accepted
progress does not advance before same-PR accepted closeout.
Every PR, including generated-only nightly work, is human-merged during the SKY-025 test/CI embargo.

The reviewer resolves/rechecks Git revisions from GitHub. Ali supplies the phase/PR identity, not hashes.
For normal open PRs, ACCEPT is recorded in a machine-readable PR marker; Ali later says only `accepted`
to the original session, which validates the marker and closes out that same PR before one human merge.

This file is a current disposition/caller/blocker map. Implementation chronology belongs in Git and
`journal/`; per-phase progress belongs in the directive.

## Current disposition by subsystem

| Surface | Disposition | Python/current owner | Important callers | Phase / condition |
|---|---|---|---|---|
| `bin/ops`, `scripts/collect-all.sh` | migrate | thin `skynet` dispatch + bounded orchestration | humans, nightly, runbooks | P2–P9/P20 |
| Proxmox node + ACL shell collectors | migrate | Python Proxmox collectors | default collection, inventory gates/renderers | P3–P4 accepted; shell forwarding cleanup P22 |
| PBS + Docker shell collectors | migrate | Python PBS/Docker collectors | backup/container views | P5 accepted; shell forwarding cleanup P22 |
| DNS + OPNsense shell collectors | migrate | Python DNS + live OPNsense collectors | DNS/firewall/state views | P6 accepted; shell forwarding cleanup P22 |
| offline OPNsense `config.xml` inventory parser | **deleted** | none | none | retired P6c; config.xml is DR restore material only |
| Omada/cert/routes/recon shell implementations | migrate | Python observation modules | default collection/status/render/recon | P7 accepted |
| `scripts/entity.sh` | forwarding compatibility only | `src/skynet/entities.py` | installed/manual callers | P8 implemented; removal P22 |
| `scripts/audit-entities.sh` | forwarding compatibility only | Python entity audit | invariant gate | P8 implemented; removal P22 |
| `scripts/build-db.sh` | forwarding compatibility only | `src/skynet/cache.py` | renderer compatibility | P8 implemented; removal P22 |
| `scripts/sql/host-map.sql`, `scripts/sql/vhosts.sql` | retain | SQL query definitions over disposable cache | renderer/query | P8 implemented |
| rendering/digest/context/catalog shell tools | forwarding compatibility only | Python render/retrieval paths | nightly, humans, agent context | P9 accepted; removal P22 |
| `bin/recall` | forwarding compatibility only | packaged read-time recall | humans, agent context | P9 accepted; removal P22 |
| `deploy-gate.sh`, GitOps deploy/rollback shell logic | forwarding compatibility only | packaged deployment verifier plus `skynet deploy service` / `skynet rollback service` | deployment/restore runbooks | P10 accepted; P11 implementation ready; shell removal P22 |
| publishing/DNS coordination shell logic | migrate | Python bounded publishing workflows | Caddy/Auth/DNS runbooks | P12 |
| Tofu env/apply + snapshot execution shell logic | migrate | Python saved-plan/policy/execution | provisioning/publishing | P13–P14 |
| restic provision/backup shell logic | migrate | Python host-local backup/provisioning | host-local units | P15/P19 |
| PBS off-site transfer shell logic | migrate | Python guarded transfer | PBS host-local unit | P16 |
| recovery/restore procedures | retain/adapt | Python helpers only where procedural value exists | DR runbooks | P17 |
| pin/onboard/access helper shell logic | migrate where useful | Python validation/onboarding | human onboarding/grant workflows | P18 |
| bootstrap workstation/Proxmox | retain if rescue-only | human bootstrap/rescue | external recovery | P18/P22/P24 decision |
| nightly shell orchestration | migrate | one Python nightly sequence | ops timer | P20 |
| CLI updater competing with Nix | delete | Nix package/config ownership | weekly update timer | P20–P22 |
| invariant/hygiene shell gates | retain only hard safety controls | post-transition redesign | local hook | P21/P24 handoff |
| `bin/new`, `bin/plan` | migrate executables; retain templates | Python planning/scaffolding helpers | operators | P21 |
| `.codex/**`, `agent_docs/**` | retain | native SKY-026 construction/continuity | construction sessions | already migrated; no SKY-022 compatibility |
| `.github/workflows/*`, automated tests | delete during embargo | post-transition redesign | none during SKY-025 | post-SKY-025 |
| `.githooks/pre-commit` | retain/adapt | secret scan + hard invariants only | local hook | P21 |
| Nix/hosts/flake | retain/adapt | Nix | package/install/timers | throughout; P23 install |
| OpenTofu declarations/state config | retain | OpenTofu | saved-plan executor | P13–P14/P18 |
| Compose/Caddy/service payload | retain | Compose/Caddy | Arcane/GitOps | P11–P12/P22 |
| `inventory/**`, `docs/generated/**` | retain contracts; machine-regenerate | owning collectors/renderers | status/cache/render/context | never hand-edit |
| current docs/runbooks | retain/adapt/prune | one current authority per rule | humans/agents | throughout; P22/P24 cleanup |
| decisions/history/journal/archive | retain as history | Git/journal | retrieval only | never current runtime authority |
| encrypted secrets/public CA material | retain | existing sops/custody | runtime/recovery | no custody widening |

No executable is retained merely to preserve an old command name. A temporary shim needs a real current
caller, one owner, and a removal phase. When the owning Python replacement is accepted, migrate known
callers together and delete duplicate procedural logic.

## P8 caller map

P8 is accepted and human-merged on PR **#255**.

### P8A · entity derivation/audit

Current owners/callers to inspect together:

- `scripts/entity.sh`
- `scripts/audit-entities.sh`
- `src/skynet/routes.py` entity resolution
- `bin/ops entities`
- entity-related renderer/cache/query callers
- `docs/conventions/naming.md`, `invariants.json`, `lab.json`

Preserve stable entity IDs, VMID/IP ambiguity handling, exceptions/templates, running-unmapped failure,
and the distinction between identity facts and OPNsense liveness annotations.

### P8B · disposable SQLite cache/query

Current owners/callers to inspect together:

- `scripts/build-db.sh`
- `scripts/sql/host-map.sql`
- `scripts/sql/vhosts.sql`
- `bin/ops query`
- `scripts/render-docs.sh`
- current collection/query caller contracts
- `nix/modules/base.nix` SQLite package/comment ownership

`.cache/inventory.db` remains disposable and rebuilt from repository/inventory truth. No ORM, DB service,
migrations framework, or second authority tree.

## P9 caller map

P9 is accepted on PR **#256**; its bounded closeout stays on that open numbered-phase PR until Ali
human-merges it once.

Current owners/callers to migrate together:

- `scripts/render-docs.sh` → packaged factual renderer; `scripts/nightly.sh` calls the package;
- `scripts/render-digest.sh` and `scripts/render-context-map.sh` → packaged content-stable renderers;
- `scripts/render-runbook-catalog.sh` → packaged frontmatter catalog renderer;
- `bin/recall` → packaged read-time retrieval;
- current observability/memory/docs conventions and the Nix package description.

The raw journal and nightly journal append remain authored evidence. General `bin/new` scaffolding stays
with P21. Thin forwarding entries remain only for compatibility until P22.

## External installs and live/recovery blockers

These are blockers for later live phases, not reasons to keep shell implementations indefinitely.

| Surface | Required evidence before affected live work |
|---|---|
| Ops VM checkout/install | identify active checkout/package/service/timer path before P23 activation |
| host-local restic/PBS transfer scripts/units | inventory installed versions, enabled instances, paths, and required packages before P15/P16/P19 |
| Arcane Git Sync / Docker mounts | identify actual sync command/revision/materialized env/mounts before P11 |
| workstation grant helper + CA custody | verify independent workstation access/rebuild path before first destructive/recovery-dependent phase |
| `/opt/skynet-ops` persistent cert/mirror/state paths | preserve required state and prove recovery before P17/P23/P24 |
| sops/age materialization | preserve current custody/materialization; never read private secret contents for planning |
| ignored local state (`.cache`, Tofu state/provider cache, local settings) | classify recovery-critical vs rebuildable before any cleanup |
| survival kit / DR path | prove one independent rebuild/access procedure before recovery acceptance |

Source references: [`../runbooks/dr/survival-kit.md`](../runbooks/dr/survival-kit.md),
[`../runbooks/dr/DR-core-node.md`](../runbooks/dr/DR-core-node.md), and
[`../runbooks/dr/DR-network-node.md`](../runbooks/dr/DR-network-node.md).

## Adjacent directive ownership

| Directive | Boundary with SKY-025 |
|---|---|
| SKY-005 | SKY-025 replaces recon implementation; diagnosis practice/lab work remains SKY-005 |
| SKY-006 | SKY-025 P9 replaces implemented digest/recall substrate; future semantic retrieval remains SKY-006 |
| SKY-012 | capability contracts carry forward; new runbook features remain SKY-012 |
| SKY-015 | entity/rendering replacements live in P8–P9; no duplicate renderer project |
| SKY-016 | P10–P12 replace existing verification/deployment substrate; extra deployment features remain SKY-016 |
| SKY-017 | autonomy promotion remains evidence-earned there; Python replacement grants no new authority |
| SKY-018 | eight-layer semantics remain there; P8/P10–P14/P20–P21 replace existing substrate only |
| SKY-020 | future OPNsense write/provider work remains there; SKY-025 P6 is reads only |
| SKY-023 | non-engine documentation-hygiene residue remains there; P21–P22 own engine-related cleanup |
| SKY-024 | guest declaration/fleet adoption remains there; P13–P14/P18 preserve its safety boundaries |

## Output and cache rules carried forward

- Existing inventory filenames/fields remain compatible until a consumer migrates in the same phase.
- Collection success must be validated and freshness-bound; old bytes cannot masquerade as fresh data.
- Optional JSON outcomes distinguish success/failure/unavailable/skipped/recovery-required where the
  command family needs those states.
- SQLite and generated Markdown are rebuildable views, not authority.
- Generated outputs are changed only by their owning generator.
- Current operational docs contain current rules. Historical rationale stays in Git/journal/decisions.
