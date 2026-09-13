# Project Core Technologies

## Authority boundary

This file is compact derived memory of the current repository stack. `pyproject.toml`, `flake.nix`,
Nix modules, Compose/OpenTofu files, design spokes, and runtime evidence are authoritative when they
differ. It records foundations and constraints, not a dependency inventory or a production grant.

## Languages and runtimes

- Python 3.12+ powers the installable `skynet` package and its `skynet` CLI.
- Bash remains the installed implementation for operator entry points, collectors, deploy/backup
  procedures, and compatibility callers that still have a concrete owner.
- Nix/NixOS declares the ops VM and LXC systems; HCL/OpenTofu declares scoped infrastructure state.
- YAML/TOML/JSON, Compose manifests, Caddy configuration, Markdown, and sops-encrypted environment
  files carry declarative configuration, metadata, policy, and documentation.

## Frameworks and libraries

The Python engine is stdlib-first and has no runtime dependencies in `pyproject.toml`. It contains
the CLI, collection orchestration, Proxmox/PBS/DNS/Docker/OPNsense/Omada readers, certificate probes,
reconnaissance, doctor reporting, static route parsing, packaged entity derivation/audit, deployment
verification, and the
disposable SQLite cache/query projection. `render.py` owns freshness-gated factual pages;
`memory.py` renders the digest, context map, and runbook catalog and provides read-time recall with
case-insensitive GNU grep ERE semantics. The Nix package closure supplies GNU grep. Entity functions
cover guest, service, node, vhost, and network identities; route resolution calls them directly. Nix
packages the application and its development shell; `deploy-rs`, sops-nix, and disko integrate with
NixOS.

## Build and development tools

- GitHub CI and automated repository tests are embargoed for the duration of SKY-025. The test tree,
  package test phase, and workflow definitions are absent until a post-transition review designs one
  coherent replacement suite.
- Ruff and strict mypy remain available as manual development tools. Deploy-rs schema validation
  remains a local flake output; pre-commit retains only secret scanning and hard-invariant checks.
- `bin/plan`, `bin/new`, and `bin/ops` are operator-facing entry points. `bin/ops entities|query`
  use the packaged audit and query paths after the collection-freshness gate. `bin/recall` and the
  `scripts/render-*.sh` commands are compatibility forwarders to the Python package. Renderers own
  `inventory/` and `docs/generated/`; nightly factual rendering invokes `bin/skynet` directly.

## External services and infrastructure

The runtime observes or operates declared boundaries for both Proxmox nodes, PBS, Docker hosts via
Arcane and unprivileged SSH, Technitium zones, scoped Authentik applications/providers, Cloudflare
DNS records for `aliammar.net`, OPNsense read-only diagnostics, and Omada inventory. GitHub provides
the review/merge boundary; Arcane provides GitOps reconciliation; Caddy and Cloudflare Tunnel provide
the internal/public service path.

## Important technical constraints

- TLS readers verify pinned/private CAs; collectors fail closed on unavailable, malformed, partial,
  or stale evidence and publish atomically. No reader disables TLS verification for an authenticated
  API call.
- Plaintext secrets never enter Git, logs, transcripts, or chat. sops/age and restrictive materialized
  files under `/opt/skynet-ops/secrets/` are the supported forms.
- Production OpenTofu uses a single-scope saved plan and the wrapper; bare re-planning apply,
  delete/replace, and unauthorized targets are refused. OPNsense's approved T2 config path is not
  yet implemented; self-leash changes remain T3 and human-merged.
- The entity audit reads authored conventions plus committed inventory and has no network or mutation
  path. The cache is a disposable 14-table `.cache/inventory.db` projection: it builds in a temporary
  file, validates schema/integrity, and atomically replaces the target only on success. A failed build
  retains the previous bytes, but freshness-gated callers do not treat retained observations as current.
- The factual renderer checks collection freshness, rejects unsafe node page basenames, and publishes
  a staged whole-tree replacement with rollback to the prior page set on failure.
- Deployment verification requires one exact full Git revision across Arcane Git Sync and project
  evidence, complete equal positive project/Docker counts, running healthy containers, and complete
  canonical routes probed from the Docker DMZ network with verified TLS. It has no deploy or rollback
  write path; the route probe only creates/removes an ephemeral pinned image container.
- `gitops-deploy.sh` and `gitops-rollback.sh` retain deployment/recovery orchestration. With
  `--gate`, the deploy script resolves the selected local `GITOPS_BRANCH` head and the thin
  `deploy-gate.sh` forwards that exact revision to the packaged verifier; rollback takes a separate
  authored deploy-commit identity.
- `scripts/entity.sh`, `scripts/audit-entities.sh`, and `scripts/build-db.sh` are compatibility
  forwarders; maintained SQL views remain under `scripts/sql/`.
- Generated inventory and documentation are machine-owned. Construction runs as the unprivileged
  `aliammar` Unix account and ordinary native construction inherits the no-prompt posture within
  that filesystem/OS boundary. Roles, models, and language grant zero production authority; self-root
  and self-merge remain forbidden.
