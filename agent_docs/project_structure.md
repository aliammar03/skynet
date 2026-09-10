# Project Structure

## Authority boundary

This is compact derived memory of stable repository layout and ownership. `docs/conventions/layout.md`,
the constitution, current directives, and the files themselves win if this map becomes stale. Generated
directories and live inventory are intentionally summarized rather than copied here.

## Directory layout

- `AGENTS.md`, `docs/system-design.md`, `docs/design/`, `docs/conventions/`, and `docs/decisions/`
  hold the operating contract, constitution, domain design, doctrine, and settled decisions.
- `src/skynet/` and `pyproject.toml` hold the installable Python engine; `nix/` and `hosts/` hold
  NixOS packaging, modules, and host definitions; `flake.nix` composes build/deploy outputs.
- `compose/<service>/` holds GitOps service manifests and encrypted environment inputs; `tofu/` holds
  declarative infrastructure sources; `secrets/` holds encrypted per-host material.
- `scripts/` holds procedures and collectors; `bin/` holds operator entry points; `runbooks/` holds
  engine-neutral operational procedures and their catalog.
- `planning/` holds SKY directives through their lifecycle; `journal/` holds append-only raw episodes;
  `agent_docs/` holds compact derived agent memory.
- `tests/` holds Python behavior and shell contract tests; `inventory/` and `docs/generated/` are
  machine-owned outputs and must be changed through their collectors/renderers.

## Modules and responsibilities

The Python CLI dispatches collection, doctor, route, and reconnaissance commands. Collector modules
own one observation boundary and its validation/publication contract; `collection.py` coordinates the
default evidence set. Bash scripts own deployment, backup, rendering, invariant, and host procedures.
Nix owns system/runtime composition, OpenTofu owns declared infrastructure state, Compose owns service
definitions, and runbooks explain task-shaped execution.

## Main interfaces and integration boundaries

- `skynet` CLI / `src/skynet/cli.py` is the local engine interface; collectors write explicit snapshots
  under `inventory/` and never claim service health merely from collection success.
- Git branch → PR → human merge → Arcane Git Sync → running Compose is the service boundary; `git
  revert` is the normal rollback path.
- Approved OpenTofu source → one-scope saved plan → `scripts/tofu-apply.sh` is the infrastructure
  write boundary. Proxmox, DNS, Cloudflare, and host access remain tier-scoped.
- `docs/system-design.md` is the authority spine. `agent_docs/` distills it and current evidence for
  cold Main intake; it cannot override constitution, runtime, current docs, directives, or evidence.

## Tests and supporting assets

Python tests mirror the engine modules (`tests/test_*.py`); shell tests cover construction, rendering,
GitOps rollback, DNS, provisioning, invariants, and repository hygiene. `tests/fixtures/` supplies
bounded API/recon data. `templates/` is the source for generated artifact scaffolding. `ca/`,
`.sops.yaml`, `.githooks/`, and `invariants.json` support trust, encryption, commit checks, and
machine-enforced hard laws.
