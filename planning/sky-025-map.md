---
summary: "SKY-025 subsystem dispositions, external callers, output contracts, and deployment blockers."
---

# SKY-025 · Repository disposition map

Owned by [the directive](projects/SKY-025-make-operational-outcomes-verifiable-and-prune-misleading-guidance.md).
Current accepted progress: **P6 / 6 of 24**. §5 releases **P7a Omada (Terra High)** as the current
executable packet; P7b certs/routes and P7c recon are same-phase continuations. P6c is a bounded
corrective slice after P6 acceptance (offline firewall inventory path retired — see below), not a
new numbered phase. Per-phase acceptance verdicts, reviewed SHAs and phase history live in the
directive §9 and git, not here.
This map describes planned replacements; it does not claim Python is installed or activated on any
lab host. Its grouped families cover the baseline's tracked paths (enumerated with `git ls-files`);
`scripts/` names are relative to that directory. **Verified** means source/caller inspection, not a
successful production operation. **Blocked** names a later phase's missing live evidence. No blanket
shell compatibility or duplicate production engine.

Enumeration counts: root files 10; `.claude` 1, `.codex` 4, `.githooks` 1, `.github` 2,
`.obsidian` 5; `bin` 6, `ca` 3, `compose` 40, `docs` 42, `hosts` 5, `inventory` 14,
`journal` 77, `nix` 14, `planning` 47, `runbooks` 24, `scripts` 50, `secrets` 16,
`templates` 7, `tests` 19, `tofu` 11. These are baseline counts, not a manifest to maintain.

## Dispositions by subsystem

| Surface | migrate/retain/delete | Replacement/owner | Callers | Phase | verified/blocked |
|---|---|---|---|---|---|
| `bin/ops`; `collect-all.sh` | migrate | Thin `skynet` dispatch and explicit workflow results | Humans, runbooks, nightly | 2–9, 20 | P4a routes core and network observations through the Nix package; paired refresh evidence guards default queries/audits/rendering. Remaining orchestration stays P20 |
| `collect-proxmox.sh`, `collect-proxmox-acl.sh` | migrate | Python read collectors; node-specific validation | collect-all, inventory gates/renderers | 3–4 | P4a leaves `collect-proxmox.sh` as a packaged-command forwarder and removes its shell API/parser. Both ACL readers remain P4b. Live behavior untested |
| `collect-pbs.sh`, `collect-docker.sh` | migrate | Python PBS/Docker collectors | collect-all, backup/container views | 5 | P5 accepted with reviewer repairs: single Docker writer, descendant cleanup, strict required fields, truthful verification, TLS and test isolation; live reads pass |
| `collect-dns.sh`, `collect-opnsense.sh` | migrate | Python DNS collection and live OPNsense firewall+state collection | collect-all, firewall/DNS views | 6 | P6a: `collect-dns.sh` → shim + `src/skynet/dns.py`. P6b-i: `collect-opnsense.sh` → shim + `src/skynet/opnsense.py` (live, paired firewall.json + opnsense.json, receipt-bound). No new OPNsense writer. P6 accepted with reviewer repairs and scoped live reads. **P6c retired the offline `config.xml` inventory path entirely** (`collect-firewall.sh`, `src/skynet/firewall.py`, `skynet collect firewall`, parser tests/fixtures deleted): live OPNsense API is the sole firewall inventory source; the `config.xml` git backup is DR-only (restored as config, never parsed into inventory). See disposition below |
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
checks are independently accepted; §5 of the directive records P3a and the same-phase P3b continuation.
P3/G2 acceptance still requires P3b's default-caller integration and freshness handling.
Independent review covers the full numbered phase after both slices; P3a has no separate review gate.
It did not install or activate a runtime, replace an existing command, or clear an external live/recovery
blocker. External live/recovery blockers above remain in force.

## Phase 3a implementation (complete; Phase 3 in progress)

`skynet collect proxmox core --output <file> [--credentials-file <file>] [--json]` is built
in `/tmp/skynet-sky-025-p3a`, from remote-main base
`f21442c44d34baf71e01ca8938ea1305c82242f6` (packet/review PR #214). It has no default
output destination and has not read production credentials or contacted a lab endpoint.
At P3a close-out the shell caller, `collect-all.sh`, `bin/ops`, timers and host profiles were unchanged.
P3b's integration is described below; P3/G2 acceptance covers both slices together.

| Consumer | Preserved snapshot contract / synthetic evidence |
|---|---|
| `check-invariants.sh` | Node-typed `nodes[].node`; pool IDs and stable member `id/type/vmid/node` (integer guest VMIDs). Null/unreadable members fail the refresh instead of becoming an empty pool. |
| `build-db.sh`, `sql/host-map.sql` | Original node/resource objects; guest `vmid/name/status/template/pool` types, optional template/pool defaults, and node identity continue to feed the existing guest table and host-map join. |
| `render-docs.sh` | Resource `vmid/name/type/status/pool`, pool IDs, nullable backup job fields, integer `enabled/all`, string VMID selection, and per-node integer-epoch/null `starttime` plus string/null `status`. Tests compare synthetic projections and exact stable members. |
| CLI / explicit file consumer | Success 0 with collection time/counts; unavailable 3; malformed/publication failure 1; usage 2. Failed refresh reports previous evidence and leaves the old bytes/timestamp intact. No freshness-blind consumer is routed to this collector. |

All collector tests exercise the actual CLI and collector with only HTTPS and local failure
boundaries substituted. Nix package checks run the suite against both source and installed
modules; outside-checkout console tests unset `PYTHONPATH` and use missing synthetic credentials.
No live response parity, real remote handshake, host activation or recovery drill is claimed.
The required hook passes with Ali's explicitly authorized 200,000-token current-authority
budget; the always-loaded budget remains 6,500. Full-phase acceptance covers P3a and P3b.

## Phase 3b implementation and full P3 review

**Current disposition, 2026-09-08: P3/G2 ACCEPT including the tested credential repair.**
The directive's newest §9 entry supersedes the earlier FIX/pending records below. Ali authorized
the reviewer to repair the simple shared-credential incompatibility and release P4 without another
review round. Accepted progress is 3/24; §5 releases P4a after human merge of this fix/packet PR.
The parser accepts optional `PVE_TOKEN_OPERATE` but observation requests still use only `PVE_TOKEN`.
P4 reuses that contract, migrates network observations then both ACL snapshots, and adds their
freshness evidence without treating other shell process exits as validated health.
Live/recovery blockers above remain in force.

**2026-09-08 combined review disposition: FIX / G2 open.** Both #215 and #216 are merged;
reviewed main is `8e6c8502ba7c9ce8e9d39fe9bd6d5fd5a45a36df`. Accepted progress remains
2/24. The directive's §5 contains the only actionable packet, repairing initial-marker failure
visibility to default consumers (R1) and subprocess-descendant cleanup before releasing the
collection lock (R2). Prior implementation evidence below is retained with these qualifications:
the reviewed revision's ordinary status accepted old success after initial marker failure, and
its timeout bounded the immediate process only. The repair implementation below awaits merged
full-phase review. No P4 or live transition is released.

Base `05b6326c46506b1c936fbaae724a083d8a218954` includes merged P3a PR #215. Ali explicitly
requested P3b and full-numbered-phase reviews. The workflow correction travels in this PR because
#215 merged before that correction was published. Accepted progress remains 2/24.

`bin/ops collect` → `collect-all.sh` → `bin/skynet` → `skynet collect all --repo` is the default
source path. The launcher uses offline Nix on tracked Git source, not ignored files or source-Python
fallback. No profile installation or NixOS activation is needed for this launcher. Actual offline
doctor and missing-evidence status invocations were checked locally without reading credentials.
`collect-proxmox.sh core` forwards to the isolated Python collector; its remaining shell code is
network-only, retained until P4. Other shell collectors remain owned by P4–7 and expose process
status, not the new core validation contract.

| Consumer | Core freshness behavior |
|---|---|
| `collect all` | Nonblocking local collection lock; unavailable marker before reads; success marker binds exact snapshot hash/time. Failed/incomplete marker never validates old evidence. |
| `bin/ops query`, `bin/ops entities` | Require matching successful core evidence within 36 hours before querying/auditing. Other input freshness is not established. |
| `render-docs.sh`, nightly | Refuse before publication if core evidence fails. Nightly requires an attempt from this pass, including when marker setup itself fails. Never reuse a prior SQLite cache after rebuild failure. |
| Direct invariant/entity/SQLite scripts | Historical-snapshot checks retained for deterministic CI; not a live-freshness gate. Tests still verify template identity and protected pool membership. |

The core files are not an atomic pair: record the attempt receipt, publish unavailable, then
snapshot, then success with its hash. A crash or final-marker failure leaves evidence unavailable;
mismatched receipts/hashes fail. If initial marker publication fails, no remote reads start and
the changed receipt prevents ordinary consumers from accepting the preceding success. Nightly
retains its additional attempt cutoff.
The isolated core command intentionally does not issue default refresh evidence.

No production collection, credentials, timer/service, host activation, state/payload or root action
was performed. The source path becomes effective when used from the merged checkout; the map's
workstation/recovery prerequisites remain unverified before that live transition. Offline package
availability is proven locally, not live API parity or independent recovery. P3/G2 review must
assess those explicit limits; P4 remains unauthorized until full-phase acceptance.

## Phase 3 fix implementation (awaiting full-phase review)

Base `89a1dee3f497df7c8609c8639298f4d3db66d505` contains merged review/repair packet #217
and accepted P2. Isolated worktree: `/tmp/skynet-sky-025-p3-fix`, branch `fix/sky-025-p3`.
The lock file holds a durable attempted timestamp; it is invalidated in place before a marker
replacement can fail. Ordinary status requires that receipt, matching marker/snapshot hashes
and times, and writable durable receipt storage. It cannot create successful refresh evidence.
The local receipt is intentionally not portable through Git: a fresh clone requires a full
collection before default consumers can claim current observations.

Remaining readers use isolated Linux process groups and temporary subreaper ownership. Timeout,
interruption and early leader exit all clean up/reap group descendants before continuing.
Unconfirmed cleanup records `recovery-required`, stops the pass and refuses another collection
until operator process recovery. No generic subprocess framework or new dependency was added.
Storage failure that prevents any durable record remains explicitly indeterminate; consumers
probe receipt durability and refuse while it cannot be established.

Ali additionally requested an end-of-work review and next-phase packet. The directive contains
a draft P4a network-observation packet plus bounded P4b ACL ownership; it is not released and
does not implement either slice. Full P3/G2 acceptance still covers #215, #216 and this fix after
merge. Accepted progress remains 2/24. All existing live/recovery blockers remain unchanged.

## Phase 4a implementation (slice complete; P4 in progress)

From remote-main base `d2bbedc649e2b4226a2f1b1721a35febbb6148cd`, P4a adds
`skynet collect proxmox network --output <file> [--credentials-file <file>] [--json]` with the
network default credential path and the established literal-assignment/read-token/TLS contract.
The synthetic network fixture has a distinct node shape, protected guests 5001/635/837, and an
observed empty pool list. The operate token remains optional, redacted, and unused for observations.

`collect all` now records one durable attempt receipt and runs core then network once before the
remaining shell readers. It publishes separate `collection-core.json` and
`collection-network.json` markers, each bound to that receipt and its own snapshot hash/time.
`collect-status`, query/entity and factual-render callers require both successful observations
within 36 hours and honor the nightly same-pass cutoff. A failed network read or final marker
publication retains its snapshot but makes default consumers unavailable; subsequent scoped readers
continue. `collect-proxmox.sh` is only the retained operator/runbook forwarding entry. ACL readers,
operate-token ACL introspection, and their freshness markers remain P4b.

Construction used fake HTTPS, synthetic credentials and disposable paths after the default-path
test was repaired: its initial form unexpectedly selected installed credentials and performed a
T1 observation during validation; the incident is recorded in the raw journal. No T2/T2+/T3
action, host/profile, timer, service, root, pool or ACL action occurred. The map's workstation,
state and payload recovery blockers remain unchanged. Source rollback is `git revert`.

## Phase 4b implementation (slice complete; P4 review pending)

P4b replaces `collect-proxmox-acl.sh` parsing and curl with Python operate-token self-observations.
`collect all` records core/network ACL snapshots and markers under the same receipt as node
observations; default consumers require all four. No ACL privilege, pool or live boundary changed.
The retained ACL script forwards only. After this PR's human merge, review P4a and P4b together.

## Phase 4 independent acceptance

Both #220 and #221 are merged and accepted together; the directive records exact merge SHAs,
exit verdicts and the review journal. Independent checks passed: 105 maintained Python cases,
32 disposable failure probes, source/installed package checks, lint/types and the staged hook.
The two shell entries remain only for documented operator callers, with P22 owning removal.

Ali additionally authorized live reads during this review. All four packaged collectors succeeded
with configured credentials/TLS into `/tmp/skynet-p4-live-read.W4brpC`: core 8 guests/1 pool,
network 6 guests/1 pool, ACL path counts 18 and 2. Protected guests 2020/5001/635/837 are unpooled;
ACL projections against the existing forbidden-privilege/root-allocation policy pass. This verifies
these four endpoint shapes and TLS paths, not other APIs or restore/service health. No repository
inventory refresh, host activation, timer/service change, grant or production write occurred.
Independent workstation access, state/payload recovery and other live-transition prerequisites
remain open.

## Phase 5 review — ACCEPT with reviewer repairs

Both #223 and #224 are merged; the directive's newest §9 entry owns the complete review and
the repaired acceptance result. The reviewer fixed the five synthetic counterexamples, TLS
fallback and test isolation, plus live-discovered PBS root namespaces and nullable Docker
Platform fields. Configured live reads succeed: PBS 152 snapshots/18 groups; Docker 18
containers/31 images. Prior blanket no-live-context test claims below remain unsupported;
the journal distinguishes the initial unguarded test run from explicitly authorized live reads.
Acceptance and P6a take effect at human merge of this combined PR. No restore/recovery
readiness or broader live-transition prerequisite is claimed cleared.

## Phase 5b implementation (historical slice completion)

From remote-main base `c0e0f53007dee3d49779c4f7fca065fbac13dbd2`, P5b replaces the Docker
shell parser/client with `skynet collect docker`. It preserves host labels and contexts, uses
bounded read-only argument arrays, validates JSON lines for container/image fields used by SQLite,
and retains prior bytes for missing context, command failure, or malformed output. Default collection
records a Docker marker under the shared receipt and status/render/query/entity callers require it.
The shell entry forwards only. Synthetic subprocess tests cover valid and failed output; no Docker
context or production host was contacted. Source rollback is `git revert`; P5 is ready for one
fresh Astra Medium review after this PR is human-merged.

## Phase 5a implementation (slice complete; P5 in progress)

From remote-main base `faf961ab3accb9466385da32efa9bb6185c77f3b`, P5a adds the explicit
`skynet collect pbs --output <file> [--credentials-file <file>] [--json]` command. Literal
credential parsing preserves PBS's token separator normalization, configured CA or fingerprint
pinning, a distinct connection address/SNI, GET-only requests, redacted errors, and atomic
publication. It validates every datastore's status, namespace and snapshot response before it
projects the existing group/count/latest-verification schema. Valid empty snapshots stay distinct
from missing, null, partial, malformed, timed-out or trust-failed observations; a failed refresh
retains its prior bytes.

`collect all` now publishes a PBS marker using the same receipt/hash/time contract as the four
Proxmox observations; status, query/entity, factual rendering and nightly require it. PBS failure
continues later scoped readers but refuses default freshness. The retained shell entry is a
documented forwarding shim; P22 owns its removal. Renderer input with incomplete PBS state is a
warning rather than a zero-snapshot/verified claim. Tests and package inputs moved the useful shell
coverage into Python and removed the superseded shell test from hook/CI. Construction uses fake
HTTPS, synthetic credentials and disposable paths only; no live PBS/Docker endpoint, credential,
trust setting, backup, restore, host, timer, service, grant or production write occurred. Source
rollback is `git revert`; endpoint parity and workstation/state/payload recovery remain unverified.

## Phase 6 independent acceptance

P6 ACCEPT including reviewer repairs, effective on Ali's merge of the combined review PR.
Reviewed main `9858daf0b4405b14aa93f45f50d71349ea29b1b6` includes merged #226, #227 and #228;
the directive's newest §9 entry owns merge identities and the criterion-by-criterion verdict.
DNS root-query and record validation, OPNsense credential compatibility, response completeness,
certificate-name precedence and probe-error reporting are repaired. Packaged live DNS returned
4 zones/13,355 records; live OPNsense returned 40 aliases/28 rules/41 ARP rows/17 interfaces.
The local offline mirror returned 41 aliases/29 rules/5 reservations and remains historical;
source path provenance is preserved but no mirror revision/hash is claimed. No production
inventory was overwritten. Full source/installed checks passed, with 225 source tests.
The raw review journal preserves failures, worker integration and limitations.

P6 shell entry points remain forwarding shims owned by P22. P7a Omada is the sole released
packet; the lead details P7b certs/routes and P7c recon after their preceding slice merges.
Workstation/state/payload recovery and live installation blockers remain unchanged.
The historical implementation entries below do not supersede this acceptance.

## Phase 6a implementation (slice complete; P6 in progress)

From remote-main base `db09021802f590d79f2ab9f7c2c56064f29c0a4a`, P6a adds
`skynet collect dns --output <file> [--credentials-file <file>] [--json]` in `src/skynet/dns.py`,
replacing the `collect-dns.sh` curl/jq/eval reader. Literal `TECH_HOST/TECH_TOKEN/TECH_CACERT`
parsing, CA-file hostname-verified HTTPS on port 53443, a 15s timeout, and a token carried only in
the request query with fixed redacted diagnostics. Only `zones/list` and `zones/records/get` are
allowed. The snapshot preserves collection time, host, every zone object, and per-zone
`{zone, records}` with record `name/type/rData` (all record types) consumed by SQLite
(`build-db.sh`) and the A/CNAME service renderer (`render-docs.sh`); a top-level `host` field feeds
the freshness node/host check. A non-`ok` API status, null/missing zone or record list, duplicate
zone identity, malformed required record field, timeout or trust failure is unavailable/failed and
retains prior bytes; a validated empty record list is a real observation.

`collect all` drops DNS from the shell `REMAINING`, runs it once under the shared attempt receipt,
publishes a receipt/hash/time `inventory/collection-dns.json` marker, and `collect-status`,
query/entity, factual rendering and the nightly cutoff now require it. DNS failure continues later
scoped readers but refuses default freshness. `collect-dns.sh` is a forwarding shim; P22 owns
removal. `test_dns.py` + `tests/fixtures/dns/` and the shim join the Nix source filter, installed
check and staged-hook glob.

| Consumer | Preserved snapshot contract / synthetic evidence |
|---|---|
| `build-db.sh`, `render-docs.sh` | `.records[].records[]` A/CNAME rows keep `name`, `type`, `rData.ipAddress`/`rData.cname`; non-A/CNAME types (SOA/NS/TXT/…) are preserved verbatim, not dropped. |
| `collect all` / `collect-status` | DNS marker binds the shared receipt and `dns-zones.json` hash/time; default consumers require all six migrated markers within 36 hours plus the nightly same-pass cutoff. Failed DNS retains bytes, refuses freshness, and lets remaining scoped readers continue. |
| CLI / explicit file consumer | Success 0 with collection time/zone+record counts; unavailable 3; malformed/publication failure 1; usage 2. A failed refresh reports previous evidence and leaves old bytes intact. |

Construction used fake HTTPS, synthetic credentials and disposable outputs only; no live
DNS/OPNsense read, mirror credential/config content, zone modification, Technitium server setting,
timer/service, root, grant or production write occurred. Source rollback is `git revert`; endpoint
parity and workstation/state/payload recovery remain unverified. **Unverified live boundary:** the
committed `dns-zones.json` shows the root `""` Secondary zone returning `records: null`, which the
stricter contract fails; whether that needs a zone-type exclusion or query adjustment is a
P6b/live-transition question, not resolved here. P6 has since been accepted (directive §9); the
interim offline `config.xml` mirror parser was retired in P6c, leaving the live OPNsense API as the
sole firewall inventory source.

## Phase 6b-i implementation (slice complete; P6 in progress)

From origin/main base `b7e6f6e8e1dd69f8bbe0f54d91738f9bced4a1b8` (includes P6a), P6b-i adds the
live OPNsense collector `src/skynet/opnsense.py`, replacing `collect-opnsense.sh`. P6 was split
further: **P6b-i = live collector** (this slice); **P6b-ii = offline config.xml mirror parser**
(`collect-firewall.sh` → `src/skynet/firewall.py`), matching the two shell scripts. One
`skynet collect opnsense --firewall-output <f> --state-output <f> [--credentials-file <f>] [--json]`
run produces both paired snapshots. TLS reuses the PBS SNI-pinned transport
(`pbs.HTTPSConnection` + `pbs._sni_from_certificate`): connect to `OPN_HOST`, present the
certificate-derived SNI, verify against the pinned cert as CA. Basic auth key/secret stay in the
header; fixed redacted diagnostics. Only the enumerated GETs (`core/firmware/status`,
`firewall/alias/get`, `firewall/filter/get`, `interfaces/overview/interfacesInfo`) and read-only
search POSTs (`firewall/filter/searchRule`, `dnsmasq/settings/searchHost`,
`diagnostics/interface/searchArp`) are called; a search page whose `total` exceeds its rows fails.

| Consumer | Preserved snapshot contract / synthetic evidence |
|---|---|
| `build-db.sh`, `render-docs.sh`, `audit-entities.sh` (firewall.json) | `.aliases[]` keep `name/type/content/description/enabled` (built-ins dropped, form fields resolved); `.rules[]` keep `sequence/action/protocol/interface/source_net/destination_net/destination_port/description/uuid/enabled` (configured user rules only); `.reservations[]` keep `host/domain/ip/hwaddr/…`. Added top-level `host` for the freshness check. |
| `build-db.sh`, `render-docs.sh`, `audit-entities.sh` (opnsense.json) | `.firmware{status,product,needs_upgrade}`, `.counts{arp,interfaces,live,silent}`, `.arp[]` (`ip/mac/hostname/intf/intf_description/manufacturer/permanent/expired/expires`), `.interfaces[]` (`device/description/status/enabled/identifier`), `.presence[]` (`ip/live/via`). |
| `collect all` / `collect-status` | Two markers (`collection-firewall.json`, `collection-opnsense.json`) bind the shared receipt and each file's hash/time; both required within 36h + nightly cutoff. A failed OPNsense read retains both files, refuses freshness, and lets remaining scoped readers continue. |
| CLI / explicit consumer | Success 0; unavailable 3; malformed/publication failure 1; usage 2. A failed read leaves both destinations untouched. |

Construction used fake HTTPS, synthetic credentials and disposable outputs only; no live OPNsense
read, config write, credential change, timer/service, root, grant or production write occurred.
Source rollback is `git revert`; live endpoint parity, the ops→NET_SKYNET ICMP-vantage floating
rule, and workstation/state/payload recovery remain unverified. A third slice, P6b-ii, later added
an offline `config.xml` mirror parser (`src/skynet/firewall.py`); it was retired entirely in P6c
(below), so the live OPNsense collector here is the sole firewall inventory source. P6 was reviewed
and accepted as a whole (directive §9).

## Phase 6c disposition (bounded corrective slice after P6 acceptance)

Authorized by GitHub issue #230 as a bounded cleanup after the P6 combined review/repair ACCEPT
(#229). P6b-ii's offline `config.xml` inventory parser created a second producer for the same
firewall-inventory shape — deliberately never live-fresh, but a source of operator/agent ambiguity
about whether firewall state came from the live OPNsense API or a stale git mirror. The capability
was not worth the ambiguity, so P6c removes the offline inventory path entirely.

Removed: `src/skynet/firewall.py`, `scripts/collect-firewall.sh`, the `skynet collect firewall`
CLI wiring, `tests/test_firewall.py`, `tests/fixtures/firewall/`, and the Nix source-filter /
installed-package / pre-commit-hook references that existed only for this parser/shim. The one
`test_collection.py` case that used the offline parser to write stale bytes now does a direct
out-of-band overwrite of `firewall.json`, preserving its receipt-hash-mismatch freshness coverage
without the parser. Docs/design/ADR references that presented offline `config.xml` parsing as an
inventory source (nix/README, observability, ADR 0006 consequence, SKY-020 references) were updated.

Disposition: **the live OPNsense API (`src/skynet/opnsense.py`) is the sole producer of firewall
inventory** (`inventory/firewall/firewall.json` + `inventory/opnsense.json`); its freshness/receipt
semantics are unchanged and this removal does not regress P6's live-collector acceptance. The
`skynet-opnsense` `config.xml` git backup is retained **only** as disaster-recovery material —
in recovery it is restored as configuration into OPNsense (see `docs/design/disaster-recovery.md`
and `runbooks/dr/DR-network-node.md`), never interpreted as current inventory. No replacement
offline collector was added; live OPNsense API behavior and firewall write policy are unchanged;
P17 recovery is not redesigned here. Accepted progress remains **6/24**; P6c is a corrective slice,
not a new numbered phase.
