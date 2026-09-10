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
reconnaissance, doctor reporting, and static route parsing. Nix packages the application and its
development shell; `deploy-rs`, sops-nix, and disko integrate with NixOS.

## Build, test, and development tools

- `pytest` runs the behavioral Python suite; shell contracts live in `tests/*-test.sh`.
- Ruff enforces Python style and mypy runs in strict mode over `src/skynet`.
- Nix flake checks package, CLI, deployment schema, and tests; pre-commit and repository gates check
  documentation, invariants, secrets, generated surfaces, and operational contracts.
- `bin/plan`, `bin/new`, `bin/ops`, and `bin/recall` are operator-facing entry points. Renderers own
  `inventory/` and `docs/generated/`.

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
- Generated inventory and documentation are machine-owned. Authored changes use a PR and normal
  human merge; construction role, model, language, and workspace sandbox do not confer production
  authority.
