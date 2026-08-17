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
| `compose/README.md` / `runbooks/README.md` / `planning/README.md` | the dirs they index |

Rules `[manual]`:
- **The hub shrinks; the spoke carries depth.** When a topic outgrows a paragraph in the hub,
  split it into a spoke and leave a one-line pointer.
- **Each spoke opens with a `> ` blockquote** stating what it covers and **which hub governs it**,
  and links back to that hub.
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
- **Open with a `Tier` line** (T1/T2/T2+/T3, PR-gated or grant), and a **Trigger** line where the
  runbook has a natural spoken trigger `[testable]`.
- **Every runbook is listed in `runbooks/README.md`** `[testable]` — the catalog is the menu;
  an uncatalogued runbook is invisible.

## README-as-catalog `[manual]`

A directory that holds a *set* of like things (`compose/`, `runbooks/`, `planning/*/`,
`docs/decisions/`) carries a `README.md` that indexes its contents and states the standard the
contents must meet. The README is the hub for that directory.

## Prose style `[manual]`

- Write to **teach** — Ali is learning git/infra through this repo. Say *why*, not just *what*.
- **Convert relative dates to absolute** (`2026-08-17`, not "today") in anything that persists.
- Prefer tables and short rules over long paragraphs; keep the hub scannable.
