---
summary: "How Skynet's prose is structured: hub-and-spoke, ADRs, runbooks, README-as-catalog, and loadable summary/trigger frontmatter."
---

# Spoke · Documentation, ADRs & runbooks

> How Skynet's prose is structured: the hub-and-spoke pattern, how ADRs and runbooks are written,
> and the README-as-catalog rule. Governed by [`../conventions.md`](../conventions.md).

Tags: **[testable]** = a lint gate could assert it; **[manual]** = holds by review.

## Hub and spokes — the convention-about-conventions

Skynet documents a domain as a **short authoritative hub + an open set of spokes**, so the hub
stays scannable and depth lives one click away. Three instances, all the same shape:

| Hub | Spokes |
|---|---|
| `docs/system-design.md` (constitution) | `docs/design/*.md` |
| `docs/conventions.md` | `docs/conventions/*.md` (this set) |
| `compose/README.md` / `runbooks/README.md` / `planning/README.md` / `journal/README.md` | the dirs they index |

Rules `[manual]`:
- **The hub shrinks; the spoke carries depth.** When a topic outgrows a paragraph in the hub,
  split it into a spoke and leave a one-line pointer.
- **Each spoke opens with a `> ` blockquote** stating what it covers and **which hub governs it**,
  and links back to that hub (preceded only by its loadable frontmatter — see *Loadable frontmatter* below).
- **One authoritative home per rule.** State a rule in exactly one place; everywhere else links to
  it. If two docs state the same rule, one is the source and the other points.

## ADRs (`docs/decisions/`)

- **Filename `NNNN-kebab-title.md`**, 4-digit zero-padded, monotonic `[testable]`.
- **Body:** a `Status` + `Date` header, then `## Context`, `## Decision`, `## Consequences`
  `[testable]`.
- **ADRs are living records, always amended in place — never superseded** `[manual]`. An ADR
  stays in effect for its topic; when reality changes (a correction *or* a full reversal), you
  **edit that same ADR** to state the current decision and add a dated line to a short
  `## History` section. There is no `Status: superseded` and no second ADR for the same topic —
  the git log holds the prior wording; the ADR body always tells you what's true now. ADR 0001 was
  amended this way on 2026-08-17 (static-for-ops-brain → static-for-all-guests).

## Runbooks (`runbooks/`)

- **Engine-neutral markdown + bash** `[manual]` — no vendor skill/command format. Any agent that
  reads a file and runs bash executes them.
- **Use compact frontmatter:** `summary`, `tier`, `executor`, and `rollback`; add `trigger` where the
  runbook has a natural spoken cue `[testable]`. Its prose `Tier`/`Trigger` lines are the human twins.
- **Use the fixed task shape:** `Preconditions` → `Steps` → `Verify` → `Rollback` → `Evidence`
  `[testable]`. Keep doctrine in its authoritative document and raw history in `journal/`.
- **Every runbook is rendered into `runbooks/README.md`** `[testable]` by
  `scripts/render-runbook-catalog.sh`; leaf frontmatter is the catalog source.

## Journal — episodic memory (`journal/`)

- **Raw episodes, append-only** `[manual]` — session / incident / decision records under
  `journal/<YYYY>/<YYYY-MM-DD>-<kind>-<slug>.md`, written concrete and **never summarized at write
  time** (that destroys the episodic signal). Distillation happens at read time. The full format
  convention — kinds, the Graveyard section, the two invariants — lives in its one authoritative
  home, [`../../journal/README.md`](../../journal/README.md); stamp entries with `bin/new journal`.
- **Not a generated dir** `[manual]` — `journal/` is authored/appended, never re-rendered, so the
  "never hand-edit generated dirs" rule does **not** apply to it (unlike `docs/generated/`).

## Loadable frontmatter — `summary` / `trigger`  `[manual]`

Every **loadable** doc — a design or conventions spoke, a runbook, a generated page — carries a small
authored frontmatter block so a routing agent can *choose it without opening it*. This is the metadata
the context map (SKY-010 P3) reads to build one row per artifact; it's the machine-readable half of
the [default-lean discipline](../design/memory.md).

| Field | Who writes it | Rule |
|---|---|---|
| `summary:` | **authored**, one line | what the file is, in ≤ ~120 chars, so the map row is legible `[manual]` |
| `trigger:` | **authored**, optional | the spoken cue that should pull this file in (mainly runbooks) `[manual]` |

- **`summary` is the source; the map shows it.** A loadable *without* a `summary:` falls back to its
  first `# heading` in the map — so nothing is invisible, but an authored line is better.
- **Load cost is computed at render time, not stored.** `scripts/render-context-map.sh` derives the
  `~tokens` column itself (content bytes ÷ 4) when it builds the map, so the figure is always fresh and
  no `tokens:` line has to be maintained in each file. (An earlier `tokens:` frontmatter + a
  `budget-frontmatter` lint gate did this by hand-stamping every doc; retired — the renderer already
  had the number.)

## README-as-catalog `[manual]`

A directory that holds a *set* of like things (`compose/`, `runbooks/`, `planning/*/`,
`docs/decisions/`) carries a `README.md` that indexes its contents and states the standard the
contents must meet. The README is the hub for that directory.

## Prose style `[manual]`

- Write to **teach** — Ali is learning git/infra through this repo. Say *why*, not just *what*.
- **Convert relative dates to absolute** (`2026-08-17`, not "today") in anything that persists.
- Prefer tables and short rules over long paragraphs; keep the hub scannable.
- **State the rule, not the incident that taught it.** Design docs, spokes, and conventions carry
  the durable rule plus small actionable notes — *what to do now and why*. The story of what was
  tried, what broke, and how it was fixed is **episodic → [`journal/`](../../journal/README.md)**
  (build-phase incidents live in [`../history/build-log.md`](../history/build-log.md)). No "learned
  at X" / "we tried Y, it fell apart" narratives in design prose — same principle as write-raw-to-journal.
