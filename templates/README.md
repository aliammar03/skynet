# templates — the golden skeletons `bin/new` stamps from

One folder holding every artifact template, so the house style has a **single source** per kind:
change a convention here and every future artifact is born with it (Style B of
[SKY-009](../planning/projects/SKY-009-convention-bedrock-doctrine-spine-and-golden-templates.md)).
Each template embeds the rules from the [convention spokes](../docs/conventions/) verbatim, so a
fresh skeleton is doctrine-conforming before you edit it — you just fill the `TODO`s.

| Template | `bin/new` command | Stamps | Rules (spoke) |
|---|---|---|---|
| [`compose/`](compose/) | `bin/new service <name>` | `compose/<name>/` | [compose](../docs/conventions/compose.md) |
| [`script.sh`](script.sh) | `bin/new script <name>` | `scripts/<name>.sh` | [scripts](../docs/conventions/scripts.md) |
| [`runbook.md`](runbook.md) | `bin/new runbook <title>` | `runbooks/<slug>.md` | [docs](../docs/conventions/docs.md) |
| [`adr.md`](adr.md) | `bin/new adr <title>` | `docs/decisions/NNNN-<slug>.md` | [docs](../docs/conventions/docs.md) |

Placeholders the generator fills: `__SVC__`, `__NAME__`, `__TITLE__`, `__NUM__`, `__DATE__`.
Everything a human must decide is a literal `TODO` in the stamped file.

**Directives (`SKY-###`) are not here** — `bin/plan` scaffolds them from `planning/TEMPLATE.md`,
which it has owned since before `bin/new` existed.
