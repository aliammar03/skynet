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
- `scripts/` holds retained procedures, collectors, and compatibility forwarders; `bin/` holds
  operator entry points; `runbooks/` holds engine-neutral procedures and their generated catalog.
- `planning/` holds SKY directives through their lifecycle; `journal/` holds append-only raw episodes;
  `agent_docs/` holds compact derived agent memory.
- `inventory/` and `docs/generated/` are machine-owned outputs and must be changed through their
  collectors/renderers. No test tree or GitHub workflow is present during the SKY-025 embargo.

## Modules and responsibilities

The Python CLI dispatches collection, doctor, route, reconnaissance, entity-audit, cache/query,
rendering, and recall commands. `entities.py` owns the five-class identity derivation/audit and
`routes.py` uses it directly; `cache.py` owns the disposable 14-table SQLite projection and queries;
`render.py` owns factual Markdown pages; `memory.py` owns digest/context/catalog rendering and
read-time recall. Collector modules own one observation boundary and its validation/publication
contract; `collection.py` coordinates the default evidence set. Bash retains deployment, backup,
invariant, and host procedures. Entity/audit/cache/render/recall shell names are compatibility
forwarders, including the nightly call into the packaged factual renderer. Nix owns system/runtime
composition, OpenTofu owns declared infrastructure state, Compose owns service definitions, and
runbooks explain task-shaped execution. Raw journal creation through `bin/new` and the nightly journal
writer remain Bash-owned P21 work; P9 packages only rendering and read-time retrieval.

## Main interfaces and integration boundaries

- `skynet` CLI / `src/skynet/cli.py` is the local engine interface; collectors write explicit snapshots
  under `inventory/`, `entities` audits committed identity mappings, and `query` rebuilds/queries the
  disposable cache. `bin/ops entities|query` first requires current collection evidence; direct
  repository scripts do not establish freshness.
  Collectors never claim service health merely from collection success.
- Git branch → PR → human merge → Arcane Git Sync → running Compose is the service boundary; `git
  revert` is the normal rollback path.
- Approved OpenTofu source → one-scope saved plan → `scripts/tofu-apply.sh` is the infrastructure
  write boundary. Proxmox, DNS, Cloudflare, and host access remain tier-scoped.
- `docs/system-design.md` is the authority spine. `agent_docs/` distills it and current evidence for
  cold Main intake; it cannot override constitution, runtime, current docs, directives, or evidence.

## Supporting assets and temporary verification boundary

GitHub CI and automated repository tests are absent for the duration of SKY-025. A post-transition
review owns the replacement test architecture. `templates/` is the source for generated artifact
scaffolding. `ca/`, `.sops.yaml`, `.githooks/`, and `invariants.json` support trust, encryption, the
retained local secret scan, and machine-enforced hard laws.
