---
summary: "The golden templates (compose, script, runbook, ADR, journal) that `skynet new` stamps so new artifacts inherit the house style."
---

# templates — the golden skeletons `skynet new` stamps from

One folder holding every artifact template, so the house style has a **single source** per kind:
change a convention here and every future artifact is born with it.
Each template embeds the rules from the [convention spokes](../docs/conventions/) verbatim, so a
fresh skeleton is doctrine-conforming before you edit it — you just fill the `TODO`s.

| Template | `skynet new` command | Stamps | Rules (spoke) |
|---|---|---|---|
| [`compose/`](compose/) | `skynet new service <name>` | `compose/<name>/` | [compose](../docs/conventions/compose.md) |
| [`script.sh`](script.sh) | `skynet new script <name>` | `scripts/<name>.sh` | [scripts](../docs/conventions/scripts.md) |
| [`runbook.md`](runbook.md) | `skynet new runbook <title>` | `runbooks/<slug>.md` | [docs](../docs/conventions/docs.md) |
| [`adr.md`](adr.md) | `skynet new adr <title>` | `docs/decisions/NNNN-<slug>.md` | [docs](../docs/conventions/docs.md) |
| [`journal.md`](journal.md) | `skynet new journal <kind> <title>` | `journal/<YYYY>/<date>-<kind>-<slug>.md` | [journal](../journal/README.md) |

Placeholders the generator fills: `__SVC__`, `__NAME__`, `__TITLE__`, `__NUM__`, `__DATE__`, `__KIND__`.
Everything a human must decide is a literal `TODO` in the stamped file.

**Directives (`SKY-###`) are not here** — `skynet plan` scaffolds them from `planning/TEMPLATE.md`,
which it has owned since before `skynet new` existed.
