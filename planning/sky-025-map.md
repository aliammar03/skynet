---
summary: "SKY-025 current subsystem dispositions, callers, replacement phases, and live/recovery blockers."
---

# SKY-025 · Repository disposition map

Owned by [the active directive](projects/SKY-025-make-operational-outcomes-verifiable-and-prune-misleading-guidance.md).

Current accepted progress is **P6 / 6 of 24**. P7 implementation/corrective work is already merged in
**#235, #236, #237 and #239**, but P7 is not yet accepted. **No implementation packet is currently
released.** The **single current next action** is the one-time fresh read-only review of the
**already-integrated P7 result** on current `main`. ACCEPT closes P7 and releases the prepared P8
packet. FIX opens one bounded corrective P7 PR, which then uses the normal open-PR review lifecycle and
never returns to the legacy integrated-main review mode.

The reviewer resolves/rechecks Git revisions from GitHub. Ali supplies the phase/PR identity, not hashes.

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
| Omada/cert/routes/recon shell implementations | migrate | Python observation modules | default collection/status/render/recon | P7 implemented; acceptance pending |
| `scripts/entity.sh` | migrate/delete shell logic | prepared `src/skynet/entities.py` | audit, routes, cache/render/query consumers | P8A |
| `scripts/audit-entities.sh` | migrate/delete shell logic | Python entity audit | `bin/ops entities`, CI/current diagnostics | P8A |
| `scripts/build-db.sh` | migrate/delete shell logic | small Python rebuildable-cache module | `bin/ops query`, renderer | P8B |
| `scripts/sql/host-map.sql`, `scripts/sql/vhosts.sql` | retain if useful | SQL query definitions over disposable cache | renderer/query | P8B |
| rendering/digest/context/catalog shell tools | migrate/prune | Python render/retrieval paths | nightly, humans, agent context | P9 |
| `deploy-gate.sh`, GitOps deploy/rollback shell logic | migrate | Python verify/deploy/recovery evidence | deployment/restore runbooks | P10–P11 |
| publishing/DNS coordination shell logic | migrate | Python bounded publishing workflows | Caddy/Auth/DNS runbooks | P12 |
| Tofu env/apply + snapshot execution shell logic | migrate | Python saved-plan/policy/execution | provisioning/publishing | P13–P14 |
| restic provision/backup shell logic | migrate | Python host-local backup/provisioning | host-local units | P15/P19 |
| PBS off-site transfer shell logic | migrate | Python guarded transfer | PBS host-local unit | P16 |
| recovery/restore procedures | retain/adapt | Python helpers only where procedural value exists | DR runbooks | P17 |
| pin/onboard/access helper shell logic | migrate where useful | Python validation/onboarding | human onboarding/grant workflows | P18 |
| bootstrap workstation/Proxmox | retain if rescue-only | human bootstrap/rescue | external recovery | P18/P22/P24 decision |
| nightly shell orchestration | migrate | one Python nightly sequence | ops timer | P20 |
| CLI updater competing with Nix | delete | Nix package/config ownership | weekly update timer | P20–P22 |
| invariant/hygiene shell gates | migrate useful behavior | deterministic Python/current gates | hook, CI, nightly | P21 |
| `bin/new`, `bin/plan` | migrate executables; retain templates | Python planning/scaffolding helpers | operators | P21 |
| `.codex/**`, `agent_docs/**` | retain | native SKY-026 construction/continuity | construction sessions | already migrated; no SKY-022 compatibility |
| `.github/workflows/*`, `.githooks/pre-commit` | retain/adapt | unified deterministic gates | GitHub/local hook | P21 |
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

P8 is prepared but remains blocked until the one-time P7 review returns ACCEPT and closeout records P7.
From P8 onward, internal slices stay on one open numbered-phase PR and are not merged separately.

### P8A · entity derivation/audit

Current owners/callers to inspect together:

- `scripts/entity.sh`
- `scripts/audit-entities.sh`
- `tests/entity-test.sh`
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
- relevant collection/query tests
- `nix/modules/base.nix` SQLite package/comment ownership

`.cache/inventory.db` remains disposable and rebuilt from repository/inventory truth. No ORM, DB service,
migrations framework, or second authority tree.

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
