---
summary: "The structured fields machines read: directive frontmatter, service-catalog entries, and the compose label/tag namespaces."
---

# Spoke · Metadata & frontmatter schemas

> The structured fields machines read: directive frontmatter, service-catalog entries, and the
> compose label/tag namespaces. Governed by [`../conventions.md`](../conventions.md).

Tags: **[testable]** = a lint gate could validate the schema; **[manual]** = holds by review.

## Directive frontmatter (`planning/**/SKY-###-*.md`) `[testable]`

Minted and moved by `bin/plan`; the leading `---` block carries unique keys:

```yaml
---
id: SKY-###                 # zero-padded, matches the filename slug
title: <prose title>        # human title (no trailing period)
status: draft | in-progress | done | archived
horizon: short | medium | long
created: YYYY-MM-DD          # absolute date
updated: YYYY-MM-DD          # bumped every phase close-out
phases: <int>                # total phases (project directives)
current_phase: <int>         # 0 until a phase completes
tier_touched: [T1, T2, T2+, T3]   # every tier the work touches
related:                     # paths + [[memory-links]] this directive leans on
  - docs/system-design.md
  - "[[SKY-###-progress]]"
---
```

- **A directive touching T2+/T3 or a blast-radius boundary MUST list `docs/system-design.md` in
  `related`** and PR the constitution `[manual]` (AGENTS.md §5).
- **`current_phase`, `status`, `updated` are bumped at every phase close-out** `[manual]`; the
  matching phase checkbox flips `[ ]`→`[x]`.

## Service-catalog entry (`planning/services/SKY-###-*.md`) `[manual]`

A sketch of a service to bring onto the skynet way — up front: what it is, why we'd run it,
image/compose notes, and its **secrets / DNS / backup** needs. `bin/plan start SKY-###` promotes
it into a real `projects/` directive with deployment phases. The standard it must reach is the
[`compose.md`](compose.md) spoke.

## Compose metadata namespaces

Defined canonically in [`compose.md`](compose.md); summarised here as schemas:

- **`x-arcane.tags`** — exactly one role tag per service, `{name: <role>, color: <stable-colour>}`
  `[testable]`.
- **`skynet.*` volume labels** — every named volume carries all three `[testable]`:
  | label | values |
  |---|---|
  | `skynet.service` | `<svc>` |
  | `skynet.backup` | `protect` \| `ephemeral` |
  | `skynet.managed` | `gitops` |

  The vocabulary is open to extend (`skynet.backup: snapshot`, a future `skynet.tier`) without
  breaking the `protect`/`ephemeral` core.
