# Spoke · Repo layout & required files

> Where each kind of artifact lives, and the minimum files each must have to be well-formed.
> Governed by [`../conventions.md`](../conventions.md).

Tags: **[testable]** = a lint gate could assert it; **[manual]** = holds by review.

## The map

| Path | Holds | Authority |
|---|---|---|
| `AGENTS.md` / `CLAUDE.md` | The always-loaded cross-vendor contract (CLAUDE.md imports AGENTS.md) | contract |
| `docs/system-design.md` | The constitution — invariants, trust model, extension points | design |
| `docs/design/*.md` | Design spokes — depth per domain | design |
| `docs/conventions.md` + `docs/conventions/*.md` | The convention hub + spokes (this set) | doctrine |
| `docs/decisions/*.md` | ADRs — decisions with lasting consequence | history |
| `docs/generated/**`, `inventory/**` | **Machine-written** — never hand-edit | generated |
| `docs/history/*.md` | Build log + original plan (lineage) | history |
| `compose/<svc>/` | One dir per service (the GitOps loop) | ops |
| `scripts/*.sh` | Procedures runbooks/entry-points call | ops |
| `bin/*` | Operator-facing entry points (`plan`, `ops`, `grant-root`) | ops |
| `runbooks/*.md`, `runbooks/dr/*.md` | Engine-neutral procedures, catalogued in `runbooks/README.md` | ops |
| `planning/{scratchpad,ideas,backlog,projects,archive,services}/` | The `SKY-###` directive pipeline | planning |
| `ca/`, `.sops.yaml`, `.githooks/` | Trust + secret + commit-gate machinery | infra |

## Required files per artifact type

- **A service** (`compose/<svc>/`) `[testable]`: `compose.yaml` + `.env.git`, plus `.env.sops`
  iff it has secrets. Rules in [`compose.md`](compose.md).
- **A script** (`scripts/*.sh`, `bin/*`) `[testable]`: shebang + `set -euo pipefail` + header
  block. Rules in [`scripts.md`](scripts.md).
- **A runbook** (`runbooks/*.md`) `[testable]`: opens with a **Tier** line (and a **Trigger** line
  where relevant), and is listed in `runbooks/README.md`. Rules in [`docs.md`](docs.md).
- **An ADR** (`docs/decisions/NNNN-*.md`) `[testable]`: Status / Date header + Context / Decision /
  Consequences. Rules in [`docs.md`](docs.md).
- **A directive** (`planning/**/SKY-###-*.md`) `[testable]`: frontmatter schema in
  [`metadata.md`](metadata.md); minted by `bin/plan`.

## Generated — never hand-edit `[testable]`

`inventory/**` and `docs/generated/**` are written by collectors/renderers. Change the
collector or `scripts/render-docs.sh`, never the output. Enforced socially today, mechanically by
the parked lint gate.
