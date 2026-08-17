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
| `journal/<YYYY>/*.md` | **Episodic memory** — raw append-only session/incident/decision episodes | memory |
| `compose/<svc>/` | One dir per service (the GitOps loop) | ops |
| `scripts/*.sh` | Procedures runbooks/entry-points call | ops |
| `bin/*` | Operator-facing entry points (`plan`, `new`, `ops`, `grant-root`) | ops |
| `runbooks/*.md`, `runbooks/dr/*.md` | Engine-neutral procedures, catalogued in `runbooks/README.md` | ops |
| `templates/` | The golden templates `bin/new` stamps from — one folder, all kinds | doctrine |
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

## Scaffolding — new artifacts are born conforming

Don't hand-write a new artifact from scratch — **stamp it from its golden template** so it inherits
the doctrine automatically:

| Command | Creates | From template |
|---|---|---|
| `bin/new service <name>` | `compose/<name>/` | `templates/compose/` |
| `bin/new script <name>` | `scripts/<name>.sh` (chmod +x) | `templates/script.sh` |
| `bin/new runbook <title>` | `runbooks/<slug>.md` | `templates/runbook.md` |
| `bin/new adr <title>` | `docs/decisions/NNNN-<slug>.md` (next number) | `templates/adr.md` |
| `bin/new journal <kind> <title>` | `journal/<YYYY>/<date>-<kind>-<slug>.md` | `templates/journal.md` |
| `bin/plan idea\|service\|start …` | a `SKY-###` directive | `planning/TEMPLATE.md` |

**All golden templates live in one folder, [`templates/`](../../templates/)** `[manual]` — not
scattered beside the artifacts they stamp. Each is the **single source** its generator reads:
change a convention once in the template and every future artifact is born with it. The templates
embed the P1 rules verbatim, so a fresh skeleton is doctrine-conforming before you touch it (fill
the `TODO`s). (`bin/plan`'s directive template stays `planning/TEMPLATE.md` — it predates `bin/new`
and `bin/plan` owns its own lifecycle.)

## Generated — never hand-edit `[testable]`

`inventory/**` and `docs/generated/**` are written by collectors/renderers. Change the
collector or `scripts/render-docs.sh`, never the output. Enforced socially today, mechanically by
the parked lint gate.
